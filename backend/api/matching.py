from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import json
from sse_starlette.sse import EventSourceResponse

from backend.config import KANDIDATEN_DIR, WERKGEVERSVRAGEN_DIR
from backend.utils import laad_profiel_uit_map
from backend.services.agents import match_kandidaat, match_kandidaat_stream
from backend.database import (
    bewaar_match, haal_top_matches_vector, haal_document,
    haal_laatste_matches, haal_cached_match, haal_alle_documenten
)
from backend.services.ollama_service import genereer_embedding

router = APIRouter(prefix="/matching", tags=["Matching"])


class SemanticSearchRequest(BaseModel):
    vacature_naam: str
    limit: int = 5


class MatchRequest(BaseModel):
    kandidaat_naam: str
    vacature_naam: str
    modus: str = "quick_scan"
    force_refresh: bool = False


class BatchMatchRequest(BaseModel):
    vacature_naam: str
    modus: str = "quick_scan"
    limit: int = 10
    use_prefilter: bool = True
    force_refresh: bool = False


async def _krijg_profiel(naam: str, is_kandidaat: bool = True):
    """Haal profiel op uit DB of filesystem."""
    doc = await haal_document(naam)
    profiel = doc.get("profiel_dict") if doc else None

    if not profiel:
        basis_dir = KANDIDATEN_DIR if is_kandidaat else WERKGEVERSVRAGEN_DIR
        pad = os.path.join(basis_dir, naam)
        profiel = laad_profiel_uit_map(pad)

    return profiel


async def _krijg_profielen(req: MatchRequest):
    cv_profiel = await _krijg_profiel(req.kandidaat_naam, is_kandidaat=True)
    vac_profiel = await _krijg_profiel(req.vacature_naam, is_kandidaat=False)

    if not cv_profiel:
        raise HTTPException(status_code=400, detail=f"Kandidaat profiel niet gevonden voor {req.kandidaat_naam}")
    if not vac_profiel:
        raise HTTPException(status_code=400, detail=f"Vacature profiel niet gevonden voor {req.vacature_naam}")

    cv_json = json.dumps(cv_profiel, ensure_ascii=False)
    vac_json = json.dumps(vac_profiel, ensure_ascii=False)

    return cv_profiel, vac_profiel, cv_json, vac_json


# --- Match Historie ---

@router.get("/history")
async def match_history(limit: int = 100):
    matches = await haal_laatste_matches(limit)
    resultaat = []
    for m in matches:
        entry = {
            "id": m.get("id"),
            "timestamp": m.get("timestamp"),
            "kandidaat_naam": m.get("kandidaat_naam"),
            "vacature_titel": m.get("vacature_titel"),
            "match_percentage": m.get("match_percentage"),
            "modus": m.get("modus"),
        }
        if m.get("resultaat_json"):
            try:
                entry["resultaat"] = json.loads(m["resultaat_json"])
            except (json.JSONDecodeError, TypeError):
                entry["resultaat"] = None
        else:
            entry["resultaat"] = None
        resultaat.append(entry)
    return resultaat


# --- Semantic Search ---

@router.post("/semantic-search")
async def semantic_search(req: SemanticSearchRequest):
    vac_profiel = await _krijg_profiel(req.vacature_naam, is_kandidaat=False)

    if not vac_profiel:
        raise HTTPException(status_code=400, detail=f"Vacature profiel niet gevonden voor {req.vacature_naam}")

    vac_json = json.dumps(vac_profiel, ensure_ascii=False)
    vector = await genereer_embedding(vac_json)

    if not vector:
        raise HTTPException(status_code=500, detail="Kon geen embedding genereren voor vacature.")

    top_matches = await haal_top_matches_vector(vector, limit=req.limit)

    enriched_matches = []
    for match in top_matches:
        profiel = await _krijg_profiel(match["naam"], is_kandidaat=True)
        if profiel:
            enriched_matches.append({
                "kandidaat_naam": match["naam"],
                "score": match["score"],
                "percentage": match["percentage"],
                "kernrol": profiel.get("kernrol", "Onbekend"),
                "kwaliteiten": profiel.get("kwaliteiten", [])
            })

    return {"message": "Semantic search voltooid", "matches": enriched_matches}


# --- Enkele Match ---

@router.post("/run")
async def run_match(req: MatchRequest):
    # Cache check
    if not req.force_refresh:
        cached = await haal_cached_match(req.kandidaat_naam, req.vacature_naam, req.modus)
        if cached and cached.get("resultaat_dict"):
            return {"message": "Match voltooid (cache)", "result": cached["resultaat_dict"], "cached": True}

    cv_profiel, vac_profiel, cv_json, vac_json = await _krijg_profielen(req)
    result = await match_kandidaat(cv_json, vac_json, modus=req.modus)

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


