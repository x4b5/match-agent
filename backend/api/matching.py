from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import json
from sse_starlette.sse import EventSourceResponse

from backend.config import KANDIDATEN_DIR, WERKGEVERSVRAGEN_DIR
from backend.utils import laad_profiel_uit_map
from backend.services.agents import match_kandidaat, match_kandidaat_stream
from backend.database import bewaar_match

router = APIRouter(prefix="/matching", tags=["Matching"])

class MatchRequest(BaseModel):
    kandidaat_naam: str
    vacature_naam: str
    modus: str = "quick_scan"

def _krijg_profielen(req: MatchRequest):
    cv_pad = os.path.join(KANDIDATEN_DIR, req.kandidaat_naam)
    vac_pad = os.path.join(WERKGEVERSVRAGEN_DIR, req.vacature_naam)
    
    cv_profiel = laad_profiel_uit_map(cv_pad)
    vac_profiel = laad_profiel_uit_map(vac_pad)
    
    if not cv_profiel:
        raise HTTPException(status_code=400, detail=f"Kandidaat profiel niet gevonden voor {req.kandidaat_naam}")
    if not vac_profiel:
        raise HTTPException(status_code=400, detail=f"Vacature profiel niet gevonden voor {req.vacature_naam}")
        
    cv_json = json.dumps(cv_profiel, ensure_ascii=False)
    vac_json = json.dumps(vac_profiel, ensure_ascii=False)
    
    return cv_profiel, vac_profiel, cv_json, vac_json

@router.post("/run")
async def run_match(req: MatchRequest):
    cv_profiel, vac_profiel, cv_json, vac_json = _krijg_profielen(req)
    result = await match_kandidaat(cv_json, vac_json, modus=req.modus)
    
    # Save to db
    kandidaat_id = cv_profiel.get("id", req.kandidaat_naam)
    vacature_id = vac_profiel.get("id", req.vacature_naam)
    vacature_titel = vac_profiel.get("titel", req.vacature_naam)
    
    await bewaar_match(
        kandidaat_naam=req.kandidaat_naam,
        kandidaat_id=kandidaat_id,
        vacature_titel=vacature_titel,
        vacature_id=vacature_id,
        percentage=result.get("match_percentage", 0),
        modus=req.modus,
        resultaat_dict=result
    )
    return {"message": "Match voltooid", "result": result}
    
@router.post("/stream")
async def stream_match(req: MatchRequest):
    cv_profiel, vac_profiel, cv_json, vac_json = _krijg_profielen(req)

    async def event_generator():
        kandidaat_id = cv_profiel.get("id", req.kandidaat_naam)
        vacature_id = vac_profiel.get("id", req.vacature_naam)
        vacature_titel = vac_profiel.get("titel", req.vacature_naam)
        final_result = None

        async for chunk in match_kandidaat_stream(cv_json, vac_json, modus=req.modus):
            if chunk.get("type") == "result":
                final_result = chunk.get("data")
            yield json.dumps(chunk, ensure_ascii=False)
            
        if final_result:
            await bewaar_match(
                kandidaat_naam=req.kandidaat_naam,
                kandidaat_id=kandidaat_id,
                vacature_titel=vacature_titel,
                vacature_id=vacature_id,
                percentage=final_result.get("match_percentage", 0),
                modus=req.modus,
                resultaat_dict=final_result
            )

    return EventSourceResponse(event_generator())
