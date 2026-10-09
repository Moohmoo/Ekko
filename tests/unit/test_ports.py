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


def test_tool_port_runtime_checkable() -> None:
    """Ensure ToolPort protocol verifies compliant tool implementations."""
    from ekko.core.models import ToolResult
    from ekko.core.ports import ToolPort

    class ValidTool:
        name: str = "test_tool"
        description: str = "Does testing"

        def get_schema(self) -> dict[str, Any]:
            return {"type": "function"}

        async def execute(self, **kwargs: Any) -> ToolResult:
            return ToolResult(content="done", success=True)

    class InvalidTool:
        pass

    assert isinstance(ValidTool(), ToolPort)
    assert not isinstance(InvalidTool(), ToolPort)

