"""Unit tests for settings and the LLM router / factory."""

import pytest

from ekko.core.errors import ProviderError
from ekko.providers.litellm_provider import LiteLLMProvider
from ekko.providers.router import LLMRouter
from ekko.settings import Settings


def test_settings_default_values() -> None:
    """Ensure Settings sets safe defaults adhering to 12-factor principles."""
    settings = Settings(_env_file=None)
    assert settings.llm_provider in ("gemini", "local")
    assert settings.llm_temperature >= 0.0


def test_router_creates_gemini_provider() -> None:
    """Ensure router resolves and configures Gemini LiteLLM provider."""
    settings = Settings(
        llm_provider="gemini",
        gemini_api_key="fake-gemini-key",
        gemini_model="gemini-2.5-flash",
        llm_temperature=0.3,
        _env_file=None,
    )
    router = LLMRouter(settings=settings)
    provider = router.get_provider()

    assert isinstance(provider, LiteLLMProvider)
    assert provider.model == "gemini/gemini-2.5-flash"
    assert provider.api_key == "fake-gemini-key"
    assert provider.temperature == 0.3
    assert provider.api_base is None


def test_router_requires_gemini_api_key() -> None:
    """Ensure router fails fast when Gemini is selected without an API key."""
    settings = Settings(
        llm_provider="gemini",
        gemini_api_key=None,
        _env_file=None,
    )
    router = LLMRouter(settings=settings)

    with pytest.raises(ProviderError) as exc_info:
        router.get_provider()

    assert "GEMINI_API_KEY is required" in str(exc_info.value)


def test_router_creates_local_provider() -> None:
    """Ensure router configures local provider (e.g. Ollama) with custom api_base."""
    settings = Settings(
        llm_provider="local",
        local_llm_url="http://127.0.0.1:11434",
        local_llm_model="llama3.1",
        llm_temperature=0.5,
        _env_file=None,
    )
    router = LLMRouter(settings=settings)
    provider = router.get_provider()

    assert isinstance(provider, LiteLLMProvider)
    assert provider.model == "ollama_chat/llama3.1"
    assert provider.api_base == "http://127.0.0.1:11434"
    assert provider.api_key is None
    assert provider.temperature == 0.5



def test_router_strips_v1_from_local_ollama_url() -> None:
    """Ensure router cleans /v1 suffix for local Ollama compatibility."""
    settings = Settings(
        llm_provider="local",
        local_llm_url="http://localhost:11434/v1",
        local_llm_model="qwen2.5:7b",
        _env_file=None,
    )
    router = LLMRouter(settings=settings)
    provider = router.get_provider()

    assert isinstance(provider, LiteLLMProvider)
    assert provider.api_base == "http://localhost:11434"



def test_router_rejects_unsupported_provider() -> None:
    """Ensure router raises ProviderError when unknown provider is specified."""
    settings = Settings(
        llm_provider="unknown_vendor",
        _env_file=None,
    )
    router = LLMRouter(settings=settings)

    with pytest.raises(ProviderError) as exc_info:
        router.get_provider()

    assert "Unsupported LLM provider" in str(exc_info.value)
