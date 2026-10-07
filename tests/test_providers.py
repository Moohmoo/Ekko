"""Tests unitaires pour les fournisseurs LLM et la gestion du timeout/retry."""

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
    """Vérifie la levée d'un TimeoutError après épuisement des tentatives."""
    provider = GeminiProvider(api_key="fake-key", timeout=0.05)

    async def slow_generate(*args: object, **kwargs: object) -> None:
        await asyncio.sleep(0.2)

    with patch.object(provider.client.aio.models, "generate_content", side_effect=slow_generate):
        with pytest.raises(TimeoutError, match="n'a pas répondu après 2 essais"):
            await provider.generate_text("Test prompt")


@pytest.mark.asyncio
async def test_gemini_provider_retry_success() -> None:
    """Vérifie que la deuxième tentative réussit si la première échoue."""
    provider = GeminiProvider(api_key="fake-key", timeout=0.1)

    calls = 0

    async def flaky_generate(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConnectionError("Intermittent error")
        mock_resp = AsyncMock()
        mock_resp.text = "Succès au 2e essai"
        return mock_resp

    with patch.object(provider.client.aio.models, "generate_content", side_effect=flaky_generate):
        res = await provider.generate_text("Test prompt")
        assert res == "Succès au 2e essai"
        assert calls == 2
