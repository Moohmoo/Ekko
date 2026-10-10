"""Domain models for unified local-first SQLite persistence."""

from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any
from pydantic import BaseModel, Field


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
    source_id: str
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
