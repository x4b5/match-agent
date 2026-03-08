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

def _parse_json_antwoord(antwoord: str) -> dict | None:
    try:
        return json.loads(antwoord)
    except (json.JSONDecodeError, ValueError):
        pass
    json_match = re.search(r"\{.*\}", antwoord, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return None

async def vraag_ollama_json(model: str, prompt: str, temperature: float = 0.3, num_predict: int = 2048, num_ctx: int = 8192, think: bool = False, max_retries: int = 1) -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
        },
        "think": think,
    }

    for poging in range(max_retries + 1):
        try:
            resp = await _post_ollama(OLLAMA_URL, payload, timeout=600)
            antwoord = resp.get("response", "")
            resultaat = _parse_json_antwoord(antwoord)
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
                            fragment = chunk.get("response", "")
                            if fragment:
                                yield {"type": "token", "data": fragment}
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            yield {"type": "error", "data": f"Error: {e}"}
