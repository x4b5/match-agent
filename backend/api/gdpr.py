from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import shutil

from backend.config import KANDIDATEN_DIR, WERKGEVERSVRAGEN_DIR
from backend.database import verwijder_alle_data, haal_document
from backend.utils import zorg_voor_uuid

router = APIRouter(prefix="/gdpr", tags=["GDPR / AVG"])

class VergeetMijRequest(BaseModel):
    naam: str
    doc_type: str  # 'kandidaat' of 'vacature'

@router.post("/vergeet-mij")
async def vergeet_mij(req: VergeetMijRequest):
    """
    AVG/GDPR 'Recht op Vergetelheid' – verwijdert alle data van een persoon/vacature 
    uit de database (documenten, embeddings, matches) en optioneel van de schijf.
    """
    # Zoek het document op via naam
    doc = await haal_document(req.naam)
    
    if not doc:
        raise HTTPException(status_code=404, detail=f"Geen data gevonden voor '{req.naam}'.")
    
    document_id = doc["document_id"]
    
    # Verwijder alle data uit de database
    rapport = await verwijder_alle_data(document_id)
    
    # Verwijder ook de bestanden van de schijf (indien aanwezig)
    if req.doc_type == "kandidaat":
        pad = os.path.join(KANDIDATEN_DIR, req.naam)
    else:
        pad = os.path.join(WERKGEVERSVRAGEN_DIR, req.naam)
    
    bestanden_verwijderd = False
    if os.path.exists(pad):
        try:
            shutil.rmtree(pad)
            bestanden_verwijderd = True
        except Exception as e:
            rapport["fout_bestanden"] = str(e)
    
    rapport["bestanden_verwijderd"] = bestanden_verwijderd
    
    return {
        "message": f"Alle data voor '{req.naam}' is succesvol verwijderd conform AVG/GDPR.",
        "rapport": rapport
    }
