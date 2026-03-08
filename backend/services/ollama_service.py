import aiohttp
import json
import re
import asyncio
from backend.config import OLLAMA_URL, OLLAMA_EMBED_URL, EMBEDDING_MODEL, SYSTEM_PROMPT

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

def _validate_json_antwoord(antwoord: str, schema: BaseModel | None) -> dict | None:
    try:
        data = json.loads(antwoord)
        if schema:
            # Validate and format with Pydantic
            validated = schema(**data)
            return validated.model_dump()
        return data
    except (json.JSONDecodeError, ValueError) as e:
        print(f"JSON Parse Error: {e}")
        return None
    except Exception as e:
        print(f"Pydantic Validation Error: {e}")
        return None

async def vraag_ollama_json(model: str, prompt: str, schema: BaseModel | None = None, temperature: float = 0.3, num_predict: int = 2048, num_ctx: int = 8192, think: bool = False, max_retries: int = 1) -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
        },
        "think": think,
    }
    
    # Use native structured outputs if schema provided
    if schema:
        payload["format"] = schema.model_json_schema()
    else:
        payload["format"] = "json"

    for poging in range(max_retries + 1):
        try:
            resp = await _post_ollama(OLLAMA_URL, payload, timeout=600)
            antwoord = resp.get("response", "")
            resultaat = _validate_json_antwoord(antwoord, schema)
            if resultaat:
                return resultaat
        except OllamaError as e:
            if poging == max_retries:
                raise e
        # If parsing failed or error, wait and retry
        await asyncio.sleep(2)
    
    raise OllamaError("Model gaf geen geldig JSON-antwoord na meerdere pogingen.")

async def stream_ollama_json(model: str, prompt: str, temperature: float = 0.3, num_predict: int = 2048, num_ctx: int = 8192, think: bool = False):
    payload = {
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": True,
        "format": "json",
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
        },
        "think": think,
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(OLLAMA_URL, json=payload, timeout=600) as response:
                response.raise_for_status()
                async for line in response.content:
                    if line:
                        try:
                            chunk = json.loads(line)
                            
                            # Log reason if finished
                            if chunk.get("done"):
                                reason = chunk.get("done_reason")
                                if reason == "length":
                                    print(f"WARNING: Ollama stream gestopt door token limiet (length).")
                                elif reason:
                                    print(f"Ollama stream klaar. Reden: {reason}")

                            fragment = chunk.get("response", "")
                            if fragment:
                                yield {"type": "token", "data": fragment}
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            yield {"type": "error", "data": f"Error: {e}"}
