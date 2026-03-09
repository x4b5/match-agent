from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import json
import time
import logging
from sse_starlette.sse import EventSourceResponse

from backend.config import KANDIDATEN_DIR, WERKGEVERSVRAGEN_DIR, MATCH_MODI, OLLAMA_MODEL

logger = logging.getLogger("matchflix.matching")
from backend.utils import laad_profiel_uit_map
from backend.services.agents import match_kandidaat, match_kandidaat_stream
from backend.database import (
    bewaar_match, haal_top_matches_vector, haal_top_vacatures_vector, haal_document,
    haal_laatste_matches, haal_cached_match, haal_alle_documenten
)
from backend.services.llm_instance import get_provider

router = APIRouter(prefix="/matching", tags=["Matching"])


class SemanticSearchRequest(BaseModel):
    vacature_naam: str
    limit: int = 5

class ReverseSearchRequest(BaseModel):
    kandidaat_naam: str
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
    kandidaat_namen: list[str] | None = None


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

@router.post("/reverse-search")
async def reverse_search(req: ReverseSearchRequest):
    """Reverse matching: bij welke vacatures past deze kandidaat?"""
    cand_doc = await haal_document(req.kandidaat_naam)
    cand_profiel = cand_doc.get("profiel_dict") if cand_doc else None
    
    if not cand_profiel:
        cand_pad = os.path.join(KANDIDATEN_DIR, req.kandidaat_naam)
        cand_profiel = laad_profiel_uit_map(cand_pad)
    
    if not cand_profiel:
        raise HTTPException(status_code=400, detail=f"Kandidaat profiel niet gevonden voor {req.kandidaat_naam}")
    
    cand_json = json.dumps(cand_profiel, ensure_ascii=False)
    vector = await get_provider().generate_embedding(cand_json)
    
    # Skills tekst
    skills_delen = []
    if "hard_skills" in cand_profiel: skills_delen.extend(cand_profiel["hard_skills"])
    if "soft_skills" in cand_profiel: skills_delen.extend(cand_profiel["soft_skills"])
    if "kwaliteiten" in cand_profiel: skills_delen.extend(cand_profiel["kwaliteiten"])
    if "taken" in cand_profiel: skills_delen.extend(cand_profiel["taken"])
    if "kernrol" in cand_profiel: skills_delen.append(cand_profiel["kernrol"])
    skills_tekst = " ".join(filter(None, skills_delen))
    vector_skills = await get_provider().generate_embedding(skills_tekst) if skills_tekst else None
    
    # Cultuur tekst
    cultuur_delen = []
    if "persoonlijkheid" in cand_profiel: cultuur_delen.extend(cand_profiel["persoonlijkheid"])
    if "drijfveren" in cand_profiel: cultuur_delen.extend(cand_profiel["drijfveren"])
    if "gewenste_bedrijfscultuur" in cand_profiel: cultuur_delen.append(cand_profiel["gewenste_bedrijfscultuur"])
    if "organisatiewaarden" in cand_profiel: cultuur_delen.extend(cand_profiel["organisatiewaarden"])
    cultuur_tekst = " ".join(filter(None, cultuur_delen))
    vector_cultuur = await get_provider().generate_embedding(cultuur_tekst) if cultuur_tekst else None
    
    if not vector:
        raise HTTPException(status_code=500, detail="Kon geen embedding genereren.")
    
    top_vacatures = await haal_top_vacatures_vector(
        kandidaat_vector=vector, 
        kandidaat_skills=vector_skills,
        kandidaat_cultuur=vector_cultuur,
        limit=req.limit
    )
    
    enriched = []
    for vac in top_vacatures:
        doc = await haal_document(vac["naam"])
        profiel = doc.get("profiel_dict") if doc else None
        if not profiel:
            vac_pad = os.path.join(WERKGEVERSVRAGEN_DIR, vac["naam"])
            profiel = laad_profiel_uit_map(vac_pad)
        if profiel:
            enriched.append({
                "vacature_naam": vac["naam"],
                "score": vac["score"],
                "percentage": vac["percentage"],
                "sub_scores": vac.get("sub_scores", {}),
                "titel": profiel.get("titel", "Onbekend"),
                "organisatie": profiel.get("organisatie", "Onbekend"),
            })
    
    return {"message": "Reverse search voltooid", "matches": enriched}



# --- Semantic Search ---

