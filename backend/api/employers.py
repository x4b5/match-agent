from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
import os
import shutil
import asyncio

from backend.config import WERKGEVERSVRAGEN_DIR
from backend.utils import formatteer_directory_response, opslaan_profiel, zorg_voor_uuid
from backend.services.agents import profileer_werkgeversvraag, extract_text_sync

router = APIRouter(prefix="/employers", tags=["Werkgevers"])

@router.get("/")
async def list_employers():
    if not os.path.exists(WERKGEVERSVRAGEN_DIR):
        os.makedirs(WERKGEVERSVRAGEN_DIR, exist_ok=True)
    return formatteer_directory_response(WERKGEVERSVRAGEN_DIR)

@router.post("/")
async def create_employer(name: str):
    veilige_naam = "".join(c for c in name if c.isalnum() or c in ('_', '-')).strip()
    nieuw_pad = os.path.join(WERKGEVERSVRAGEN_DIR, veilige_naam)
    if os.path.exists(nieuw_pad):
        raise HTTPException(status_code=400, detail="Map bestaat al.")
    os.makedirs(nieuw_pad)
    uuid_val = zorg_voor_uuid(nieuw_pad)
    return {"message": "Success", "id": uuid_val, "naam": veilige_naam}

@router.delete("/{name}")
async def delete_employer(name: str):
    pad = os.path.join(WERKGEVERSVRAGEN_DIR, name)
    if not os.path.exists(pad):
        raise HTTPException(status_code=404, detail="Map niet gevonden.")
    try:
        shutil.rmtree(pad)
        return {"message": "Verwijderd"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{name}/upload")
async def upload_document(name: str, file: UploadFile = File(...)):
    doel_pad = os.path.join(WERKGEVERSVRAGEN_DIR, name)
    if not os.path.exists(doel_pad):
        raise HTTPException(status_code=404, detail="Map niet gevonden.")
    file_pad = os.path.join(doel_pad, file.filename)
    with open(file_pad, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"message": "Geüpload", "filename": file.filename}

@router.delete("/{name}/document/{filename}")
async def delete_document(name: str, filename: str):
    pad = os.path.join(WERKGEVERSVRAGEN_DIR, name, filename)
    if not os.path.exists(pad):
        raise HTTPException(status_code=404, detail="Document niet gevonden.")
    os.remove(pad)
    return {"message": "Verwijderd"}

def _generate_profile_task(map_pad: str):
    gecombineerde_tekst, waarschuwingen = extract_text_sync(map_pad)
    if not gecombineerde_tekst.strip():
        return
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        resultaat = loop.run_until_complete(profileer_werkgeversvraag(gecombineerde_tekst))
        if isinstance(resultaat, dict):
            if waarschuwingen:
                resultaat["_waarschuwingen"] = waarschuwingen
            opslaan_profiel(map_pad, resultaat)
    finally:
        loop.close()

@router.post("/{name}/generate-profile")
async def generate_profile(name: str, background_tasks: BackgroundTasks):
    doel_pad = os.path.join(WERKGEVERSVRAGEN_DIR, name)
    if not os.path.exists(doel_pad):
        raise HTTPException(status_code=404, detail="Map niet gevonden.")
    background_tasks.add_task(_generate_profile_task, doel_pad)
    return {"message": "Profiel generatie gestart in de achtergrond."}
