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
