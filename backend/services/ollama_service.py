import aiohttp
import json
import re
import asyncio
import logging
import typing
from collections.abc import AsyncGenerator
from pydantic import BaseModel, ValidationError

import instructor
from openai import AsyncOpenAI

from backend.config import OLLAMA_URL, OLLAMA_EMBED_URL, OLLAMA_BASE_URL, EMBEDDING_MODEL, SYSTEM_PROMPT
from backend.services.llm_provider import LLMProvider, T

logger = logging.getLogger("matchflix.ollama")


class OllamaError(Exception):
    pass


# ── Helper functies (module-level) ──

def _extract_json_from_thinking(antwoord: str) -> str:
    """Haal het JSON-blok uit een thinking-mode antwoord dat denktekst kan bevatten."""
    stripped = antwoord.strip()
    if stripped.startswith("{"):
        return stripped
    matches = list(re.finditer(r'\{[\s\S]*\}', stripped))
    if matches:
        return matches[-1].group()
    return stripped


def _validate_json_antwoord(antwoord: str, schema: type[BaseModel] | None) -> dict | None:
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


# ── OllamaProvider ──

class OllamaProvider(LLMProvider):
    """LLM-provider die communiceert met een lokale Ollama-instantie."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL, generate_url: str = OLLAMA_URL,
                 embed_url: str = OLLAMA_EMBED_URL, embedding_model: str = EMBEDDING_MODEL,
                 system_prompt: str = SYSTEM_PROMPT):
        self.base_url = base_url
        self.generate_url = generate_url
        self.embed_url = embed_url
        self.embedding_model = embedding_model
        self.system_prompt = system_prompt
        
        # Initialize Instructor patched OpenAI Client
        openai_base_url = f"{self.base_url}/v1"
        self._async_client = AsyncOpenAI(
            base_url=openai_base_url,
            api_key="ollama", # required but unused by ollama
            timeout=600.0,  # 10 minuten timeout
        )
        self.client = instructor.from_openai(self._async_client, mode=instructor.Mode.JSON)

    async def _post(self, url: str, payload: dict, timeout: int = 600) -> dict:
        client_timeout = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=client_timeout) as session:
            try:
                async with session.post(url, json=payload) as response:
                    response.raise_for_status()
                    return await response.json()
            except asyncio.TimeoutError:
                raise OllamaError("Timeout bij Ollama request.")
            except aiohttp.ClientError as e:
                raise OllamaError(f"HTTP of netwerkfout bij verbinding met Ollama: {str(e)}")

    async def generate_json(
        self,
        model: str,
        prompt: str,
        schema: type[T] | None = None,
        temperature: float = 0.1,
        num_predict: int = 2048,
        num_ctx: int = 8192,
        think: bool = False,
        max_retries: int = 2,
    ) -> T | dict:
        import time
        t0 = time.time()
        logger.info(f"Ollama generate_json aangeroepen (model={model}, schema={schema.__name__ if schema else 'None'}, think={think})")
        
        # We use the native Ollama route by default as it supports 'format' 
        # (json schema) which is more stable for local models than the 
        # OpenAI-compatible /v1 route.
        payload = {
            "model": model,
            "prompt": prompt,
            "system": self.system_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
                "num_ctx": num_ctx,
                "seed": 42,
            },
            "think": think,
        }

        if schema:
            payload["format"] = schema.model_json_schema()
        else:
            payload["format"] = "json"

        laatste_antwoord = ""
        for poging in range(max_retries + 1):
            try:
                resp = await self._post(self.generate_url, payload, timeout=600)

                if resp.get("done_reason") == "length":
                    logger.warning(f"Ollama gestopt door token limiet (poging {poging + 1}, model={model})")

                antwoord = resp.get("response", "")
                laatste_antwoord = antwoord

                if think:
                    antwoord = _extract_json_from_thinking(antwoord)

                resultaat = _validate_json_antwoord(antwoord, schema) if schema else json.loads(antwoord)
                if resultaat is not None:
                    logger.info(f"Ollama native generate succesvol in {time.time()-t0:.2f}s")
                    return schema(**resultaat) if schema and isinstance(resultaat, dict) else resultaat

                _bewaar_debug_output(antwoord, poging, model)

            except OllamaError as e:
                logger.error(f"Ollama fout poging {poging + 1}: {e}")
                if poging == max_retries:
                    raise e
            except json.JSONDecodeError:
                _bewaar_debug_output(antwoord, poging, model)

            if poging < max_retries:
                await asyncio.sleep(2 * (poging + 1))

        # Graceful fallback
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


    async def generate_json_stream(
        self,
        model: str,
        prompt: str,
        schema: type[T] | None = None,
        temperature: float = 0.1,
        num_predict: int = 2048,
        num_ctx: int = 8192,
        think: bool = False,
    ) -> AsyncGenerator[dict, None]:
        use_structured = schema and not think

        # We prefer the native Ollama endpoint for streaming because it supports 
        # FULL JSON SCHEMA validation at the token level via the 'format' parameter.
        payload = {
            "model": model,
            "prompt": prompt,
            "system": self.system_prompt,
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
                async with session.post(self.generate_url, json=payload, timeout=600) as response:
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
                logger.error(f"Ollama stream error: {e}")
                yield {"type": "error", "data": f"Error: {e}"}

    async def generate_embedding(self, text: str) -> list[float]:
        payload = {
            "model": self.embedding_model,
            "prompt": text,
        }
        result = await self._post(self.embed_url, payload, timeout=120)
        return result.get("embedding", [])

    async def check_status(self) -> dict:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [m["name"] for m in data.get("models", [])]
                        return {"online": True, "models": models}
                    else:
                        return {"online": False, "models": []}
        except Exception:
            return {"online": False, "models": []}
