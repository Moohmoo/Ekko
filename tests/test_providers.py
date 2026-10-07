"""Tests unitaires pour les fournisseurs LLM et la gestion du timeout."""

import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from providers.gemini import GeminiProvider


def test_gemini_provider_requires_api_key() -> None:
    """Vérifie le rejet d'une clé API vide."""
    with pytest.raises(ValueError, match="clé GEMINI_API_KEY valide"):
        GeminiProvider(api_key="")


@pytest.mark.asyncio
async def test_gemini_provider_timeout_handling() -> None:
    """Vérifie la levée d'un TimeoutError explicite lors d'un blocage réseau."""
    provider = GeminiProvider(api_key="fake-key", timeout=0.05)

    async def slow_generate(*args: object, **kwargs: object) -> None:
        await asyncio.sleep(0.2)

    with patch.object(provider.client.aio.models, "generate_content", side_effect=slow_generate):
        with pytest.raises(TimeoutError, match="n'a pas répondu sous 0.05s"):
            await provider.generate_text("Test prompt")
