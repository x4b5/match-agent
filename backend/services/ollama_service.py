import aiohttp
import json
import re
import asyncio
import logging
from backend.config import OLLAMA_URL, OLLAMA_EMBED_URL, EMBEDDING_MODEL, SYSTEM_PROMPT

logger = logging.getLogger("matchflix.ollama")

class OllamaError(Exception):
    pass

async def _post_ollama(url: str, payload: dict, timeout=600):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, timeout=timeout) as response:
                response.raise_for_status()
                return await response.json()
        except asyncio.TimeoutError:
            raise OllamaError("Timeout bij Ollama request.")
        except aiohttp.ClientError as e:
            raise OllamaError(f"HTTP of netwerkfout bij verbinding met Ollama: {str(e)}")

async def genereer_embedding(tekst: str) -> list[float]:
    payload = {
        "model": EMBEDDING_MODEL,
        "prompt": tekst,
    }
    result = await _post_ollama(OLLAMA_EMBED_URL, payload, timeout=120)
    return result.get("embedding", [])

from pydantic import BaseModel

def _extract_json_from_thinking(antwoord: str) -> str:
    """Haal het JSON-blok uit een thinking-mode antwoord dat denktekst kan bevatten."""
    # Probeer eerst het volledige antwoord als JSON
    stripped = antwoord.strip()
    if stripped.startswith("{"):
        return stripped
    # Zoek het laatste JSON-blok in de output (na eventuele denktekst)
    matches = list(re.finditer(r'\{[\s\S]*\}', stripped))
    if matches:
        return matches[-1].group()
    return stripped

def _validate_json_antwoord(antwoord: str, schema: BaseModel | None) -> dict | None:
    try:
        data = json.loads(antwoord)
        if schema:
            validated = schema(**data)
            return validated.model_dump()
        return data
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"JSON Parse Error: {e}")
        return None
    except Exception as e:
        logger.warning(f"Pydantic Validation Error for {schema.__name__ if schema else 'Unknown'}: {e}")
        if hasattr(e, 'errors'):
            for err in e.errors():
                logger.warning(f"  - Field {err.get('loc')}: {err.get('msg')} (type={err.get('type')})")
        return None

def _bewaar_debug_output(antwoord: str, poging: int, model: str):
    """Log de ruwe output voor debugging bij herhaalde fouten."""
    logger.error(
        f"Ongeldige JSON na poging {poging + 1} (model={model}). "
        f"Ruwe output ({len(antwoord)} chars): {antwoord[:500]}{'...' if len(antwoord) > 500 else ''}"
    )

async def vraag_ollama_json(model: str, prompt: str, schema: BaseModel | None = None, temperature: float = 0.1, num_predict: int = 2048, num_ctx: int = 8192, think: bool = False, max_retries: int = 2) -> dict:
    # Thinking mode is incompatibel met structured output (Ollama issue #10929).
    # Bij think=True: gebruik format:"json" en parse handmatig met Pydantic.
    use_structured = schema and not think

    payload = {
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
            "seed": 42,
        },
        "think": think,
    }

    if use_structured:
        payload["format"] = schema.model_json_schema()
    else:
        payload["format"] = "json"

    laatste_antwoord = ""
    for poging in range(max_retries + 1):
        try:
            resp = await _post_ollama(OLLAMA_URL, payload, timeout=600)

            # Check of het model gestopt is door token limiet
            if resp.get("done_reason") == "length":
                logger.warning(f"Ollama gestopt door token limiet (poging {poging + 1}, model={model})")

            antwoord = resp.get("response", "")
            laatste_antwoord = antwoord

            # Bij thinking mode: strip denktekst en extract JSON
            if think:
                antwoord = _extract_json_from_thinking(antwoord)

            resultaat = _validate_json_antwoord(antwoord, schema)
            if resultaat:
                return resultaat

            _bewaar_debug_output(antwoord, poging, model)

        except OllamaError as e:
            logger.error(f"Ollama fout poging {poging + 1}: {e}")
            if poging == max_retries:
                raise e

        if poging < max_retries:
            await asyncio.sleep(2 * (poging + 1))

    # Graceful fallback: probeer de ruwe JSON te parsen zonder schema-validatie
    if laatste_antwoord:
        if think:
            laatste_antwoord = _extract_json_from_thinking(laatste_antwoord)
        fallback = _validate_json_antwoord(laatste_antwoord, None)
        if fallback:
            logger.warning(f"Fallback: JSON valide maar voldoet niet aan schema (model={model}). Ruwe data geretourneerd.")
            fallback["_waarschuwing"] = "Profiel voldoet niet volledig aan het verwachte schema. Sommige velden kunnen ontbreken."
            return fallback

    raise OllamaError(
        f"Model {model} gaf geen geldig JSON-antwoord na {max_retries + 1} pogingen. "
        f"Controleer of het model geladen is en voldoende context heeft."
    )

async def stream_ollama_json(model: str, prompt: str, schema: BaseModel | None = None, temperature: float = 0.1, num_predict: int = 2048, num_ctx: int = 8192, think: bool = False):
    # Thinking mode is incompatibel met structured output
    use_structured = schema and not think

    payload = {
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
            "seed": 42,
        },
        "think": think,
    }

    if use_structured:
        payload["format"] = schema.model_json_schema()
    else:
        payload["format"] = "json"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(OLLAMA_URL, json=payload, timeout=600) as response:
                response.raise_for_status()
                async for line in response.content:
                    if line:
                        try:
                            chunk = json.loads(line)

                            if chunk.get("done"):
                                reason = chunk.get("done_reason")
                                if reason == "length":
                                    logger.warning("Ollama stream gestopt door token limiet (length).")
                                elif reason:
                                    logger.debug(f"Ollama stream klaar. Reden: {reason}")

                            fragment = chunk.get("response", "")
                            if fragment:
                                yield {"type": "token", "data": fragment}
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            yield {"type": "error", "data": f"Error: {e}"}
