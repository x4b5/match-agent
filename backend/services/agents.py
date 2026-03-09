import json
import os
import uuid
import datetime
import logging
import traceback
from backend.config import (
    PROFIEL_KANDIDAAT_PROMPT,
    PROFIEL_WERKGEVERSVRAAG_PROMPT,
    VERRIJK_KANDIDAAT_PROMPT,
    VERRIJK_WERKGEVERSVRAAG_PROMPT,
    PROFIEL_MODEL,
    MATCH_MODI,
    OLLAMA_MODEL,
    KERN_MATCH_PROMPT,
    VERDIEPING_MATCH_PROMPT,
    MATCH_PROMPT
)
from backend.services.llm_instance import get_provider
from backend.services.ollama_service import OllamaError
from backend.database import bewaar_embedding
from backend.schemas import (
    KandidaatProfiel,
    WerkgeversvraagProfiel,
    KernMatchResult,
    VerdiepingMatchResult,
    QuickScanMatchResult,
    StandaardMatchResult
)

logger = logging.getLogger("matchflix.agents")


async def genereer_embedding(tekst: str) -> list[float]:
    """Wrapper voor embedding generatie via de actieve LLM-provider."""
    return await get_provider().generate_embedding(tekst)


async def profileer_kandidaat(tekst: str) -> dict:
    prompt = PROFIEL_KANDIDAAT_PROMPT.format(tekst=tekst)
    result = await get_provider().generate_json(PROFIEL_MODEL, prompt, schema=KandidaatProfiel, temperature=0.1)
    return result.model_dump() if hasattr(result, "model_dump") else result

async def profileer_werkgeversvraag(tekst: str) -> dict:
    prompt = PROFIEL_WERKGEVERSVRAAG_PROMPT.format(tekst=tekst)
    result = await get_provider().generate_json(PROFIEL_MODEL, prompt, schema=WerkgeversvraagProfiel, temperature=0.1)
    return result.model_dump() if hasattr(result, "model_dump") else result

async def verrijk_kandidaat_profiel(profiel_json: str, antwoorden_json: str, ruwe_tekst: str) -> dict:
    prompt = VERRIJK_KANDIDAAT_PROMPT.format(
        profiel_json=profiel_json,
        antwoorden_json=antwoorden_json,
        ruwe_tekst=ruwe_tekst
    )
    result = await get_provider().generate_json(PROFIEL_MODEL, prompt, schema=KandidaatProfiel, temperature=0.1)
    return result.model_dump() if hasattr(result, "model_dump") else result

async def verrijk_werkgeversvraag_profiel(profiel_json: str, antwoorden_json: str, ruwe_tekst: str) -> dict:
    prompt = VERRIJK_WERKGEVERSVRAAG_PROMPT.format(
        profiel_json=profiel_json,
        antwoorden_json=antwoorden_json,
        ruwe_tekst=ruwe_tekst
    )
    result = await get_provider().generate_json(PROFIEL_MODEL, prompt, schema=WerkgeversvraagProfiel, temperature=0.1)
    return result.model_dump() if hasattr(result, "model_dump") else result

def _verkort_tekst(tekst: str, max_lengte: int) -> tuple[str, bool]:
    if len(tekst) <= max_lengte:
        return tekst, False
    try:
        data = json.loads(tekst)
        compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        if len(compact) <= max_lengte:
            return compact, False
        return compact, True
    except (json.JSONDecodeError, ValueError):
        pass
    return tekst, True

def _modus_params(modus: str | None) -> dict:
    modi = MATCH_MODI.get(modus) if modus else None
    return {
        "prompt_template": modi["prompt"] if modi else KERN_MATCH_PROMPT,
        "temperature": modi["temperature"] if modi else 0.3,
        "num_predict": modi["num_predict"] if modi else 2048,
        "num_ctx": modi.get("num_ctx", 8192) if modi else 8192,
        "model_override": modi.get("model_override") if modi else None,
        "max_tekst_lengte": modi.get("max_tekst_lengte") if modi else None,
        "think": modi.get("think", False) if modi else False,
        "stappen": modi.get("stappen", ["kern"]) if modi else ["kern"],
    }


async def _doe_kern_match(model: str, cv_tekst: str, vacature_tekst: str, params: dict) -> dict:
    """Stap 1: kern-match met 8 velden."""
    prompt = params["prompt_template"].format(cv_tekst=cv_tekst, vacature_tekst=vacature_tekst)
    result = await get_provider().generate_json(
        model=model,
        prompt=prompt,
        schema=KernMatchResult,
        temperature=params["temperature"],
        num_predict=params["num_predict"],
        num_ctx=params["num_ctx"],
        think=params["think"]
    )
    return result.model_dump() if hasattr(result, "model_dump") else result

