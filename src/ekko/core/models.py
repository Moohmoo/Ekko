"""Domain models representing conversation messages and LLM responses."""

from typing import Literal
from pydantic import BaseModel, Field, field_validator


RoleType = Literal["system", "user", "assistant"]


class Message(BaseModel):
    """Immutable domain representation of a conversation turn."""

    role: RoleType
    content: str = Field(..., min_length=1)

    @field_validator("content")
    @classmethod
    def validate_content_not_blank(cls, value: str) -> str:
        # Prevent silent failures and wasted tokens by rejecting empty prompts early
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message content cannot be empty or blank")
        return stripped


class ModelResponse(BaseModel):
    """Normalized response payload returned by LLM providers."""

    content: str
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens
