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
