"""Singleton die de actieve LLM-provider beheert."""
from backend.services.llm_provider import LLMProvider

_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """Haal de actieve LLM-provider op. Moet eerst geïnitialiseerd zijn via init_provider()."""
    if _provider is None:
        raise RuntimeError("LLM provider is niet geïnitialiseerd. Roep init_provider() aan bij opstarten.")
    return _provider


def init_provider():
    """Initialiseer de LLM-provider op basis van de configuratie."""
    global _provider
    from backend.services.ollama_service import OllamaProvider
    _provider = OllamaProvider()