async def _doe_verdieping(model: str, kern_result: dict, cv_tekst: str, vacature_tekst: str, params: dict) -> dict:
    """Stap 2: verdieping met kern-resultaat als context."""
    kern_json = json.dumps(kern_result, ensure_ascii=False)
    prompt = VERDIEPING_MATCH_PROMPT.format(
        kern_json=kern_json,
        cv_tekst=cv_tekst,
        vacature_tekst=vacature_tekst
    )
    result = await get_provider().generate_json(
        model=model,
        prompt=prompt,
        schema=VerdiepingMatchResult,
        temperature=params["temperature"],
        num_predict=params["num_predict"],
        num_ctx=params["num_ctx"],
        think=params["think"]
    )
    return result.model_dump() if hasattr(result, "model_dump") else result


async def match_kandidaat(cv_tekst: str, vacature_tekst: str, modus: str | None = None) -> dict:
    params = _modus_params(modus)
    if params["max_tekst_lengte"]:
        cv_tekst, _ = _verkort_tekst(cv_tekst, params["max_tekst_lengte"])
        vacature_tekst, _ = _verkort_tekst(vacature_tekst, params["max_tekst_lengte"])

    model = params["model_override"] or OLLAMA_MODEL
    stappen = params["stappen"]

    # Stap 1: Kern-match
    kern_result = await _doe_kern_match(model, cv_tekst, vacature_tekst, params)
    if "match_percentage" in kern_result:
        kern_result["match_percentage"] = int(round(kern_result.get("match_percentage", 0)))

    # Stap 2: Verdieping (indien modus dit vereist)
    if "verdieping" in stappen:
        try:
            verdieping = await _doe_verdieping(model, kern_result, cv_tekst, vacature_tekst, params)
            # Merge: kern + verdieping = volledig resultaat
            kern_result.update(verdieping)
        except OllamaError as e:
            logger.warning(f"Verdieping mislukt, kern-resultaat wordt geretourneerd: {e}")
            kern_result["_waarschuwing"] = "Verdieping kon niet worden gegenereerd. Kern-analyse is beschikbaar."

    return kern_result


async def match_kandidaat_stream(cv_tekst: str, vacature_tekst: str, modus: str | None = None):
    params = _modus_params(modus)
    if params["max_tekst_lengte"]:
        cv_tekst, cv_afgekapt = _verkort_tekst(cv_tekst, params["max_tekst_lengte"])
        vacature_tekst, vac_afgekapt = _verkort_tekst(vacature_tekst, params["max_tekst_lengte"])
        if cv_afgekapt or vac_afgekapt:
            yield {"type": "warning", "data": "Profiel te lang voor quick scan modus."}

    model = params["model_override"] or OLLAMA_MODEL
    stappen = params["stappen"]

    # Stap 1: Kern-match (streamed)
    yield {"type": "phase", "data": "kern_analyse"}
    kern_schema = KernMatchResult
    volledig_antwoord = ""
    async for chunk in get_provider().generate_json_stream(
        model=model,
        prompt=params["prompt_template"].format(cv_tekst=cv_tekst, vacature_tekst=vacature_tekst),
        schema=kern_schema,
        temperature=params["temperature"],
        num_predict=params["num_predict"],
        num_ctx=params["num_ctx"],
        think=params["think"]
    ):
        if chunk.get("type") == "error":
            yield chunk
            return
        fragment = chunk.get("data", "")
        if fragment:
            volledig_antwoord += fragment
        yield chunk

    from backend.services.ollama_service import _validate_json_antwoord, _extract_json_from_thinking  # noqa: E402

    if params["think"]:
        volledig_antwoord = _extract_json_from_thinking(volledig_antwoord)
    kern_result = _validate_json_antwoord(volledig_antwoord, kern_schema)

    if not kern_result:
        yield {"type": "error", "data": "Kon kern-match JSON niet parsen uit streaming output."}
        return

    if "match_percentage" in kern_result:
        kern_result["match_percentage"] = int(round(kern_result["match_percentage"]))

    # Stap 2: Verdieping (niet-streamed, maar resultaat wordt meegegeven)
    if "verdieping" in stappen:
        yield {"type": "phase", "data": "verdieping"}
        try:
            verdieping = await _doe_verdieping(model, kern_result, cv_tekst, vacature_tekst, params)
            kern_result.update(verdieping)
        except OllamaError as e:
            logger.warning(f"Verdieping mislukt bij stream: {e}")
            kern_result["_waarschuwing"] = "Verdieping kon niet worden gegenereerd."

    yield {"type": "result", "data": kern_result}


