"""Buffer domain hybrid search operations (FTS5 + sqlite-vec with RRF)."""

from typing import Any
from ekko.db.manager import DatabaseManager
from ekko.domains.buffer.entities import KnowledgeNote


async def execute_hybrid_search(
    db_manager: DatabaseManager,
    query: str,
    query_embedding: list[float] | None = None,
    mode: str = "hybrid",
    limit: int = 5,
) -> list[tuple[KnowledgeNote, float]]:
    """Execute hybrid search combining BM25 lexical and dense vector similarity."""
    return await db_manager.search_notes(
        query=query,
        query_embedding=query_embedding,
        mode=mode,
        limit=limit,
    )
