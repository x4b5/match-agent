from fastapi import APIRouter

from backend.services.llm_instance import get_provider

router = APIRouter(prefix="/status", tags=["Status"])

@router.get("/")
async def get_ollama_status():
    """Check of de LLM-provider bereikbaar is en haal de geladen modellen op."""
    return await get_provider().check_status()

@router.get("/prompts")
async def get_prompts():
    """Haal de geconfigureerde AI prompts op voor transparantie."""
    from backend import config
    return {
        "SYSTEM_PROMPT": config.SYSTEM_PROMPT,
        "KERN_MATCH_PROMPT": config.KERN_MATCH_PROMPT,
        "VERDIEPING_MATCH_PROMPT": config.VERDIEPING_MATCH_PROMPT,
        "PROFIEL_KANDIDAAT_PROMPT": config.PROFIEL_KANDIDAAT_PROMPT,
        "PROFIEL_WERKGEVERSVRAAG_PROMPT": config.PROFIEL_WERKGEVERSVRAAG_PROMPT,
        "MATCH_MODI": config.MATCH_MODI,
        "GLOBAL_MODELS": {
            "OLLAMA_MODEL": config.OLLAMA_MODEL,
            "CLAUDE_MODEL": config.CLAUDE_MODEL,
            "PROFIEL_MODEL": config.PROFIEL_MODEL,
            "EMBEDDING_MODEL": config.EMBEDDING_MODEL
        },
        "SEED": 42
    }
