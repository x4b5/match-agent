from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import os
import json
import time
import logging
import asyncio
from sse_starlette.sse import EventSourceResponse

from backend.config import KANDIDATEN_DIR, WERKGEVERSVRAGEN_DIR, MATCH_MODI, OLLAMA_MODEL

logger = logging.getLogger("matchflix.matching")
from backend.utils import laad_profiel_uit_map
from backend.services.agents import match_kandidaat, match_kandidaat_stream, genereer_embeddings_batch
from backend.database import (
    bewaar_match, haal_top_matches_vector, haal_top_vacatures_vector, haal_document,
    haal_laatste_matches, haal_cached_match, haal_alle_documenten,
    bewaar_recruiter_rating, tel_onverwerkte_ratings, haal_learning_weights
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
    
    # Skills tekst (kunnen + kernrol)
    skills_tekst = cand_profiel.get("kunnen", "")
    if cand_profiel.get("kernrol"):
        skills_tekst += " " + cand_profiel["kernrol"]

    # Cultuur tekst (zijn + willen)
    cultuur_tekst = f"{cand_profiel.get('zijn', '')} {cand_profiel.get('willen', '')}"

    # Parallelle embedding generatie
    vector, vector_skills, vector_cultuur = await genereer_embeddings_batch([cand_json, skills_tekst, cultuur_tekst])
    
    if not vector:
        raise HTTPException(status_code=500, detail="Kon geen embedding genereren.")
    
    gewichten = await haal_learning_weights()
    top_vacatures = await haal_top_vacatures_vector(
        kandidaat_vector=vector,
        kandidaat_skills=vector_skills,
        kandidaat_cultuur=vector_cultuur,
        limit=req.limit,
        gewichten=gewichten
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
    
    # Skills tekst (kunnen + titel)
    skills_tekst = f"{vac_profiel.get('kunnen', '')} {vac_profiel.get('titel', '')}".strip()

    # Cultuur tekst (zijn + willen)
    cultuur_tekst = f"{vac_profiel.get('zijn', '')} {vac_profiel.get('willen', '')}".strip()

    # Parallelle embedding generatie
    from backend.services.agents import genereer_embeddings_batch
    vector, vector_skills, vector_cultuur = await genereer_embeddings_batch([vac_json, skills_tekst, cultuur_tekst])

    if not vector:
        raise HTTPException(status_code=500, detail="Kon geen embedding genereren voor vacature.")

    gewichten = await haal_learning_weights()
    top_matches = await haal_top_matches_vector(
        vacature_vector=vector,
        vacature_skills=vector_skills,
        vacature_cultuur=vector_cultuur,
        limit=req.limit,
        gewichten=gewichten
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
                "kunnen": profiel.get("kunnen", "")
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

class FeedbackRequest(BaseModel):
    match_id: int
    feedback_tekst: str = ""
    recruiter_rating: int | None = Field(default=None, ge=1, le=5)
    feedback_categorieen: list[str] = []

@router.post("/feedback")
async def match_feedback(req: FeedbackRequest):
    from backend.services.agents import verwerk_match_feedback, optimaliseer_systeem_gewichten
    from backend.database import bewaar_match_feedback

    # 1. Sla recruiter-rating op (indien meegegeven)
    if req.recruiter_rating is not None:
        await bewaar_recruiter_rating(req.match_id, req.recruiter_rating)

    # 2. Combineer categorieën met feedback-tekst
    feedback_tekst = req.feedback_tekst
    if req.feedback_categorieen:
        categorie_prefix = "[Categorieën: " + ", ".join(req.feedback_categorieen) + "] "
        feedback_tekst = categorie_prefix + feedback_tekst

    # 3. Verwerk feedback-tekst met AI (alleen bij niet-lege tekst)
    nieuw_profiel = None
    if feedback_tekst.strip():
        await bewaar_match_feedback(req.match_id, feedback_tekst)
        try:
            nieuw_profiel = await verwerk_match_feedback(req.match_id, feedback_tekst)
        except Exception as e:
            logger.error(f"Fout bij verwerken feedback: {e}")
            if req.recruiter_rating is None:
                return {"message": "Feedback opgeslagen, maar verwerking mislukt door technische fout.", "detail": str(e)}

    # 4. Trigger gewichtsoptimalisatie als er genoeg onverwerkte ratings zijn
    try:
        onverwerkt = await tel_onverwerkte_ratings()
        if onverwerkt >= 10:
            await optimaliseer_systeem_gewichten()
    except Exception as e:
        logger.error(f"Fout bij gewichtsoptimalisatie: {e}")

    if nieuw_profiel:
        return {"message": "Feedback verwerkt en kandidaat- en werkgeversprofiel verrijkt", "nieuw_profiel": nieuw_profiel}
    elif req.recruiter_rating is not None:
        return {"message": f"Beoordeling ({req.recruiter_rating} sterren) opgeslagen"}
    else:
        return {"message": "Geen feedback of rating ontvangen"}


# --- Gewichten ---

@router.get("/weights")
async def get_weights():
    """Retourneert de huidige learning weights."""
    gewichten = await haal_learning_weights()
    return {"weights": gewichten}


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
                gewichten = await haal_learning_weights()
                top = await haal_top_matches_vector(vector, limit=req.limit, gewichten=gewichten)
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

        # Stap 2: Match elke kandidaat (Parallel met Semaphore)
        sem = asyncio.Semaphore(3) # Max 3 parallelle matches voor Ollama

        async def worker(naam, idx):
            async with sem:
                yield_json = lambda t, d: json.dumps({"type": t, "data": d}, ensure_ascii=False)
                
                # Start event
                start_evt = {"type": "match_start", "data": {"naam": naam, "index": idx + 1, "total": total}}
                # We can't yield from here easily to the outer generator, 
                # so we return the result and the caller yields.
                # Actually, better to just use a list of tasks.
                
                # Cache check
                if not req.force_refresh:
                    cached = await haal_cached_match(naam, req.vacature_naam, req.modus)
                    if cached and cached.get("resultaat_dict"):
                        return {"naam": naam, "result": cached["resultaat_dict"], "cached": True}

                cv_profiel = await _krijg_profiel(naam, is_kandidaat=True)
                if not cv_profiel:
                    return None

                cv_json = json.dumps(cv_profiel, ensure_ascii=False)
                kandidaat_id = cv_profiel.get("id", naam)

                try:
                    result = await match_kandidaat(cv_json, vac_json, modus=req.modus)
                    
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
                    return {"naam": naam, "result": result, "cached": False}
                except Exception as e:
                    logger.error(f"Fout bij matchen van {naam}: {e}")
                    return {"naam": naam, "error": str(e)}

        # We draaien de tasks en yielden updates wanneer ze klaar zijn
        tasks = [worker(naam, i) for i, naam in enumerate(kandidaten_lijst)]
        for fut in asyncio.as_completed(tasks):
            res = await fut
            if res:
                if "error" in res:
                    yield json.dumps({"type": "error", "data": f"Fout bij {res['naam']}: {res['error']}"}, ensure_ascii=False)
                else:
                    alle_resultaten.append({"naam": res["naam"], **res["result"], "cached": res.get("cached", False)})
                    yield json.dumps({
                        "type": "match_result",
                        "data": {"naam": res["naam"], "result": res["result"], "cached": res.get("cached", False)}
                    }, ensure_ascii=False)

        # Stap 3: Gesorteerd eindresultaat
        alle_resultaten.sort(key=lambda x: x.get("match_percentage", 0), reverse=True)
        yield json.dumps({
            "type": "batch_complete",
            "data": alle_resultaten
        }, ensure_ascii=False)

    return EventSourceResponse(batch_generator())
