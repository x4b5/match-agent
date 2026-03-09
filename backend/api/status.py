from fastapi import APIRouter
import aiohttp
from backend.config import OLLAMA_URL

router = APIRouter(prefix="/status", tags=["Status"])

@router.get("/")
async def get_ollama_status():
    """Check of Ollama bereikbaar is en haal de geladen modellen op."""
    # Using the base url from OLLAMA_URL
    base_url = OLLAMA_URL.split("/api/")[0]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/api/tags", timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return {"online": True, "models": models}
                else:
                    return {"online": False, "models": []}
    except Exception:
        return {"online": False, "models": []}
@router.get("/prompts")
async def get_prompts():
    """Haal de geconfigureerde AI prompts op voor transparantie."""
    from backend import config
    return {
        "SYSTEM_PROMPT": config.SYSTEM_PROMPT,
        "MATCH_PROMPT": config.MATCH_PROMPT,
        "PROFIEL_KANDIDAAT_PROMPT": config.PROFIEL_KANDIDAAT_PROMPT,
        "PROFIEL_WERKGEVERSVRAAG_PROMPT": config.PROFIEL_WERKGEVERSVRAAG_PROMPT,
        "MATCH_MODI": config.MATCH_MODI
    }
