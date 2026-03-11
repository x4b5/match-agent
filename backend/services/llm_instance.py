"""Singleton die de actieve LLM-provider beheert."""
from backend.services.llm_provider import LLMProvider

_providers: dict[str, LLMProvider] = {}


def get_provider(provider_type: str = "local") -> LLMProvider:
    """
    Haal een LLM-provider op.
    :param provider_type: 'local' (Ollama) of 'api' (Anthropic/Claude)
    """
    if provider_type not in _providers:
        init_provider(provider_type)
    return _providers[provider_type]


def init_provider(provider_type: str = "local"):
    """Initialiseer een LLM-provider op basis van het type."""
    global _providers
    
    if provider_type == "local":
        from backend.services.ollama_service import OllamaProvider
        _providers["local"] = OllamaProvider()
    elif provider_type == "api":
        from backend.services.anthropic_service import ClaudeProvider
        _providers["api"] = ClaudeProvider()
    else:
        raise ValueError(f"Onbekend provider type: {provider_type}")
