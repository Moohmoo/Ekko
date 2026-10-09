"""Abstract ports (interfaces) defining inbound and outbound domain boundaries."""

from typing import Any, Protocol, runtime_checkable
from ekko.core.models import Message, ModelResponse


@runtime_checkable
class LLMProviderPort(Protocol):
    """Port defining the contract for LLM inference adapters."""

    async def generate(
        self,
        messages: list[Message],
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate a response from the underlying LLM provider."""
        ...


@runtime_checkable
class MemoryPort(Protocol):
    """Port defining conversation session memory persistence."""

    async def add_message(self, session_id: str, message: Message) -> None:
        """Persist a message into the specified session."""
        ...

    async def get_messages(self, session_id: str) -> list[Message]:
        """Retrieve full conversation history for the specified session."""
        ...

    async def clear_session(self, session_id: str) -> None:
        """Remove all messages associated with the specified session."""
        ...