# --- Streaming Match (enkele kandidaat) ---

@router.post("/stream")
async def stream_match(req: MatchRequest):
    # Cache check
    if not req.force_refresh:
        cached = await haal_cached_match(req.kandidaat_naam, req.vacature_naam, req.modus)
        if cached and cached.get("resultaat_dict"):
            async def cached_generator():
                yield json.dumps({"type": "result", "data": cached["resultaat_dict"], "cached": True}, ensure_ascii=False)
            return EventSourceResponse(cached_generator())

    cv_profiel, vac_profiel, cv_json, vac_json = await _krijg_profielen(req)

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


# --- Batch Match (meerdere kandidaten tegen één vacature) ---

@router.post("/batch")
async def batch_match(req: BatchMatchRequest):
    vac_profiel = await _krijg_profiel(req.vacature_naam, is_kandidaat=False)
    if not vac_profiel:
        raise HTTPException(status_code=400, detail=f"Vacature profiel niet gevonden voor {req.vacature_naam}")

    vac_json = json.dumps(vac_profiel, ensure_ascii=False)
    vacature_id = vac_profiel.get("id", req.vacature_naam)
    vacature_titel = vac_profiel.get("titel", req.vacature_naam)

    async def batch_generator():
        kandidaten_lijst = []

        # Stap 1: Pre-filter met embeddings als gewenst
        if req.use_prefilter:
            vector = await genereer_embedding(vac_json)
            if vector:
                top = await haal_top_matches_vector(vector, limit=req.limit)
                kandidaten_lijst = [m["naam"] for m in top]
                yield json.dumps({
                    "type": "prefilter",
                    "data": [{"naam": m["naam"], "percentage": m["percentage"]} for m in top]
                }, ensure_ascii=False)

        # Fallback: alle kandidaten met profiel
        if not kandidaten_lijst:
            alle_docs = await haal_alle_documenten("kandidaat")
            kandidaten_lijst = [
                d["naam"] for d in alle_docs
                if d.get("profiel_dict")
            ][:req.limit]

        total = len(kandidaten_lijst)
        alle_resultaten = []

        # Stap 2: Match elke kandidaat
        for idx, naam in enumerate(kandidaten_lijst):
            yield json.dumps({
                "type": "match_start",
                "data": {"naam": naam, "index": idx + 1, "total": total}
            }, ensure_ascii=False)

            # Cache check
            if not req.force_refresh:
                cached = await haal_cached_match(naam, req.vacature_naam, req.modus)
                if cached and cached.get("resultaat_dict"):
                    result = cached["resultaat_dict"]
                    alle_resultaten.append({"naam": naam, **result, "cached": True})
                    yield json.dumps({
                        "type": "match_result",
                        "data": {"naam": naam, "result": result, "cached": True}
                    }, ensure_ascii=False)
                    continue

            cv_profiel = await _krijg_profiel(naam, is_kandidaat=True)
            if not cv_profiel:
                continue

            cv_json = json.dumps(cv_profiel, ensure_ascii=False)
            kandidaat_id = cv_profiel.get("id", naam)

            # Stream tokens per kandidaat
            volledig = ""
            async for chunk in match_kandidaat_stream(cv_json, vac_json, modus=req.modus):
                if chunk.get("type") == "token":
                    volledig += chunk.get("data", "")
                    yield json.dumps({
                        "type": "token",
                        "data": chunk.get("data", ""),
                        "kandidaat": naam
                    }, ensure_ascii=False)
                elif chunk.get("type") == "result":
                    result = chunk.get("data", {})
                    alle_resultaten.append({"naam": naam, **result})

                    await bewaar_match(
                        kandidaat_naam=naam,
                        kandidaat_id=kandidaat_id,
                        vacature_titel=vacature_titel,
                        vacature_id=vacature_id,
                        percentage=result.get("match_percentage", 0),
                        modus=req.modus,
                        resultaat_dict=result
                    )

                    yield json.dumps({
                        "type": "match_result",
                        "data": {"naam": naam, "result": result}
                    }, ensure_ascii=False)

        # Stap 3: Gesorteerd eindresultaat
        alle_resultaten.sort(key=lambda x: x.get("match_percentage", 0), reverse=True)
        yield json.dumps({
            "type": "batch_complete",
            "data": alle_resultaten
        }, ensure_ascii=False)

    return EventSourceResponse(batch_generator())
