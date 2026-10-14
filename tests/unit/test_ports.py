"""Unit tests for providers and resource management protocols."""

from typing import Any
import pytest

from ekko.core.errors import EkkoError, ProviderError
from ekko.daemon.resources import ResourceManager, ResourceManagerPort
from ekko.db.embedder import EmbedderPort, TextEmbedder
from ekko.providers.base import LLMProvider, Message, ModelResponse


class DummyValidProvider:
    """Mock provider correctly implementing the LLMProvider contract."""

    async def generate(
        self,
        messages: list[Message],
        **kwargs: Any,
    ) -> ModelResponse:
        return ModelResponse(content="ok", model_name="dummy")


class DummyInvalidProvider:
    """Mock provider missing required method."""

    pass


def test_provider_protocol_runtime_checkable() -> None:
    """Ensure LLMProvider validates conforming implementations at runtime."""
    valid_instance = DummyValidProvider()
    invalid_instance = DummyInvalidProvider()

    assert isinstance(valid_instance, LLMProvider)
    assert not isinstance(invalid_instance, LLMProvider)


def test_provider_error_hierarchy() -> None:
    """Ensure ProviderError inherits from base EkkoError and captures cause."""
    cause = RuntimeError("Low level timeout")
    err = ProviderError("Provider failed to respond", cause=cause)

    assert isinstance(err, EkkoError)
    assert err.cause is cause
    assert "Provider failed to respond" in str(err)


def test_embedder_port_runtime_checkable() -> None:
    """Ensure TextEmbedder complies with EmbedderPort."""
    assert issubclass(TextEmbedder, EmbedderPort)


def test_resource_manager_port_runtime_checkable() -> None:
    """Ensure ResourceManager complies with ResourceManagerPort."""
    assert issubclass(ResourceManager, ResourceManagerPort)
