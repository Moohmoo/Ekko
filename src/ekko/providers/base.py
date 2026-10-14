"""Universal LLM inference primitives and provider protocol."""

from typing import Any, Literal, Protocol, runtime_checkable
from pydantic import BaseModel, model_validator

RoleType = Literal["system", "user", "assistant"]


class Message(BaseModel):
    """Immutable prompt message transmitted to an LLM provider."""

    role: RoleType
    content: str

    @model_validator(mode="after")
    def validate_message_consistency(self) -> "Message":
        """Ensure message content is not empty or blank."""
        raw_content = (self.content or "").strip()
        if not raw_content:
            raise ValueError("Message content cannot be empty or blank")
        self.content = raw_content
        return self


class ModelResponse(BaseModel):
    """Normalized response payload returned by LLM providers."""

    content: str = ""
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol defining the contract for LLM inference providers."""

    async def generate(
        self,
        messages: list[Message],
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate an inference response from the underlying provider."""
        ...
