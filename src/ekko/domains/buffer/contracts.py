"""Buffer domain IPC contracts defining retrieval, search payloads, and repository ports."""

from typing import Protocol, runtime_checkable
from pydantic import BaseModel
from ekko.domains.buffer.entities import KnowledgeNote


@runtime_checkable
class NoteRepositoryPort(Protocol):
    """Port defining knowledge note persistence operations."""

    async def save_knowledge_note(
        self,
        note: KnowledgeNote,
        embedding: list[float] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> None: ...

    async def delete_knowledge_note(self, note_id: str) -> bool: ...
    async def get_knowledge_note_by_slug(self, slug: str) -> KnowledgeNote | None: ...
    async def list_knowledge_notes(self, limit: int = 50) -> list[KnowledgeNote]: ...
    async def get_recent_notes(self, limit: int = 5) -> list[KnowledgeNote]: ...
    async def get_popular_tags(self, limit: int = 30) -> list[str]: ...
    async def get_note_chunks(self, note_id: str) -> list[str]: ...
    async def has_content_hash(self, content_hash: str) -> bool: ...
    async def has_source_url(self, url: str) -> bool: ...


@runtime_checkable
class SearchEnginePort(Protocol):
    """Port defining note search operations."""

    async def search_notes(
        self,
        query: str,
        query_embedding: list[float] | None = None,
        mode: str = "hybrid",
        limit: int = 5,
        k: int = 60,
    ) -> list[tuple[KnowledgeNote, float]]: ...


class NoteSearchResult(BaseModel):
    """Scored knowledge note returned by hybrid lexical/semantic search."""

    note: KnowledgeNote
    score: float
