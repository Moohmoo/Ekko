"""Abstract ports (interfaces) defining inbound and outbound domain boundaries."""

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable
from ekko.core.models import Message, ModelResponse, ToolResult


@runtime_checkable
class LLMProviderPort(Protocol):
    """Port defining the contract for LLM inference adapters."""

    async def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate a response from the underlying LLM provider."""
        ...


@runtime_checkable
class StreamingLLMProviderPort(LLMProviderPort, Protocol):
    """Optional port extending LLMProviderPort with real-time streaming capabilities."""

    async def generate_stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        """Stream response chunks from the underlying LLM provider."""
        ...



@runtime_checkable
class MemoryPort(Protocol):
    """Port defining conversation session memory persistence."""

    async def add_message(self, session_id: str, message: Message) -> None:
        """Persist a message into the specified session."""
        ...

    async def get_messages(self, session_id: str, limit: int = 50) -> list[Message]:
        """Retrieve conversation history for the session, up to limit turns."""
        ...

    async def clear_session(self, session_id: str) -> None:
        """Remove all messages associated with the specified session."""
        ...


@runtime_checkable
class ToolPort(Protocol):
    """Port defining the contract for modular tools and capabilities."""

    name: str
    description: str

    def get_schema(self) -> dict[str, Any]:
        """Return the tool JSON schema definition for LLM tool calling."""
        ...

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool logic using provided parameters."""
        ...
