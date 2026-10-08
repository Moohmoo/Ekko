"""Fabrique et point d'accès pour les fournisseurs LLM."""

from config import Settings
from .base import LLMProvider
from .gemini import GeminiProvider
from .local import LocalProvider


def create_llm_provider(settings: Settings) -> LLMProvider:
    """Instancie le provider LLM configuré (Gemini officiel ou local)."""
    provider = settings.llm_provider.strip().lower()
    if provider == "local":
        return LocalProvider(
            base_url=settings.local_llm_url,
            model_name=settings.local_llm_model,
        )
    if provider == "gemini":
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model_name=settings.gemini_model,
        )
    raise ValueError(
        f"Fournisseur LLM non supporté : '{settings.llm_provider}'. "
        "Valeurs autorisées : 'local', 'gemini'."
    )


__all__ = ["LLMProvider", "GeminiProvider", "LocalProvider", "create_llm_provider"]
