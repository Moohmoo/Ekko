"""Unit tests for core domain ports and exceptions."""

from typing import Any
import pytest

from ekko.core.errors import EkkoError, ProviderError
from ekko.core.models import Message, ModelResponse
from ekko.core.ports import LLMProviderPort


class DummyValidProvider:
    """Mock provider correctly implementing the LLMProviderPort contract."""

    async def generate(
        self,
        messages: list[Message],
        **kwargs: Any,
    ) -> ModelResponse:
        return ModelResponse(content="ok", model_name="dummy")


class DummyInvalidProvider:
    """Mock provider missing required method."""

    pass


def test_provider_port_runtime_checkable() -> None:
    """Ensure LLMProviderPort validates conforming implementations at runtime."""
    valid_instance = DummyValidProvider()
    invalid_instance = DummyInvalidProvider()

    assert isinstance(valid_instance, LLMProviderPort)
    assert not isinstance(invalid_instance, LLMProviderPort)


def test_provider_error_hierarchy() -> None:
    """Ensure ProviderError inherits from base EkkoError and captures cause."""
    cause = RuntimeError("Low level timeout")
    err = ProviderError("Provider failed to respond", cause=cause)

    assert isinstance(err, EkkoError)
    assert err.cause is cause
    assert "Provider failed to respond" in str(err)
