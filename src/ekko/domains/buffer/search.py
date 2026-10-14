"""Buffer domain hybrid search engine combining FTS5 BM25 lexical and sqlite-vec vector retrieval via RRF."""

import asyncio
import re
import sqlite3

import sqlite_vec

from ekko.core.logger import get_logger
from ekko.db.connection import DatabaseConnection
from ekko.domains.buffer.contracts import SearchEnginePort
from ekko.domains.buffer.entities import KnowledgeNote
from ekko.domains.buffer.repository import _row_to_knowledge_note

logger = get_logger("domains.buffer.search")

_RESERVED_FTS_WORDS = frozenset({"AND", "OR", "NOT", "NEAR"})


def _sanitize_fts_query(query: str) -> str:
    """Format query string into safe quoted terms connected with OR for FTS5."""
    clean_query = query.strip()
    if not clean_query:
        return ""

    # Replace punctuation with spaces to prevent fusing domains (e.g. sqlite.org -> sqlite org)
    normalized = re.sub(r"[^\w-]", " ", clean_query)
    tokens = normalized.split()
    valid_terms: list[str] = []
    for token in tokens:
        stripped = token.strip("-")
        if stripped and stripped.upper() not in _RESERVED_FTS_WORDS:
            valid_terms.append(f'"{stripped}"')

    return " OR ".join(valid_terms)


class SqliteHybridSearchEngine:
    """SQLite implementation of SearchEnginePort combining FTS5 BM25 and sqlite-vec via RRF."""

    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def _run_fts_search(self, conn: sqlite3.Connection, query: str, limit: int) -> dict[str, int]:
        """Execute FTS5 search and return mapping of note_id to 1-based rank."""
        sanitized = _sanitize_fts_query(query)
        if not sanitized:
            return {}
        sql = "SELECT note_id FROM knowledge_fts WHERE knowledge_fts MATCH ? ORDER BY rank LIMIT ?;"
        rows = conn.execute(sql, (sanitized, limit)).fetchall()
        return {str(row["note_id"]): idx + 1 for idx, row in enumerate(rows)}

    def _run_vec_search(
        self,
        conn: sqlite3.Connection,
        embedding: list[float],
        limit: int,
    ) -> dict[str, int]:
        """Execute sqlite-vec vector search on chunks and return mapping of note_id to 1-based rank."""
        candidate_pool = max(limit * 5, 50)
        serialized = sqlite_vec.serialize_float32(embedding)
        sql = """
        SELECT c.note_id, min(v.distance) AS best_distance
        FROM (
            SELECT chunk_rowid, distance
            FROM knowledge_vectors
            WHERE embedding MATCH ?
            ORDER BY distance
            LIMIT ?
        ) v
        JOIN note_chunks c ON c.id = v.chunk_rowid
        GROUP BY c.note_id
        ORDER BY best_distance ASC
        LIMIT ?;
        """
        rows = conn.execute(sql, (serialized, candidate_pool, limit)).fetchall()
        return {str(row["note_id"]): idx + 1 for idx, row in enumerate(rows)}

    def search_notes_sync(
        self,
        query: str,
        query_embedding: list[float] | None,
        mode: str,
        limit: int,
        k: int,
    ) -> list[tuple[KnowledgeNote, float]]:
        """Execute hybrid, lexical, or semantic note retrieval using RRF fusion synchronously."""
        candidate_pool_size = max(limit * 5, 50)
        with self.connection.connection() as conn:
            fts_ranks = self._run_fts_search(conn, query, candidate_pool_size) if mode in {"lexical", "hybrid"} else {}
            vec_ranks = (
                self._run_vec_search(conn, query_embedding, candidate_pool_size)
                if mode in {"semantic", "hybrid"} and query_embedding is not None
                else {}
            )

            scores: dict[str, float] = {}
            candidate_ids = set(fts_ranks.keys()) | set(vec_ranks.keys())
            for nid in candidate_ids:
                rrf = 0.0
                if nid in fts_ranks:
                    rrf += 1.0 / (k + fts_ranks[nid])
                if nid in vec_ranks:
                    rrf += 1.0 / (k + vec_ranks[nid])
                scores[nid] = rrf

            sorted_candidates = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
            if not sorted_candidates:
                return []

            note_map: dict[str, KnowledgeNote] = {}
            placeholders = ",".join("?" for _ in sorted_candidates)
            rows = conn.execute(
                f"SELECT * FROM knowledge_notes WHERE id IN ({placeholders});",
                tuple(nid for nid, _ in sorted_candidates),
            ).fetchall()
            for r in rows:
                note_map[str(r["id"])] = _row_to_knowledge_note(r)

            return [(note_map[nid], score) for nid, score in sorted_candidates if nid in note_map]

    async def search_notes(
        self,
        query: str,
        query_embedding: list[float] | None = None,
        mode: str = "hybrid",
        limit: int = 5,
        k: int = 60,
    ) -> list[tuple[KnowledgeNote, float]]:
        """Search knowledge notes using RRF fusion, lexical FTS5, or semantic vectors asynchronously."""
        return await asyncio.to_thread(self.search_notes_sync, query, query_embedding, mode, limit, k)


async def execute_hybrid_search(
    search_engine: SearchEnginePort,
    query: str,
    query_embedding: list[float] | None = None,
    mode: str = "hybrid",
    limit: int = 5,
) -> list[tuple[KnowledgeNote, float]]:
    """Execute hybrid search combining BM25 lexical and dense vector similarity."""
    return await search_engine.search_notes(
        query=query,
        query_embedding=query_embedding,
        mode=mode,
        limit=limit,
    )
