"""Buffer domain façade exposing knowledge notes retrieval and hybrid search."""

from typing import Any
from ekko.core.logger import get_logger
from ekko.domains.buffer import search
from ekko.domains.buffer.contracts import NoteRepositoryPort, NoteSearchResult, SearchEnginePort
from ekko.domains.buffer.entities import KnowledgeNote

logger = get_logger("domains.buffer")


async def scan_notes(repo: NoteRepositoryPort, params: dict[str, Any]) -> list[KnowledgeNote]:
    """Scan recent knowledge notes ordered by creation time DESC."""
    limit = int(params.get("limit", 20))
    if hasattr(repo, "list_knowledge_notes"):
        return await repo.list_knowledge_notes(limit=limit)
    return await repo.get_recent_notes(limit=limit)


async def search_notes(
    search_engine: SearchEnginePort,
    params: dict[str, Any],
    embedder: Any | None = None,
) -> list[NoteSearchResult]:
    """Search knowledge notes with hybrid lexical/semantic ranking."""
    query = str(params.get("query", ""))
    limit = int(params.get("limit", 10))
    mode = str(params.get("mode", "hybrid"))

    query_embedding = None
    if mode in ("hybrid", "semantic") and embedder and query.strip():
        try:
            if hasattr(embedder, "async_embed_query"):
                query_embedding = await embedder.async_embed_query(query)
            elif hasattr(embedder, "embed_query"):
                query_embedding = embedder.embed_query(query)
        except Exception as e:
            logger.warning("Embedding generation failed for query %s: %s", query, e)

    results = await search.execute_hybrid_search(
        search_engine=search_engine,
        query=query,
        query_embedding=query_embedding,
        mode=mode,
        limit=limit,
    )

    return [
        NoteSearchResult(note=note, score=round(score, 4))
        for note, score in results
    ]
