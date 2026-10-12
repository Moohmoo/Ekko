"""Unit tests for core domain ports and exceptions."""

from typing import Any
import pytest

from ekko.core.errors import EkkoError, ProviderError
from ekko.core.models import Message, ModelResponse
from ekko.core.ports import LLMProviderPort, StreamingLLMProviderPort


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


def test_streaming_provider_port_runtime_checkable() -> None:
    """Ensure StreamingLLMProviderPort validates conforming implementations at runtime."""
    from collections.abc import AsyncIterator

    class DummyStreamingProvider(DummyValidProvider):
        async def generate_stream(self, messages: list[Message], **kwargs: Any) -> AsyncIterator[Any]:
            yield "chunk"

    streaming_instance = DummyStreamingProvider()
    non_streaming_instance = DummyValidProvider()

    assert isinstance(streaming_instance, StreamingLLMProviderPort)
    assert isinstance(streaming_instance, LLMProviderPort)
    assert not isinstance(non_streaming_instance, StreamingLLMProviderPort)



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


def test_hybrid_memory_port_runtime_checkable() -> None:
    """Ensure HybridStore complies with HybridMemoryPort."""
    from ekko.core.ports import HybridMemoryPort
    from ekko.memory.hybrid_store import HybridStore

    assert issubclass(HybridStore, HybridMemoryPort)


def test_sqlite_memory_port_runtime_checkable() -> None:
    """Ensure SqliteMemory complies with MemoryPort."""
    from ekko.core.ports import MemoryPort
    from ekko.memory.sqlite_memory import SqliteMemory

    assert issubclass(SqliteMemory, MemoryPort)


def test_embedder_port_runtime_checkable() -> None:
    """Ensure TextEmbedder complies with EmbedderPort."""
    from ekko.core.ports import EmbedderPort
    from ekko.memory.embedder import TextEmbedder

    assert issubclass(TextEmbedder, EmbedderPort)

