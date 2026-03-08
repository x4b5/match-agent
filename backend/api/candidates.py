from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
import os
import shutil

from backend.config import KANDIDATEN_DIR
from backend.utils import formatteer_directory_response, opslaan_profiel, zorg_voor_uuid
from backend.services.agents import profileer_kandidaat, extract_text_sync, genereer_embedding
from backend.database import bewaar_embedding, bewaar_document, haal_alle_documenten
from backend.services.pii_scrubber import scrub_pii
from backend.api.tasks import maak_task, update_task

router = APIRouter(prefix="/candidates", tags=["Kandidaten"])

# Minimale tekst voor profielgeneratie
MIN_TEKST_LENGTE = 50


@router.get("/")
async def list_candidates():
    if not os.path.exists(KANDIDATEN_DIR):
        os.makedirs(KANDIDATEN_DIR, exist_ok=True)

    # Get all processed documents from DB
    db_docs = await haal_alle_documenten("kandidaat")

    # Also get raw directories for items not yet processed
    raw_dirs = formatteer_directory_response(KANDIDATEN_DIR)

    # We blend them: DB documents take precedence and contain the profile_dict
    db_map = {doc["naam"]: doc for doc in db_docs}

    response = []
    for d in raw_dirs:
        naam = d["naam"]
        if naam in db_map:
            db_doc = db_map[naam]
            d["profiel"] = db_doc.get("profiel_dict")
            d["waarschuwingen"] = db_doc.get("waarschuwingen_list", [])
        response.append(d)

    return response

@router.post("/")
async def create_candidate(name: str):
    veilige_naam = "".join(c for c in name if c.isalnum() or c in ('_', '-')).strip()
    nieuw_pad = os.path.join(KANDIDATEN_DIR, veilige_naam)
    if os.path.exists(nieuw_pad):
        raise HTTPException(status_code=400, detail="Map bestaat al.")
    os.makedirs(nieuw_pad)
    uuid_val = zorg_voor_uuid(nieuw_pad)
    return {"message": "Success", "id": uuid_val, "naam": veilige_naam}

@router.delete("/{name}")
async def delete_candidate(name: str):
    pad = os.path.join(KANDIDATEN_DIR, name)
    if not os.path.exists(pad):
        raise HTTPException(status_code=404, detail="Map niet gevonden.")
    try:
        shutil.rmtree(pad)
        return {"message": "Verwijderd"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{name}/upload")
async def upload_document(name: str, file: UploadFile = File(...)):
    doel_pad = os.path.join(KANDIDATEN_DIR, name)
    if not os.path.exists(doel_pad):
        raise HTTPException(status_code=404, detail="Map niet gevonden.")
    file_pad = os.path.join(doel_pad, file.filename)
    with open(file_pad, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"message": "Geüpload", "filename": file.filename}

@router.delete("/{name}/document/{filename}")
async def delete_document(name: str, filename: str):
    pad = os.path.join(KANDIDATEN_DIR, name, filename)
    if not os.path.exists(pad):
        raise HTTPException(status_code=404, detail="Document niet gevonden.")
    os.remove(pad)
    return {"message": "Verwijderd"}

async def _generate_profile_task(map_pad: str, task_id: str):
    update_task(task_id, status="running")
    try:
        gecombineerde_tekst, waarschuwingen = extract_text_sync(map_pad)

        # Input validatie: minimaal 50 bruikbare karakters
        schone_tekst = gecombineerde_tekst.strip()
        # Verwijder de header-markers om echte inhoud te meten
        inhoud = "\n".join(
            l for l in schone_tekst.splitlines()
            if not l.strip().startswith("--- Inhoud uit")
        ).strip()

        if len(inhoud) < MIN_TEKST_LENGTE:
            update_task(
                task_id, status="failed",
                error=f"Te weinig tekst voor profielgeneratie ({len(inhoud)} karakters, minimaal {MIN_TEKST_LENGTE}). Upload meer documenten."
            )
            return

        update_task(task_id, progress="PII scrubbing...")

        # PII Scrubbing voordat tekst naar het LLM gaat
        geschoonde_tekst, pii_rapport = scrub_pii(gecombineerde_tekst)
        if pii_rapport:
            waarschuwingen.append(f"PII gemaskeerd: {pii_rapport}")

        update_task(task_id, progress="Profiel genereren via LLM...")

        # Generate Profile via LLM (met geschoonde tekst)
        resultaat = await profileer_kandidaat(geschoonde_tekst)

        update_task(task_id, progress="Embedding en opslag...")

        # Generate and Store Embeddings and Document into DB
        try:
            uuid_val = zorg_voor_uuid(map_pad)
            naam = os.path.basename(map_pad)

            # Save embedding
            vector = await genereer_embedding(gecombineerde_tekst)
            if vector:
                await bewaar_embedding(uuid_val, "kandidaat", naam, vector)

            # Save full document to SQL
            await bewaar_document(
                document_id=uuid_val,
                doc_type="kandidaat",
                naam=naam,
                ruwe_tekst=gecombineerde_tekst,
                profiel_dict=resultaat if isinstance(resultaat, dict) else None,
                waarschuwingen=waarschuwingen
            )

        except Exception as e:
            print(f"Error saving data for candidate {map_pad}: {e}")

        if isinstance(resultaat, dict):
            if waarschuwingen:
                resultaat["_waarschuwingen"] = waarschuwingen
            opslaan_profiel(map_pad, resultaat)

        update_task(task_id, status="done", progress="Klaar")

    except Exception as e:
        update_task(task_id, status="failed", error=str(e))

@router.post("/{name}/generate-profile")
async def generate_profile(name: str, background_tasks: BackgroundTasks):
    doel_pad = os.path.join(KANDIDATEN_DIR, name)
    if not os.path.exists(doel_pad):
        raise HTTPException(status_code=404, detail="Map niet gevonden.")
    task_id = maak_task("profile_generation", name)
    background_tasks.add_task(_generate_profile_task, doel_pad, task_id)
    return {"message": "Profiel generatie gestart in de achtergrond.", "task_id": task_id}
