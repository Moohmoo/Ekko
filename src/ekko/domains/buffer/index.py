"""Buffer domain façade exposing knowledge notes retrieval and hybrid search."""

from typing import Any
from ekko.db.manager import DatabaseManager
from ekko.domains.buffer import crud, search
from ekko.logger import get_logger

logger = get_logger("domains.buffer")


async def scan_notes(db_manager: DatabaseManager, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Scan recent knowledge notes ordered by creation time DESC."""
    limit = int(params.get("limit", 20))
    notes = await crud.fetch_recent_notes(db_manager, limit=limit)
    return [n.model_dump(mode="json") for n in notes]


async def search_notes(
    db_manager: DatabaseManager,
    params: dict[str, Any],
    embedder: Any | None = None,
) -> list[dict[str, Any]]:
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
        db_manager=db_manager,
        query=query,
        query_embedding=query_embedding,
        mode=mode,
        limit=limit,
    )

    return [
        {
            "note": note.model_dump(mode="json"),
            "score": round(score, 4),
        }
        for note, score in results
    ]
