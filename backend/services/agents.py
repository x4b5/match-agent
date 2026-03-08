import json
import os
import uuid
import datetime
import traceback
from backend.config import (
    PROFIEL_KANDIDAAT_PROMPT,
    PROFIEL_WERKGEVERSVRAAG_PROMPT,
    PROFIEL_MODEL,
    MATCH_MODI,
    OLLAMA_MODEL,
    MATCH_PROMPT
)
from backend.services.ollama_service import (
    genereer_embedding,
    vraag_ollama_json,
    stream_ollama_json,
    OllamaError
)
from backend.database import bewaar_embedding
from backend.schemas import (
    KandidaatProfiel, 
    WerkgeversvraagProfiel, 
    QuickScanMatchResult, 
    StandaardMatchResult
)

async def profileer_kandidaat(tekst: str) -> dict:
    prompt = PROFIEL_KANDIDAAT_PROMPT.format(tekst=tekst)
    return await vraag_ollama_json(PROFIEL_MODEL, prompt, schema=KandidaatProfiel, temperature=0.1)

async def profileer_werkgeversvraag(tekst: str) -> dict:
    prompt = PROFIEL_WERKGEVERSVRAAG_PROMPT.format(tekst=tekst)
    return await vraag_ollama_json(PROFIEL_MODEL, prompt, schema=WerkgeversvraagProfiel, temperature=0.1)

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
        "prompt_template": modi["prompt"] if modi else MATCH_PROMPT,
        "temperature": modi["temperature"] if modi else 0.3,
        "num_predict": modi["num_predict"] if modi else 1024,
        "num_ctx": modi.get("num_ctx", 8192) if modi else 8192,
        "model_override": modi.get("model_override") if modi else None,
        "max_tekst_lengte": modi.get("max_tekst_lengte") if modi else None,
        "think": modi.get("think", False) if modi else False,
    }

async def match_kandidaat(cv_tekst: str, vacature_tekst: str, modus: str | None = None) -> dict:
    params = _modus_params(modus)
    if params["max_tekst_lengte"]:
        cv_tekst, _ = _verkort_tekst(cv_tekst, params["max_tekst_lengte"])
        vacature_tekst, _ = _verkort_tekst(vacature_tekst, params["max_tekst_lengte"])
    
    model = params["model_override"] or OLLAMA_MODEL
    prompt = params["prompt_template"].format(cv_tekst=cv_tekst, vacature_tekst=vacature_tekst)
    
    schema = QuickScanMatchResult if modus == "quick_scan" else StandaardMatchResult
    
    result = await vraag_ollama_json(
        model=model,
        prompt=prompt,
        schema=schema,
        temperature=params["temperature"],
        num_predict=params["num_predict"],
        num_ctx=params["num_ctx"],
        think=params["think"]
    )
    if "match_percentage" in result:
        result["match_percentage"] = int(round(result.get("match_percentage", 0)))
    return result

async def match_kandidaat_stream(cv_tekst: str, vacature_tekst: str, modus: str | None = None):
    params = _modus_params(modus)
    if params["max_tekst_lengte"]:
        cv_tekst, cv_afgekapt = _verkort_tekst(cv_tekst, params["max_tekst_lengte"])
        vacature_tekst, vac_afgekapt = _verkort_tekst(vacature_tekst, params["max_tekst_lengte"])
        if cv_afgekapt or vac_afgekapt:
            yield {"type": "warning", "data": "Profiel te lang voor quick scan modus."}
    
    model = params["model_override"] or OLLAMA_MODEL
    prompt = params["prompt_template"].format(cv_tekst=cv_tekst, vacature_tekst=vacature_tekst)
    
    volledig_antwoord = ""
    async for chunk in stream_ollama_json(
        model=model,
        prompt=prompt,
        temperature=params["temperature"],
        num_predict=params["num_predict"],
        num_ctx=params["num_ctx"],
        think=params["think"]
    ):
        if chunk.get("type") == "error":
            yield chunk
            return
        # buffer the token
        fragment = chunk.get("data", "")
        if fragment:
            volledig_antwoord += fragment
        yield chunk
        
    # after stream, attempt to parse the entire response block to validate format
    from backend.services.ollama_service import _validate_json_antwoord
    
    schema = QuickScanMatchResult if modus == "quick_scan" else StandaardMatchResult
    resultaat = _validate_json_antwoord(volledig_antwoord, schema)
    if resultaat:
        if "match_percentage" in resultaat:
            resultaat["match_percentage"] = int(round(resultaat["match_percentage"]))
        yield {"type": "result", "data": resultaat}
    else:
        yield {"type": "error", "data": "Could not parse JSON from streaming output."}

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
