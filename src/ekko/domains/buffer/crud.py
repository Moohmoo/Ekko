"""Buffer domain CRUD operations for knowledge notes."""

from ekko.domains.buffer.entities import KnowledgeNote
from ekko.db.manager import DatabaseManager


async def fetch_recent_notes(db_manager: DatabaseManager, limit: int = 20) -> list[KnowledgeNote]:
    """Retrieve most recent knowledge notes."""
    if hasattr(db_manager, "list_knowledge_notes"):
        return await db_manager.list_knowledge_notes(limit=limit)
    return await db_manager.get_recent_notes(limit=limit)


async def fetch_note_by_slug(db_manager: DatabaseManager, slug: str) -> KnowledgeNote | None:
    """Retrieve single knowledge note by unique slug."""
    return await db_manager.get_note_by_slug(slug)
