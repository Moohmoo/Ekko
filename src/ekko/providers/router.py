"""LLM Router and Factory selecting the configured inference provider."""

from ekko.core.errors import ProviderError
from ekko.core.ports import LLMProviderPort
from ekko.providers.litellm_provider import LiteLLMProvider
from ekko.settings import Settings


def _normalize_model_name(model: str, default_prefix: str) -> str:
    """Ensure LiteLLM has provider namespace prefix to route correctly."""
    if "/" in model:
        return model
    return f"{default_prefix}/{model}"


def _build_gemini_provider(settings: Settings) -> LiteLLMProvider:
    """Build and validate LiteLLM provider for Gemini API."""
    if not settings.gemini_api_key:
        raise ProviderError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")

    model = _normalize_model_name(settings.gemini_model, "gemini")
    return LiteLLMProvider(
        model=model,
        api_key=settings.gemini_api_key,
        temperature=settings.llm_temperature,
    )


def _normalize_local_url(url: str) -> str:
    """Trim /v1 suffix from local URL to support native Ollama endpoints."""
    cleaned = url.rstrip("/")
    if cleaned.endswith("/v1"):
        return cleaned[:-3]
    return cleaned


def _normalize_local_model_name(model: str) -> str:
    """Ensure local Ollama models use LiteLLM native ollama_chat prefix for tools."""
    if model.startswith("ollama/"):
        return f"ollama_chat/{model[7:]}"
    if "/" in model:
        return model
    return f"ollama_chat/{model}"


def _build_local_provider(settings: Settings) -> LiteLLMProvider:
    """Build LiteLLM provider pointing to a local inference server (e.g. Ollama)."""
    model = _normalize_local_model_name(settings.local_llm_model)
    api_base = _normalize_local_url(settings.local_llm_url)
    return LiteLLMProvider(
        model=model,
        api_base=api_base,
        temperature=settings.llm_temperature,
    )




class LLMRouter:
    """Factory resolving the active LLMProviderPort based on settings."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def get_provider(self) -> LLMProviderPort:
        """Resolve and instantiate the configured LLM provider."""
        provider_name = self.settings.llm_provider.strip().lower()

        if provider_name == "gemini":
            return _build_gemini_provider(self.settings)
        if provider_name == "local":
            return _build_local_provider(self.settings)

        raise ProviderError(f"Unsupported LLM provider: {self.settings.llm_provider}")
