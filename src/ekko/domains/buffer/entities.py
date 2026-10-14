"""Buffer domain entities representing PKM knowledge notes."""

from datetime import datetime, timezone
from pydantic import BaseModel, Field


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
