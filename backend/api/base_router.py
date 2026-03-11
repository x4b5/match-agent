"""
Generieke Document Router — elimineert code duplicatie tussen candidates.py en employers.py.

Gebruik:
    router = create_document_router(
        prefix="/candidates",
        tag="Kandidaten",
        base_dir=KANDIDATEN_DIR,
        doc_type="kandidaat",
        profiel_agent_fn=profileer_kandidaat,
        verrijk_agent_fn=verrijk_kandidaat_profiel,
    )
"""
import os
import shutil
import json
import logging
import asyncio
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from pydantic import BaseModel as PydanticBaseModel

from backend.utils import formatteer_directory_response, opslaan_profiel, zorg_voor_uuid
from backend.services.agents import extract_text_sync
from backend.database import (
    bewaar_embedding, bewaar_document, haal_alle_documenten, haal_document,
    bewaar_verrijking, update_profiel_na_verrijking, update_task_db
)
from backend.services.pii_scrubber import scrub_pii
from backend.api.tasks import maak_task

logger = logging.getLogger("matchflix.router")

MIN_TEKST_LENGTE = 50


class EnrichRequest(PydanticBaseModel):
    antwoorden: dict  # {"vraag": "antwoord", ...}


def create_document_router(
    prefix: str,
    tag: str,
    get_base_dir,
    doc_type: str,
    profiel_agent_fn,
    verrijk_agent_fn,
    auto_shortlist: bool = False,
) -> APIRouter:
    """
    Factory functie die een volledige CRUD + profiel router maakt
    voor een document type (kandidaat of vacature).
    
    get_base_dir: callable die het pad naar de basisdirectory retourneert.
                  Dit zorgt ervoor dat test-monkeypatches correct werken.
    """
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.get("/")
    async def list_items():
        base_dir = get_base_dir()
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)

        # 1. Haal alles op uit de database (Source of Truth)
        db_docs = await haal_alle_documenten(doc_type)
        
        # 2. Haal de fysieke mappen op
        fysieke_mappen = formatteer_directory_response(base_dir)
        fysieke_map_namen = {d["naam"] for d in fysieke_mappen}
        db_map_namen = {doc["naam"] for doc in db_docs}

        response = []
        
        # Voeg DB items toe (met status-verrijking)
        for doc in db_docs:
            naam = doc["naam"]
            bestaat_fysiek = naam in fysieke_map_namen
            
            # Zoek bijbehorende fysieke info (doc count etc)
            fysieke_info = next((d for d in fysieke_mappen if d["naam"] == naam), {})
            
            # Zorg dat last_generated altijd aanwezig is in profile_data
            profiel_data = doc["profiel_dict"]
            if profiel_data and not profiel_data.get("last_generated"):
                profiel_data["last_generated"] = doc.get("timestamp")

            # Tags genereren uit profieldata (voor zoekfunctie)
            tags = []
            if profiel_data:
                if profiel_data.get("titel"):
                    tags.append(profiel_data["titel"])
                if profiel_data.get("organisatie"):
                    tags.append(profiel_data["organisatie"])

            response.append({
                "id": doc["document_id"],
                "naam": naam,
                "doc_count": fysieke_info.get("doc_count", 0),
                "docs": fysieke_info.get("docs", []),
                "has_profile": doc["profiel_compleet"],
                "profile_score": profiel_data.get("dossier_compleetheid", profiel_data.get("profiel_betrouwbaarheid")) if profiel_data else None,
                "profile_data": profiel_data,
                "tags": tags,
                "waarschuwingen": doc.get("waarschuwingen_list", []),
                "exists_on_disk": bestaat_fysiek,
                "timestamp": doc["timestamp"]
            })
            
        # Voeg fysieke mappen toe die nog niet in de DB staan (nieuwe/onverwerkte items)
        for d in fysieke_mappen:
            if d["naam"] not in db_map_namen:
                d["exists_on_disk"] = True
                d["has_profile"] = False # Nog niet in DB = geen formeel profiel
                response.append(d)
                
        # Sorteer op timestamp (indien aanwezig) of naam
        response.sort(key=lambda x: x.get("timestamp", x["naam"]), reverse=True)
        return response

    @router.post("/")
    async def create_item(name: str):
        base_dir = get_base_dir()
        veilige_naam = "".join(c for c in name if c.isalnum() or c in ('_', '-')).strip()
        if not veilige_naam:
            raise HTTPException(status_code=400, detail="Naam mag niet leeg zijn na sanitizatie.")
        nieuw_pad = os.path.join(base_dir, veilige_naam)
        if os.path.exists(nieuw_pad):
            raise HTTPException(status_code=400, detail="Map bestaat al.")
        os.makedirs(nieuw_pad)
        
        # Check DB eerst voor UUID
        from backend.database import haal_uuid_bij_naam
        bestaande_uuid = await haal_uuid_bij_naam(veilige_naam, doc_type)
        uuid_val = bestaande_uuid if bestaande_uuid else zorg_voor_uuid(nieuw_pad)
        
        return {"message": "Success", "id": uuid_val, "naam": veilige_naam}

    @router.delete("/{name}")
    async def delete_item(name: str):
        base_dir = get_base_dir()
        pad = os.path.join(base_dir, name)
        
        # GDPR verwijdering uit DB
        from backend.database import haal_uuid_bij_naam, verwijder_alle_data
        uuid_val = await haal_uuid_bij_naam(name, doc_type)
        if uuid_val:
            await verwijder_alle_data(uuid_val)
            
        if os.path.exists(pad):
            try:
                shutil.rmtree(pad)
                return {"message": "Verwijderd (DB+FS)"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        return {"message": "Verwijderd uit database (map bestond niet)"}

    @router.get("/{name}")
    async def get_item_detail(name: str):
        """Haal volledige detail-informatie op voor één item, inclusief profiel en documenten."""
        base_dir = get_base_dir()
        pad = os.path.join(base_dir, name)
        
        # Haal data primair uit DB
        db_doc = await haal_document(name)
        
        from backend.utils import laad_profiel_uit_map, lijst_bestanden, zorg_voor_uuid
        
        exists_on_disk = os.path.exists(pad)
        docs = [f for f in lijst_bestanden(pad) if not f.endswith(".json")] if exists_on_disk else []
        
        if not db_doc and not exists_on_disk:
            raise HTTPException(status_code=404, detail="Item niet gevonden.")

        uuid_val = db_doc["document_id"] if db_doc else zorg_voor_uuid(pad)
        profiel = db_doc.get("profiel_dict") if db_doc else laad_profiel_uit_map(pad)
        waarschuwingen = db_doc.get("waarschuwingen_list", []) if db_doc else []

        # Zorg dat last_generated altijd aanwezig is
        if profiel and not profiel.get("last_generated") and db_doc:
            profiel["last_generated"] = db_doc.get("timestamp")

        return {
            "id": uuid_val,
            "naam": name,
            "doc_count": len(docs),
            "docs": docs,
            "has_profile": bool(profiel),
            "profile_data": profiel,
            "waarschuwingen": waarschuwingen,
            "profile_score": (profiel or {}).get("dossier_compleetheid", (profiel or {}).get("profiel_betrouwbaarheid")),
            "vervolgvragen": (profiel or {}).get("vervolgvragen", []),
            "stellingen": (profiel or {}).get("stellingen", []),
            "exists_on_disk": exists_on_disk
        }

    @router.put("/{name}/profile")
    async def update_item_profile(name: str, profile: dict):
        """Handmatig een profiel bijwerken (inhoud inzien en aanpassen)."""
        base_dir = get_base_dir()
        pad = os.path.join(base_dir, name)
        
        # Check DB eerst voor UUID
        from backend.database import haal_uuid_bij_naam
        uuid_val = await haal_uuid_bij_naam(name, doc_type)
        if not uuid_val and os.path.exists(pad):
            uuid_val = zorg_voor_uuid(pad)
        
        if not uuid_val:
            raise HTTPException(status_code=404, detail="Item niet gevonden in DB of op schijf.")

        # Sla op in database
        await bewaar_document(
            document_id=uuid_val,
            doc_type=doc_type,
            naam=name,
            ruwe_tekst="",
            profiel_dict=profile,
            waarschuwingen=[]
        )

        # Sla op als JSON-bestand in directory (fallback/backup)
        if os.path.exists(pad):
            opslaan_profiel(pad, profile)

        return {"message": "Profiel bijgewerkt", "naam": name}

    @router.post("/{name}/upload")
    async def upload_document(name: str, file: UploadFile = File(...)):
        base_dir = get_base_dir()
        doel_pad = os.path.join(base_dir, name)
        if not os.path.exists(doel_pad):
            os.makedirs(doel_pad) # Auto-create directory if it was deleted but remains in DB
            
        file_pad = os.path.join(doel_pad, file.filename)
        with open(file_pad, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"message": "Geüpload", "filename": file.filename}

    @router.delete("/{name}/document/{filename}")
    async def delete_document(name: str, filename: str):
        base_dir = get_base_dir()
        pad = os.path.join(base_dir, name, filename)
        if not os.path.exists(pad):
            raise HTTPException(status_code=404, detail="Document niet gevonden.")
        os.remove(pad)
        return {"message": "Verwijderd"}

    async def _generate_profile_task(map_pad: str, task_id: str, skip_pii: bool = False, direct_text: str | None = None, provider_type: str = "local"):
        await update_task_db(task_id, status="running", progress="Starten...", progress_percent=5)
        try:
            if direct_text:
                gecombineerde_tekst = direct_text
                waarschuwingen = []
            else:
                from fastapi.concurrency import run_in_threadpool
                gecombineerde_tekst, waarschuwingen = await run_in_threadpool(extract_text_sync, map_pad)

            schone_tekst = gecombineerde_tekst.strip()
            inhoud = "\n".join(
                l for l in schone_tekst.splitlines()
                if not l.strip().startswith("--- Inhoud uit")
            ).strip()

            if len(inhoud) < MIN_TEKST_LENGTE:
                await update_task_db(
                    task_id, status="failed",
                    error=f"Te weinig tekst voor profielgeneratie ({len(inhoud)} karakters, minimaal {MIN_TEKST_LENGTE}). Upload meer documenten."
                )
                return
            
            # ── Deduplicatie Check (Hash) ──
            from backend.utils import bereken_hash
            content_hash = bereken_hash(inhoud)
            
            from backend.database import haal_document_bij_hash
            bestaand = await haal_document_bij_hash(content_hash, doc_type)
            if bestaand and bestaand["naam"] != os.path.basename(map_pad):
                logger.info(f"Deduplicatie: Document met deze inhoud bestaat al als '{bestaand['naam']}'")
                waarschuwingen.append(f"Let op: Inhoud is identiek aan bestaand item '{bestaand['naam']}'.")

            if skip_pii:
                geschoonde_tekst = gecombineerde_tekst
                pii_rapport = {}
            else:
                await update_task_db(task_id, progress="Persoonlijke gegevens anonimiseren...", progress_percent=20)
                geschoonde_tekst, pii_rapport = scrub_pii(gecombineerde_tekst)
                if pii_rapport:
                    waarschuwingen.append(f"PII gemaskeerd: {pii_rapport}")

            # ── Sequentiële uitvoering: profiel eerst, dan embedding ──
            # Ollama kan maar één model tegelijk laden, dus sequentieel uitvoeren
            await update_task_db(task_id, progress="Model wordt geladen...", progress_percent=35)

            # Voortgangsticker: laat de balk geleidelijk oplopen tijdens de LLM-call
            llm_berichten = [
                (38, "Tekst wordt gelezen door AI..."),
                (42, "Persoonlijkheid wordt geanalyseerd..."),
                (48, "Drijfveren worden ingeschat..."),
                (54, "Vaardigheden worden geëxtraheerd..."),
                (60, "Verrassende functies worden bedacht..."),
                (65, "Profiel wordt afgerond..."),
            ]
            ticker_done = asyncio.Event()

            async def _progress_ticker():
                for pct, msg in llm_berichten:
                    try:
                        await asyncio.wait_for(ticker_done.wait(), timeout=15)
                        return  # LLM is klaar
                    except asyncio.TimeoutError:
                        await update_task_db(task_id, progress=msg, progress_percent=pct)
                # Als we hier komen draait de LLM nog steeds — blijf rustig wachten
                stap = 68
                while stap < 74:
                    try:
                        await asyncio.wait_for(ticker_done.wait(), timeout=30)
                        return
                    except asyncio.TimeoutError:
                        await update_task_db(task_id, progress="Bijna klaar met analyse...", progress_percent=stap)
                        stap += 2

            ticker_task = asyncio.create_task(_progress_ticker())
            try:
                resultaat = await asyncio.wait_for(
                    profiel_agent_fn(geschoonde_tekst, provider_type=provider_type),
                    timeout=600
                )
            except asyncio.TimeoutError:
                ticker_done.set()
                await update_task_db(
                    task_id, status="failed",
                    error="Profielgeneratie duurde te lang (timeout na 10 minuten). Mogelijk is het Ollama model overbelast. Probeer het opnieuw."
                )
                return
            finally:
                ticker_done.set()
                ticker_task.cancel()

            await update_task_db(task_id, progress="Embedding genereren...", progress_percent=75)
            # Geef Ollama even tijd om van generatie-model naar embedding-model te wisselen
            await asyncio.sleep(2)

            await update_task_db(task_id, progress="Gegevens opslaan en indexeren...", progress_percent=90)
            try:
                naam = os.path.basename(map_pad)
                resultaat["last_generated"] = datetime.now().isoformat()
                from backend.database import haal_uuid_bij_naam
                bestaande_uuid = await haal_uuid_bij_naam(naam, doc_type)
                uuid_val = bestaande_uuid if bestaande_uuid else zorg_voor_uuid(map_pad)

                vector_zijn = None
                vector_willen = None
                vector_kunnen = None

                # Drie pijler-embeddings genereren
                if isinstance(resultaat, dict):
                    zijn_tekst = str(resultaat.get("zijn", ""))
                    willen_tekst = str(resultaat.get("willen", ""))
                    kunnen_delen = []
                    if "kunnen" in resultaat: kunnen_delen.append(str(resultaat["kunnen"]))
                    if "kernrol" in resultaat: kunnen_delen.append(resultaat["kernrol"])
                    if "titel" in resultaat: kunnen_delen.append(resultaat["titel"])
                    kunnen_tekst = " ".join(filter(None, kunnen_delen))

                    from backend.services.agents import genereer_embeddings_batch
                    try:
                        vector_zijn, vector_willen, vector_kunnen = await genereer_embeddings_batch([zijn_tekst, willen_tekst, kunnen_tekst])
                    except Exception as e:
                        logger.warning(f"Zijn/willen/kunnen embeddings mislukt: {e}")
                        vector_zijn, vector_willen, vector_kunnen = None, None, None

                # ── Semantische Deduplicatie Check (Numpy Batch) ──
                if vector_zijn:
                    from backend.database import haal_alle_embeddings, _batch_cosine
                    bestaande_embeddings = await haal_alle_embeddings(doc_type)

                    if bestaande_embeddings:
                        target_naam = os.path.basename(map_pad)
                        valid_to_check = [emb for emb in bestaande_embeddings if emb["naam"] != target_naam and emb["vector_zijn"]]

                        if valid_to_check:
                            import numpy as np
                            q = np.asarray(vector_zijn, dtype=np.float64)
                            mat = np.array([emb["vector_zijn"] for emb in valid_to_check], dtype=np.float64)

                            if mat.size > 0:
                                similarities = _batch_cosine(mat, q)
                                max_idx = np.argmax(similarities)
                                max_sim = similarities[max_idx]

                                if max_sim > 0.92:
                                    match_naam = valid_to_check[max_idx]["naam"]
                                    waarschuwingen.append(f"Let op: Dit document lijkt sterk op '{match_naam}'. Wil je doorgaan?")
                                    logger.info(f"Semantische deduplicatie: '{target_naam}' lijkt {int(max_sim * 100)}% op '{match_naam}'")

                # Save embedding (AVG-compliant)
                if vector_zijn or vector_willen or vector_kunnen:
                    await bewaar_embedding(uuid_val, doc_type, naam, vector_zijn, vector_willen, vector_kunnen)

                await bewaar_document(
                    document_id=uuid_val,
                    doc_type=doc_type,
                    naam=naam,
                    ruwe_tekst=geschoonde_tekst,
                    profiel_dict=resultaat if isinstance(resultaat, dict) else None,
                    waarschuwingen=waarschuwingen,
                    content_hash=content_hash
                )

                # Auto-shortlist bij nieuwe vacature
                if auto_shortlist and vector_zijn and isinstance(resultaat, dict):
                    from backend.database import haal_top_matches_vector
                    shortlist = await haal_top_matches_vector(vacature_zijn=vector_zijn, vacature_willen=vector_willen, vacature_kunnen=vector_kunnen, limit=5)
                    if shortlist:
                        logger.info(f"Auto-shortlist voor '{naam}': {len(shortlist)} matches (top: {shortlist[0]['percentage']}%)")

            except Exception as e:
                logger.error(f"Error saving data for {doc_type} {map_pad}: {e}")

            if isinstance(resultaat, dict):
                if waarschuwingen:
                    resultaat["_waarschuwingen"] = waarschuwingen
                opslaan_profiel(map_pad, resultaat)

            await update_task_db(task_id, status="done", progress="Klaar", progress_percent=100)

        except Exception as e:
            logger.error(f"Profile generation failed for {map_pad}: {e}")
            await update_task_db(task_id, status="failed", error=str(e))

    @router.post("/{name}/generate-profile")
    async def generate_profile(name: str, background_tasks: BackgroundTasks, skip_pii: bool = False):
        base_dir = get_base_dir()
        doel_pad = os.path.join(base_dir, name)
        if not os.path.exists(doel_pad):
            raise HTTPException(status_code=404, detail="Map niet gevonden.")
        task_id = maak_task("profile_generation", name)
        background_tasks.add_task(_generate_profile_task, doel_pad, task_id, skip_pii)
        return {"message": "Profiel generatie gestart in de achterground.", "task_id": task_id}

    @router.post("/{name}/enrich")
    async def enrich_profile(name: str, req: EnrichRequest, background_tasks: BackgroundTasks):
        """Verrijk een profiel met nieuwe Q&A antwoorden."""
        base_dir = get_base_dir()
        doel_pad = os.path.join(base_dir, name)
        
        doc = await haal_document(name)
        if not doc or not doc.get("profiel_dict"):
            raise HTTPException(status_code=400, detail="Geen bestaand profiel gevonden. Genereer eerst een profiel.")
        
        document_id = doc["document_id"]
        await bewaar_verrijking(document_id, req.antwoorden)
        
        profiel_json = json.dumps(doc["profiel_dict"], ensure_ascii=False)
        antwoorden_json = json.dumps(req.antwoorden, ensure_ascii=False)
        ruwe_tekst = doc.get("ruwe_tekst", "")
        
        nieuw_profiel = await verrijk_agent_fn(profiel_json, antwoorden_json, ruwe_tekst)
        if isinstance(nieuw_profiel, dict):
            nieuw_profiel["last_generated"] = datetime.now().isoformat()
        
        if not isinstance(nieuw_profiel, dict):
            raise HTTPException(status_code=500, detail="LLM kon geen verrijkt profiel genereren.")
        
        versie_info = await update_profiel_na_verrijking(document_id, nieuw_profiel)
        
        if os.path.exists(doel_pad):
            opslaan_profiel(doel_pad, nieuw_profiel)
        
        # Herbereken embeddings zodat het systeem "leert" van de nieuwe info
        try:
            from backend.services.agents import genereer_embeddings_batch

            zijn_tekst = str(nieuw_profiel.get("zijn", ""))
            willen_tekst = str(nieuw_profiel.get("willen", ""))
            kunnen_delen = [str(nieuw_profiel.get("kunnen", ""))]
            if nieuw_profiel.get("kernrol"):
                kunnen_delen.append(nieuw_profiel["kernrol"])
            if nieuw_profiel.get("titel"):
                kunnen_delen.append(nieuw_profiel["titel"])
            kunnen_tekst = " ".join(filter(None, kunnen_delen))

            vec_zijn, vec_willen, vec_kunnen = await genereer_embeddings_batch([
                zijn_tekst,
                willen_tekst,
                kunnen_tekst
            ])

            await bewaar_embedding(document_id, doc_type, name, vec_zijn, vec_willen, vec_kunnen)
            logger.info(f"Embeddings herberekened voor {name} na verrijking.")
        except Exception as e:
            logger.error(f"Fout bij herberekenen embeddings voor {name}: {e}")
            # We gaan door, want het profiel is wel opgeslagen
        
        return {
            "message": f"Profiel verrijkt naar versie {versie_info['versie']}.",
            "versie": versie_info["versie"],
            "nieuwe_score": nieuw_profiel.get("dossier_compleetheid", nieuw_profiel.get("profiel_betrouwbaarheid", 0)),
            "vervolgvragen": nieuw_profiel.get("vervolgvragen", []),
            "stellingen": nieuw_profiel.get("stellingen", []),
            "profiel": nieuw_profiel
        }

    @router.post("/bulk-import")
    async def bulk_import(background_tasks: BackgroundTasks, skip_pii: bool = False):
        """Scan directory en importeer alles wat nog niet in de DB staat."""
        base_dir = get_base_dir()
        if not os.path.exists(base_dir):
            return {"message": "Geen mappen gevonden."}

        db_docs = await haal_alle_documenten(doc_type)
        db_namen = {doc["naam"] for doc in db_docs}

        from backend.utils import lijst_mappen
        fysieke_mappen = lijst_mappen(base_dir)

        import_count = 0
        tasks = []
        for m in fysieke_mappen:
            if m not in db_namen:
                pad = os.path.join(base_dir, m)
                task_id = maak_task("profile_generation", m)
                background_tasks.add_task(_generate_profile_task, pad, task_id, skip_pii)
                tasks.append(task_id)
                import_count += 1
                
        return {
            "message": f"Bulk import gestart voor {import_count} items.",
            "task_ids": tasks
        }

    class GenerateFromTextRequest(PydanticBaseModel):
        tekst: str
        provider_type: str = "local"

    class ExtractTextRequest(PydanticBaseModel):
        filenames: list[str]

    @router.post("/{name}/generate-from-text")
    async def generate_from_text(name: str, req: GenerateFromTextRequest, background_tasks: BackgroundTasks):
        """Genereer een volledig nieuw profiel vanuit geschoonde tekst."""
        base_dir = get_base_dir()
        doel_pad = os.path.join(base_dir, name)
        if not os.path.exists(doel_pad):
            os.makedirs(doel_pad, exist_ok=True)

        task_id = maak_task("profile_generation", name)
        background_tasks.add_task(
            _generate_profile_task, doel_pad, task_id,
            skip_pii=True, direct_text=req.tekst, provider_type=req.provider_type
        )
        return {"message": "Profiel generatie gestart.", "task_id": task_id}

    @router.post("/{name}/enrich-from-text")
    async def enrich_from_text(name: str, req: GenerateFromTextRequest, background_tasks: BackgroundTasks):
        """Voeg nieuwe tekst toe aan een bestaand profiel en regenereer."""
        base_dir = get_base_dir()
        doel_pad = os.path.join(base_dir, name)
        
        doc = await haal_document(name)
        if not doc or not doc.get("profiel_dict"):
            raise HTTPException(status_code=400, detail="Geen bestaand profiel om te verrijken.")
            
        task_id = maak_task("profile_enrichment", name)
        
        async def _enrich_task():
            await update_task_db(task_id, status="running", progress="Profiel verrijken met nieuwe data...", progress_percent=10)
            
            # Combineer bestaande ruwe tekst met nieuwe tekst
            bestaande_tekst = doc.get("ruwe_tekst", "")
            gecombineerde_tekst = f"{bestaande_tekst}\n\n--- Toegevoegde informatie ---\n\n{req.tekst}"
            
            # Gebruik de bestaande generatie logic maar met de gecombineerde tekst
            await _generate_profile_task(doel_pad, task_id, skip_pii=True, direct_text=gecombineerde_tekst, provider_type=req.provider_type)

        background_tasks.add_task(_enrich_task)
        return {"message": "Profiel verrijking gestart.", "task_id": task_id}

    @router.post("/{name}/extract-text")
    async def extract_item_text(name: str, req: ExtractTextRequest):
        """Haal tekst op uit specifieke documenten in een dossier."""
        base_dir = get_base_dir()
        pad = os.path.join(base_dir, name)
        if not os.path.exists(pad):
            raise HTTPException(status_code=404, detail="Dossier niet gevonden.")
        
        from fastapi.concurrency import run_in_threadpool
        tekst, waarschuwingen = await run_in_threadpool(extract_text_sync, pad, req.filenames)
        return {"tekst": tekst, "waarschuwingen": waarschuwingen}

    return router

