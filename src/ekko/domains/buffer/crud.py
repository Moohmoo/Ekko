"""Buffer domain CRUD operations for knowledge notes."""

from ekko.domains.buffer.contracts import NoteRepositoryPort
from ekko.domains.buffer.entities import KnowledgeNote


async def fetch_recent_notes(repo: NoteRepositoryPort, limit: int = 20) -> list[KnowledgeNote]:
    """Retrieve most recent knowledge notes."""
    if hasattr(repo, "list_knowledge_notes"):
        return await repo.list_knowledge_notes(limit=limit)
    return await repo.get_recent_notes(limit=limit)


async def fetch_note_by_slug(repo: NoteRepositoryPort, slug: str) -> KnowledgeNote | None:
    """Retrieve single knowledge note by unique slug."""
    if hasattr(repo, "get_knowledge_note_by_slug"):
        return await repo.get_knowledge_note_by_slug(slug)
    return await repo.get_note_by_slug(slug)