@router.post("/semantic-search")
async def semantic_search(req: SemanticSearchRequest):
    vac_profiel = await _krijg_profiel(req.vacature_naam, is_kandidaat=False)

    if not vac_profiel:
        raise HTTPException(status_code=400, detail=f"Vacature profiel niet gevonden voor {req.vacature_naam}")

    vac_json = json.dumps(vac_profiel, ensure_ascii=False)
    vector = await get_provider().generate_embedding(vac_json)
    
    # Skills tekst
    skills_delen = []
    if "hard_skills" in vac_profiel: skills_delen.extend(vac_profiel["hard_skills"])
    if "must_have_skills" in vac_profiel: skills_delen.extend(vac_profiel["must_have_skills"])
    if "benodigde_kwaliteiten" in vac_profiel: skills_delen.extend(vac_profiel["benodigde_kwaliteiten"])
    if "taken" in vac_profiel: skills_delen.extend(vac_profiel["taken"])
    if "titel" in vac_profiel: skills_delen.append(vac_profiel["titel"])
    skills_tekst = " ".join(filter(None, skills_delen))
    vector_skills = await get_provider().generate_embedding(skills_tekst) if skills_tekst else None
    
    # Cultuur tekst
    cultuur_delen = []
    if "organisatiewaarden" in vac_profiel: cultuur_delen.extend(vac_profiel["organisatiewaarden"])
    if "gezochte_persoonlijkheid" in vac_profiel: cultuur_delen.extend(vac_profiel["gezochte_persoonlijkheid"])
    if "team_en_cultuur" in vac_profiel: cultuur_delen.append(vac_profiel["team_en_cultuur"])
    cultuur_tekst = " ".join(filter(None, cultuur_delen))
    vector_cultuur = await get_provider().generate_embedding(cultuur_tekst) if cultuur_tekst else None

    if not vector:
        raise HTTPException(status_code=500, detail="Kon geen embedding genereren voor vacature.")

    top_matches = await haal_top_matches_vector(
        vacature_vector=vector, 
        vacature_skills=vector_skills,
        vacature_cultuur=vector_cultuur,
        limit=req.limit
    )

    enriched_matches = []
    for match in top_matches:
        profiel = await _krijg_profiel(match["naam"], is_kandidaat=True)
        if profiel:
            enriched_matches.append({
                "kandidaat_naam": match["naam"],
                "score": match["score"],
                "percentage": match["percentage"],
                "sub_scores": match.get("sub_scores", {}),
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
    
    # Track duration en model
    start_time = time.time()
    modi = MATCH_MODI.get(req.modus)
    model_versie = (modi.get("model_override") if modi else None) or OLLAMA_MODEL
    
    result = await match_kandidaat(cv_json, vac_json, modus=req.modus)
    duur_ms = int((time.time() - start_time) * 1000)

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
        resultaat_dict=result,
        model_versie=model_versie,
        duur_ms=duur_ms,
        temperature=modi.get("temperature") if modi else None
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

        modi = MATCH_MODI.get(req.modus, {})
        stappen = modi.get("stappen", ["kern"])
        yield json.dumps({"type": "phase", "data": "profielen_geladen", "stappen": stappen}, ensure_ascii=False)

        async for chunk in match_kandidaat_stream(cv_json, vac_json, modus=req.modus):
            if chunk.get("type") == "result":
                final_result = chunk.get("data")
            yield json.dumps(chunk, ensure_ascii=False)

        if final_result:
            modi = MATCH_MODI.get(req.modus)
            await bewaar_match(
                kandidaat_naam=req.kandidaat_naam,
                kandidaat_id=kandidaat_id,
                vacature_titel=vacature_titel,
                vacature_id=vacature_id,
                percentage=final_result.get("match_percentage", 0),
                modus=req.modus,
                resultaat_dict=final_result,
                temperature=modi.get("temperature") if modi else None
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

        if req.kandidaat_namen:
            kandidaten_lijst = req.kandidaat_namen
        # Stap 1: Pre-filter met embeddings als gewenst
        elif req.use_prefilter:
            vector = await get_provider().generate_embedding(vac_json)
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
            ]
            if not req.kandidaat_namen:
                kandidaten_lijst = kandidaten_lijst[:req.limit]

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

                    modi = MATCH_MODI.get(req.modus)
                    await bewaar_match(
                        kandidaat_naam=naam,
                        kandidaat_id=kandidaat_id,
                        vacature_titel=vacature_titel,
                        vacature_id=vacature_id,
                        percentage=result.get("match_percentage", 0),
                        modus=req.modus,
                        resultaat_dict=result,
                        temperature=modi.get("temperature") if modi else None
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