def extract_text_sync(map_pad: str) -> tuple[str, list[str]]:
    """Synchronous file IO block for reading documents, run via executor in FastAPI"""
    if not os.path.isdir(map_pad):
        return "", [f"{map_pad} is geen geldige map."]

    gecombineerde_tekst = ""
    waarschuwingen = []

    baseless_bestanden = os.listdir(map_pad)
    tekst_extensies = (".txt", ".md", ".csv", ".eml", ".json", ".log", ".rtf")
    verwerkbare_bestanden = [f for f in baseless_bestanden if f.lower().endswith(tekst_extensies) or f.lower().endswith(".docx") or f.lower().endswith(".pdf")]

    for doc in sorted(verwerkbare_bestanden):
        pad = os.path.join(map_pad, doc)
        gecombineerde_tekst += f"\n\n--- Inhoud uit {doc} ---\n\n"
        try:
            if doc.lower().endswith(tekst_extensies):
                with open(pad, "r", encoding="utf-8") as f:
                    gecombineerde_tekst += f.read()
            elif doc.endswith(".docx"):
                try:
                    from docx import Document
                    document = Document(pad)
                    voor_docx = "\n".join([p.text for p in document.paragraphs])
                    gecombineerde_tekst += voor_docx
                except ImportError:
                    waarschuwingen.append(f"python-docx module ontbreekt — {doc} overgeslagen.")
                except Exception as e:
                    waarschuwingen.append(f"Kon {doc} niet lezen: {e}")
            elif doc.endswith(".pdf"):
                try:
                    import pypdf
                    reader = pypdf.PdfReader(pad)
                    voor_pdf = ""
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            voor_pdf += text + "\n"
                    gecombineerde_tekst += voor_pdf
                except ImportError:
                    waarschuwingen.append(f"pypdf module ontbreekt — {doc} overgeslagen.")
                except Exception as e:
                    waarschuwingen.append(f"Kon {doc} niet lezen: {e}")
        except Exception as e:
            waarschuwingen.append(f"Kon {doc} niet lezen: {e}")

    return gecombineerde_tekst, waarschuwingen

async def verwerk_match_feedback(match_id: int, feedback_tekst: str) -> dict:
    """Verwerkt feedback op een match en werkt het kandidaatprofiel bij."""
    from backend.database import _get_connection, update_profiel_na_verrijking, bewaar_embedding
    from backend.config import VERWERK_MATCH_FEEDBACK_PROMPT, PROFIEL_MODEL, KANDIDATEN_DIR
    from backend.utils import opslaan_profiel

    conn = await _get_connection()
    try:
        # 1. Haal match en bijbehorend profiel op
        cursor = await conn.execute("""
            SELECT m.resultaat_json, d.document_id, d.profiel_json, d.naam
            FROM matches m
            JOIN documenten d ON d.naam = m.kandidaat_naam
            WHERE m.id = ?
        """, (match_id,))
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Match met ID {match_id} niet gevonden of geen bijbehorend document.")

        match_json = row[0]
        doc_id = row[1]
        profiel_json = row[2]
        naam = row[3]

        # 2. Laat LLM het profiel bijwerken op basis van feedback
        prompt = VERWERK_MATCH_FEEDBACK_PROMPT.format(
            profiel_json=profiel_json,
            match_json=match_json,
            feedback_tekst=feedback_tekst
        )
        
        result = await get_provider().generate_json(PROFIEL_MODEL, prompt, schema=KandidaatProfiel, temperature=0.1)
        nieuw_profiel = result.model_dump() if hasattr(result, "model_dump") else result

        # 3. Update profiel in database
        versie_info = await update_profiel_na_verrijking(doc_id, nieuw_profiel)

        # 4. Synchroniseer met iCloud JSON bestand
        doel_pad = os.path.join(KANDIDATEN_DIR, naam)
        if os.path.exists(doel_pad):
            opslaan_profiel(doel_pad, nieuw_profiel)

        # 5. Herbereken embeddings (Echt leren!)
        try:
            full_text = json.dumps(nieuw_profiel, ensure_ascii=False)
            vector = await genereer_embedding(full_text)
            
            skills_tekst = ", ".join(nieuw_profiel.get("hard_skills", []) + nieuw_profiel.get("soft_skills", []))
            cultuur_tekst = f"{nieuw_profiel.get('gewenste_bedrijfscultuur', '')} {nieuw_profiel.get('onderliggende_motivatie', '')}"
            
            vec_skills = await genereer_embedding(skills_tekst) if skills_tekst else None
            vec_cultuur = await genereer_embedding(cultuur_tekst) if cultuur_tekst else None
            
            await bewaar_embedding(doc_id, "kandidaat", naam, vector, vec_skills, vec_cultuur)
            logger.info(f"Embeddings herberekened voor {naam} na match-feedback.")
        except Exception as e:
            logger.error(f"Fout bij herberekenen embeddings na feedback voor {naam}: {e}")

        # 6. Markeer feedback als verwerkt
        await conn.execute(
            "UPDATE matches SET feedback_verwerkt = 1 WHERE id = ?",
            (match_id,)
        )
        await conn.commit()

        return nieuw_profiel
    finally:
        await conn.close()
