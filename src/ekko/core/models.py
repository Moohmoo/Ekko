"""Domain models representing prompt messages, distillation entities, and LLM responses."""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, model_validator

RoleType = Literal["system", "user", "assistant"]


class Message(BaseModel):
    """Immutable domain representation of a prompt message."""

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


class SignalStatus(str, Enum):
    """Lifecycle status of an ingested raw signal."""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    RETAINED = "retained"
    DISCARDED = "discarded"
    ARCHIVED = "archived"


class SourceState(BaseModel):
    """Tracking entity for source polling state, conditional headers, and backoff."""

    id: str
    source_type: str
    url_or_path: str
    etag: str | None = None
    last_modified: str | None = None
    last_polled_at: datetime | None = None
    consecutive_errors: int = 0
    backoff_until: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RawSignal(BaseModel):
    """Raw signal ingested from an external source before semantic distillation."""

    id: str
    source_id: str | None = None
    title: str
    external_id: str | None = None
    url: str | None = None
    raw_content: str | None = None
    clean_content: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: SignalStatus = SignalStatus.PENDING


class KnowledgeNote(BaseModel):
    """Structured PKM knowledge note distilled from signals or user drops."""

    id: str
    slug: str
    title: str
    summary: str
    content: str
    tags: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
