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
        with pytest.raises(TimeoutError, match="délai imparti"):
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


def test_clean_json_payload_unwraps_properties_and_defaults() -> None:
    """Vérifie que clean_json_payload élimine les fragments de schéma JSON émis par les SLMs."""
    import json
    from providers.local import clean_json_payload

    # Cas 1 : Enveloppe globale 'properties'
    raw1 = '{"properties": {"intent": "chat"}}'
    cleaned1 = clean_json_payload(raw1)
    assert json.loads(cleaned1) == {"intent": "chat"}

    # Cas 2 : Propriété avec définition de schéma {'default': ..., 'type': ...}
    raw2 = '{"is_search_needed": {"default": true, "type": "boolean"}, "focus": "web"}'
    cleaned2 = clean_json_payload(raw2)
    assert json.loads(cleaned2) == {"is_search_needed": True, "focus": "web"}

    # Cas 3 : Markdown avec bloc json
    raw3 = '```json\n{"properties": {"thought": "ok", "intent": "action"}}\n```'
    cleaned3 = clean_json_payload(raw3)
    assert json.loads(cleaned3) == {"thought": "ok", "intent": "action"}

    # Cas 4 : Propriété avec anyOf et default: null
    raw4 = '{"focus": "news", "direct_answer": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null, "title": "Direct Answer"}}'
    cleaned4 = clean_json_payload(raw4)
    assert json.loads(cleaned4) == {"focus": "news", "direct_answer": None}


def test_clean_json_text_strips_markdown_fences() -> None:
    """Vérifie que _clean_json_text nettoie les balises markdown pour Gemini."""
    from providers.gemini import _clean_json_text

    assert _clean_json_text('```json\n{"intent": "chat"}\n```') == '{"intent": "chat"}'
    assert _clean_json_text('```\n{"intent": "chat"}\n```') == '{"intent": "chat"}'
    assert _clean_json_text('{"intent": "chat"}') == '{"intent": "chat"}'
    assert _clean_json_text(None) == "{}"


def test_translate_local_error_types() -> None:
    """Vérifie la conversion typée des erreurs réseau du fournisseur local."""
    import httpx
    from providers.errors import ProviderError, ProviderTimeoutError, ProviderUnavailableError
    from providers.local import _translate_local_error

    conn_err = httpx.ConnectError("Connection refused")
    typed_unavail = _translate_local_error(conn_err, "http://localhost:11434")
    assert isinstance(typed_unavail, ProviderUnavailableError)

    timeout_err = httpx.ReadTimeout("Read timed out")
    typed_timeout = _translate_local_error(timeout_err, "http://localhost:11434")
    assert isinstance(typed_timeout, ProviderTimeoutError)

    status_err = httpx.HTTPStatusError("500 Server Error", request=None, response=httpx.Response(500))  # type: ignore[arg-type]
    typed_status = _translate_local_error(status_err, "http://localhost:11434")
    assert isinstance(typed_status, ProviderError)



