"""Thread-safe SQLite database manager for Ekko unified persistence and hybrid search."""

import asyncio
from collections import Counter
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path
import re
import sqlite3

import sqlite_vec

from ekko.core.models import (
    KnowledgeNote,
    RawSignal,
    SignalStatus,
    SourceState,
)
from ekko.core.ports import EmbedderPort
from ekko.memory.chunking import chunk_markdown
from ekko.memory.embedder import EMBEDDING_DIM
from ekko.memory.schema import INIT_UNIFIED_SCHEMA_SQL
from ekko.logger import get_logger

logger = get_logger("memory.hybrid_store")

_RESERVED_FTS_WORDS = frozenset({"AND", "OR", "NOT", "NEAR"})


def _to_iso(dt: datetime | None) -> str | None:
    """Format datetime to ISO string safely."""
    return dt.isoformat() if dt else None


def _from_iso(val: str | None) -> datetime | None:
    """Parse ISO string back to datetime safely."""
    return datetime.fromisoformat(val) if val else None


def _sanitize_fts_query(query: str) -> str:
    """Format query string into safe quoted terms connected with OR for FTS5."""
    clean_query = query.strip()
    if not clean_query:
        return ""

    # Replace punctuation (e.g. '.', '/', ':') with spaces to prevent fusing domains (e.g. sqlite.org -> sqlite org)
    normalized = re.sub(r"[^\w-]", " ", clean_query)
    tokens = normalized.split()
    valid_terms: list[str] = []
    for token in tokens:
        stripped = token.strip("-")
        if stripped and stripped.upper() not in _RESERVED_FTS_WORDS:
            valid_terms.append(f'"{stripped}"')

    return " OR ".join(valid_terms)



def _row_to_knowledge_note(row: sqlite3.Row) -> KnowledgeNote:
    """Map database Row object to KnowledgeNote model."""
    return KnowledgeNote(
        id=row["id"],
        slug=row["slug"],
        title=row["title"],
        summary=row["summary"],
        content=row["content"],
        tags=json.loads(row["tags"]),
        sources=json.loads(row["sources"]),
        created_at=_from_iso(row["created_at"]) or datetime.now(),
        updated_at=_from_iso(row["updated_at"]) or datetime.now(),
    )


class HybridStore:
    """Manages asynchronous access to unified SQLite tables and hybrid vector search."""

    def __init__(
        self,
        db_path: str | Path = "data/ekko.db",
        auto_init: bool = True,
        embedder: EmbedderPort | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder
        if auto_init:
            self.init_schema()

    def _create_connection(self) -> sqlite3.Connection:
        """Create connection with sqlite-vec extension, WAL mode, timeout, and foreign keys enabled."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 10000;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager guaranteeing connection closure and transaction commit/rollback."""
        conn = self._create_connection()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Create standalone connection for backwards compatibility (prefer _connection context manager)."""
        return self._create_connection()

    def _backfill_chunks_if_needed(self, conn: sqlite3.Connection) -> None:
        """Idempotently backfill existing notes into note_chunks and knowledge_vectors if chunks table is empty."""
        try:
            note_count = conn.execute("SELECT count(*) FROM knowledge_notes;").fetchone()[0]
            chunk_count = conn.execute("SELECT count(*) FROM note_chunks;").fetchone()[0]
        except Exception:
            return

        if note_count > 0 and chunk_count == 0:
            logger.info("Backfilling %d existing knowledge notes into note_chunks...", note_count)
            rows = conn.execute("SELECT id, content FROM knowledge_notes;").fetchall()
            now_iso = datetime.now().isoformat()
            for row in rows:
                note_id = str(row["id"])
                content = str(row["content"])
                chunks = chunk_markdown(content)
                if not chunks:
                    continue

                vectors: list[list[float]] | None = None
                if self.embedder is not None and hasattr(self.embedder, "embed"):
                    try:
                        vectors = self.embedder.embed(chunks)
                    except Exception as exc:
                        logger.warning("Backfill embedding failed for note %s: %s", note_id, exc)

                for idx, chunk_text in enumerate(chunks):
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO note_chunks (note_id, chunk_index, content, created_at) VALUES (?, ?, ?, ?);",
                        (note_id, idx, chunk_text, now_iso),
                    )
                    chunk_rowid = cur.lastrowid
                    if vectors and idx < len(vectors):
                        serialized = sqlite_vec.serialize_float32(vectors[idx])
                        conn.execute(
                            "INSERT INTO knowledge_vectors (chunk_rowid, embedding) VALUES (?, ?);",
                            (chunk_rowid, serialized),
                        )

        # Also backfill knowledge_vectors if chunks exist but vectors table is empty
        try:
            chunk_count_now = conn.execute("SELECT count(*) FROM note_chunks;").fetchone()[0]
            vec_count = conn.execute("SELECT count(*) FROM knowledge_vectors;").fetchone()[0]
            if chunk_count_now > 0 and vec_count == 0 and self.embedder is not None and hasattr(self.embedder, "embed"):
                logger.info("Backfilling vectors for %d existing chunks in knowledge_vectors...", chunk_count_now)
                chunk_rows = conn.execute("SELECT id, content FROM note_chunks ORDER BY id ASC;").fetchall()
                if chunk_rows:
                    texts = [str(r["content"]) for r in chunk_rows]
                    vectors = self.embedder.embed(texts)
                    for r, vec in zip(chunk_rows, vectors):
                        serialized = sqlite_vec.serialize_float32(vec)
                        conn.execute(
                            "INSERT INTO knowledge_vectors (chunk_rowid, embedding) VALUES (?, ?);",
                            (r["id"], serialized),
                        )
        except Exception as exc:
            logger.warning("Vector backfill check failed: %s", exc)

    def init_schema(self) -> None:
        """Initialize unified database tables, FTS5 index, and vec0 virtual tables with migration and backfill."""
        with self._connection() as conn:
            # Check if existing knowledge_vectors table needs migration from note_id to chunk_rowid
            tables = [
                str(r[0])
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name = 'knowledge_vectors';"
                ).fetchall()
            ]
            if tables:
                info = conn.execute("PRAGMA table_info(knowledge_vectors);").fetchall()
                col_names = [str(r["name"]) for r in info]
                if "note_id" in col_names:
                    logger.info("Migrating knowledge_vectors from note_id to chunk_rowid...")
                    conn.execute("DROP TABLE knowledge_vectors;")

            conn.executescript(INIT_UNIFIED_SCHEMA_SQL)
            self._backfill_chunks_if_needed(conn)
        logger.debug("Unified SQLite schema initialized at %s", self.db_path)

    def is_wal_mode(self) -> bool:
        """Check if SQLite is configured in WAL journal mode."""
        with self._connection() as conn:
            row = conn.execute("PRAGMA journal_mode;").fetchone()
            return bool(row and row[0].lower() == "wal")

    def get_table_names(self) -> list[str]:
        """Fetch list of all user-defined table names in the database."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            ).fetchall()
            return [str(row["name"]) for row in rows]

    def _upsert_source_state_sync(self, state: SourceState) -> None:
        """Upsert source state row synchronously."""
        sql = """
        INSERT INTO source_states (
            id, source_type, url_or_path, etag, last_modified,
            last_polled_at, consecutive_errors, backoff_until, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            source_type = excluded.source_type,
            url_or_path = excluded.url_or_path,
            etag = excluded.etag,
            last_modified = excluded.last_modified,
            last_polled_at = excluded.last_polled_at,
            consecutive_errors = excluded.consecutive_errors,
            backoff_until = excluded.backoff_until;
        """
        with self._connection() as conn:
            conn.execute(
                sql,
                (
                    state.id,
                    state.source_type,
                    state.url_or_path,
                    state.etag,
                    state.last_modified,
                    _to_iso(state.last_polled_at),
                    state.consecutive_errors,
                    _to_iso(state.backoff_until),
                    _to_iso(state.created_at),
                ),
            )

    async def upsert_source_state(self, state: SourceState) -> None:
        """Persist or update source state asynchronously."""
        await asyncio.to_thread(self._upsert_source_state_sync, state)

    def _get_source_state_sync(self, source_id: str) -> SourceState | None:
        """Retrieve source state by identifier synchronously."""
        sql = "SELECT * FROM source_states WHERE id = ?;"
        with self._connection() as conn:
            row = conn.execute(sql, (source_id,)).fetchone()
            if not row:
                return None
            return SourceState(
                id=row["id"],
                source_type=row["source_type"],
                url_or_path=row["url_or_path"],
                etag=row["etag"],
                last_modified=row["last_modified"],
                last_polled_at=_from_iso(row["last_polled_at"]),
                consecutive_errors=row["consecutive_errors"],
                backoff_until=_from_iso(row["backoff_until"]),
                created_at=_from_iso(row["created_at"]) or datetime.now(),
            )

    async def get_source_state(self, source_id: str) -> SourceState | None:
        """Retrieve source state asynchronously."""
        return await asyncio.to_thread(self._get_source_state_sync, source_id)

    def _list_source_states_sync(self) -> list[SourceState]:
        """Fetch all source states synchronously."""
        sql = "SELECT * FROM source_states ORDER BY id ASC;"
        with self._connection() as conn:
            rows = conn.execute(sql).fetchall()
            return [
                SourceState(
                    id=row["id"],
                    source_type=row["source_type"],
                    url_or_path=row["url_or_path"],
                    etag=row["etag"],
                    last_modified=row["last_modified"],
                    last_polled_at=_from_iso(row["last_polled_at"]),
                    consecutive_errors=row["consecutive_errors"],
                    backoff_until=_from_iso(row["backoff_until"]),
                    created_at=_from_iso(row["created_at"]) or datetime.now(),
                )
                for row in rows
            ]

    async def list_source_states(self) -> list[SourceState]:
        """List all source states asynchronously."""
        return await asyncio.to_thread(self._list_source_states_sync)

    def _save_raw_signals_sync(self, signals: list[RawSignal]) -> int:
        """Insert raw signals ignoring duplicates synchronously."""
        sql = """
        INSERT OR IGNORE INTO raw_signals (
            id, source_id, external_id, url, title, raw_content,
            clean_content, author, published_at, ingested_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        inserted_count = 0
        with self._connection() as conn:
            for s in signals:
                cur = conn.execute(
                    sql,
                    (
                        s.id,
                        s.source_id,
                        s.external_id,
                        s.url,
                        s.title,
                        s.raw_content,
                        s.clean_content,
                        s.author,
                        _to_iso(s.published_at),
                        _to_iso(s.ingested_at),
                        s.status.value,
                    ),
                )
                inserted_count += cur.rowcount
        return inserted_count

    async def save_raw_signals(self, signals: list[RawSignal]) -> int:
        """Batch save raw signals asynchronously."""
        return await asyncio.to_thread(self._save_raw_signals_sync, signals)

    def _get_raw_signals_sync(
        self,
        source_id: str | None,
        status: SignalStatus | str | None,
        limit: int,
    ) -> list[RawSignal]:
        """Query raw signals matching filters synchronously."""
        conditions: list[str] = []
        params: list[str | int] = []
        if source_id:
            conditions.append("source_id = ?")
            params.append(source_id)
        if status:
            status_val = status.value if isinstance(status, SignalStatus) else status
            conditions.append("status = ?")
            params.append(status_val)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM raw_signals {where} ORDER BY ingested_at DESC LIMIT ?;"
        params.append(limit)

        with self._connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [
                RawSignal(
                    id=row["id"],
                    source_id=row["source_id"] or row["source_type"],
                    external_id=row["external_id"],
                    url=row["url"] or row["source_url"],
                    title=row["title"],
                    raw_content=row["raw_content"],
                    clean_content=row["clean_content"],
                    author=row["author"],
                    published_at=_from_iso(row["published_at"]),
                    ingested_at=_from_iso(row["ingested_at"]) or datetime.now(),
                    status=SignalStatus(row["status"]),
                )
                for row in rows
            ]

    async def get_raw_signals(
        self,
        source_id: str | None = None,
        status: SignalStatus | str | None = None,
        limit: int = 50,
    ) -> list[RawSignal]:
        """Retrieve filtered raw signals asynchronously."""
        return await asyncio.to_thread(self._get_raw_signals_sync, source_id, status, limit)

    def _update_signal_status_sync(self, signal_id: str, status: SignalStatus) -> None:
        """Update signal status synchronously."""
        sql = "UPDATE raw_signals SET status = ? WHERE id = ?;"
        with self._connection() as conn:
            conn.execute(sql, (status.value, signal_id))

    async def update_signal_status(self, signal_id: str, status: SignalStatus) -> None:
        """Update signal status asynchronously."""
        await asyncio.to_thread(self._update_signal_status_sync, signal_id, status)

    async def get_pending_signals(self, limit: int = 5) -> list[RawSignal]:
        """Retrieve un-distilled raw signals in retained status asynchronously."""
        return await self.get_raw_signals(status=SignalStatus.RETAINED, limit=limit)


    async def mark_signal_status(self, signal_id: str, status: str | SignalStatus) -> None:
        """Update signal processing status with string or enum value."""
        target_status = status if isinstance(status, SignalStatus) else SignalStatus(status)
        await self.update_signal_status(signal_id, target_status)

    def _get_retained_signals_sync(self, limit: int = 5) -> list[dict[str, str | None]]:
        """Fetch pending retained signals for UC-1 proactive alert."""
        sql = """
        SELECT id, title, COALESCE(source_type, source_id, '') as source_type,
               COALESCE(source_url, url, '') as source_url,
               COALESCE(summary, raw_content, clean_content, '') as summary,
               COALESCE(created_at, ingested_at) as created_at
        FROM raw_signals
        WHERE status = 'retained'
        ORDER BY COALESCE(created_at, ingested_at) DESC
        LIMIT ?;
        """
        def _clean_summary(raw: str | None) -> str:
            if not raw:
                return ""
            trimmed = raw.strip()
            if trimmed.startswith("{") or "_highlightResult" in trimmed:
                return ""
            return trimmed

        with self._connection() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "source_type": row["source_type"],
                    "source_url": row["source_url"],
                    "summary": _clean_summary(row["summary"]),
                    "created_at": str(row["created_at"]) if row["created_at"] is not None else None,
                }
                for row in rows
            ]

    async def get_retained_signals(self, limit: int = 5) -> list[dict[str, str | None]]:
        """Retrieve retained signals asynchronously for UC-1 proactive alerts."""
        return await asyncio.to_thread(self._get_retained_signals_sync, limit)

    def _get_retained_signals_count_sync(self) -> int:
        """Count total raw signals currently in retained status."""
        sql = "SELECT count(*) FROM raw_signals WHERE status = 'retained';"
        with self._connection() as conn:
            row = conn.execute(sql).fetchone()
            return int(row[0]) if row else 0

    async def get_retained_signals_count(self) -> int:
        """Count total retained signals asynchronously."""
        return await asyncio.to_thread(self._get_retained_signals_count_sync)

    def _get_retained_signals_with_count_sync(self, limit: int = 20) -> dict[str, object]:
        """Fetch retained signals along with total count of retained records."""
        signals = self._get_retained_signals_sync(limit=limit)
        total_count = self._get_retained_signals_count_sync()
        return {"signals": signals, "total_count": total_count}

    async def get_retained_signals_with_count(self, limit: int = 20) -> dict[str, object]:
        """Fetch retained signals with total count asynchronously."""
        return await asyncio.to_thread(self._get_retained_signals_with_count_sync, limit)

    def _resolve_all_retained_signals_sync(self, action: str) -> int:
        """Resolve all currently retained signals with 'archive' -> 'archived' or 'discard' -> 'discarded'."""
        status_map = {"archive": "archived", "discard": "discarded"}
        new_status = status_map.get(action)
        if not new_status:
            raise ValueError(f"Invalid action '{action}'. Must be 'archive' or 'discard'.")

        sql_update = "UPDATE raw_signals SET status = ? WHERE status = 'retained';"
        with self._connection() as conn:
            cursor = conn.execute(sql_update, (new_status,))
            return cursor.rowcount

    async def resolve_all_retained_signals(self, action: str) -> int:
        """Resolve all retained signals asynchronously."""
        return await asyncio.to_thread(self._resolve_all_retained_signals_sync, action)

    def _get_raw_signal_by_id_sync(self, signal_id: str) -> dict[str, object] | None:
        """Fetch raw signal record by ID synchronously."""
        sql = "SELECT * FROM raw_signals WHERE id = ?;"
        with self._connection() as conn:
            row = conn.execute(sql, (signal_id,)).fetchone()
            return dict(row) if row else None

    async def get_raw_signal_by_id(self, signal_id: str) -> dict[str, object] | None:
        """Fetch raw signal record by ID asynchronously."""
        return await asyncio.to_thread(self._get_raw_signal_by_id_sync, signal_id)

    def _resolve_signal_sync(self, signal_id: str, action: str) -> bool:
        """Resolve signal by ID with 'archive' -> 'archived' or 'discard' -> 'discarded'."""
        status_map = {"archive": "archived", "discard": "discarded"}
        new_status = status_map.get(action)
        if not new_status:
            raise ValueError(f"Invalid action '{action}'. Must be 'archive' or 'discard'.")

        sql_check = "SELECT id FROM raw_signals WHERE id = ?;"
        sql_update = "UPDATE raw_signals SET status = ? WHERE id = ?;"
        with self._connection() as conn:
            exists = conn.execute(sql_check, (signal_id,)).fetchone()
            if not exists:
                return False
            conn.execute(sql_update, (new_status, signal_id))
            return True

    async def resolve_signal(self, signal_id: str, action: str) -> bool:
        """Resolve signal asynchronously."""
        return await asyncio.to_thread(self._resolve_signal_sync, signal_id, action)

    def _save_knowledge_note_sync(
        self,
        note: KnowledgeNote,
        embedding: list[float] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> None:
        """Persist knowledge note, update FTS5, chunk content, and index vector embeddings."""
        insert_note_sql = """
        INSERT INTO knowledge_notes (
            id, slug, title, summary, content, tags, sources, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            slug = excluded.slug,
            title = excluded.title,
            summary = excluded.summary,
            content = excluded.content,
            tags = excluded.tags,
            sources = excluded.sources,
            updated_at = excluded.updated_at;
        """
        tags_json = json.dumps(note.tags)
        now_iso = _to_iso(note.updated_at) or datetime.now().isoformat()
        chunks = chunk_markdown(note.content)
        if not chunks:
            fallback = f"{note.title}\n{note.summary}".strip()
            chunks = [fallback] if fallback else [note.title]

        # Determine vectors for chunks
        chunk_vectors: list[list[float]] | None = None
        if embeddings is not None:
            chunk_vectors = embeddings
        elif embedding is not None:
            chunk_vectors = [embedding] * len(chunks)
        elif self.embedder is not None and hasattr(self.embedder, "embed"):
            try:
                chunk_vectors = self.embedder.embed(chunks)
            except Exception as exc:
                logger.warning("Failed to generate embeddings for note %s: %s", note.id, exc)

        with self._connection() as conn:
            conn.execute(
                insert_note_sql,
                (
                    note.id,
                    note.slug,
                    note.title,
                    note.summary,
                    note.content,
                    tags_json,
                    json.dumps(note.sources),
                    _to_iso(note.created_at),
                    _to_iso(note.updated_at),
                ),
            )
            # Update FTS5 virtual table
            conn.execute("DELETE FROM knowledge_fts WHERE note_id = ?;", (note.id,))
            conn.execute(
                "INSERT INTO knowledge_fts (note_id, title, summary, content, tags) VALUES (?, ?, ?, ?, ?);",
                (note.id, note.title, note.summary, note.content, tags_json),
            )
            # Idempotent cleanup of existing chunks and vectors for this note
            old_chunks = conn.execute("SELECT id FROM note_chunks WHERE note_id = ?;", (note.id,)).fetchall()
            for r in old_chunks:
                conn.execute("DELETE FROM knowledge_vectors WHERE chunk_rowid = ?;", (r["id"],))
            conn.execute("DELETE FROM note_chunks WHERE note_id = ?;", (note.id,))

            # Insert new chunks and vector embeddings
            for idx, chunk_text in enumerate(chunks):
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO note_chunks (note_id, chunk_index, content, created_at) VALUES (?, ?, ?, ?);",
                    (note.id, idx, chunk_text, now_iso),
                )
                chunk_rowid = cur.lastrowid
                if chunk_vectors and idx < len(chunk_vectors):
                    serialized = sqlite_vec.serialize_float32(chunk_vectors[idx])
                    conn.execute(
                        "INSERT INTO knowledge_vectors (chunk_rowid, embedding) VALUES (?, ?);",
                        (chunk_rowid, serialized),
                    )

    async def save_knowledge_note(
        self,
        note: KnowledgeNote,
        embedding: list[float] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> None:
        """Persist or update knowledge note and its chunked indexes asynchronously."""
        computed_embeddings = embeddings
        if embedding is None and embeddings is None and self.embedder is not None and hasattr(self.embedder, "embed_batch"):
            chunks = chunk_markdown(note.content)
            if not chunks:
                fallback = f"{note.title}\n{note.summary}".strip()
                chunks = [fallback] if fallback else [note.title]
            try:
                computed_embeddings = await self.embedder.embed_batch(chunks)
            except Exception as exc:
                logger.warning("Async batch embedding failed for note %s: %s", note.id, exc)

        await asyncio.to_thread(self._save_knowledge_note_sync, note, embedding, computed_embeddings)

    def _delete_knowledge_note_sync(self, note_id: str) -> bool:
        """Delete a knowledge note, cleaning up its chunks, vectors, and FTS entries."""
        with self._connection() as conn:
            exists = conn.execute("SELECT 1 FROM knowledge_notes WHERE id = ?;", (note_id,)).fetchone()
            if not exists:
                return False
            chunk_rows = conn.execute("SELECT id FROM note_chunks WHERE note_id = ?;", (note_id,)).fetchall()
            for r in chunk_rows:
                conn.execute("DELETE FROM knowledge_vectors WHERE chunk_rowid = ?;", (r["id"],))
            conn.execute("DELETE FROM note_chunks WHERE note_id = ?;", (note_id,))
            conn.execute("DELETE FROM knowledge_fts WHERE note_id = ?;", (note_id,))
            conn.execute("DELETE FROM knowledge_notes WHERE id = ?;", (note_id,))
            return True

    async def delete_knowledge_note(self, note_id: str) -> bool:
        """Delete a knowledge note and all associated indexes asynchronously."""
        return await asyncio.to_thread(self._delete_knowledge_note_sync, note_id)

    def _get_note_chunks_sync(self, note_id: str) -> list[str]:
        """Fetch chunk contents for a given note_id ordered by chunk_index."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT content FROM note_chunks WHERE note_id = ? ORDER BY chunk_index ASC;",
                (note_id,),
            ).fetchall()
            return [str(r["content"]) for r in rows]

    async def get_note_chunks(self, note_id: str) -> list[str]:
        """Fetch chunk contents for a given note_id asynchronously."""
        return await asyncio.to_thread(self._get_note_chunks_sync, note_id)

    def _has_content_hash_sync(self, content_hash: str) -> bool:
        """Check if a document with this SHA-256 hash or text ID prefix already exists in database."""
        with self._connection() as conn:
            # Check raw_signals id (e.g. text_<hash> or sig_<hash>)
            sig_exists = conn.execute(
                "SELECT 1 FROM raw_signals WHERE id LIKE ? OR external_id = ? LIMIT 1;",
                (f"%{content_hash}%", content_hash),
            ).fetchone()
            if sig_exists:
                return True

            # Check knowledge_notes id or sources
            note_exists = conn.execute(
                "SELECT 1 FROM knowledge_notes WHERE id LIKE ? OR sources LIKE ? LIMIT 1;",
                (f"%{content_hash}%", f"%{content_hash}%"),
            ).fetchone()
            return bool(note_exists)

    async def has_content_hash(self, content_hash: str) -> bool:
        """Check if document hash already exists in raw signals or knowledge notes asynchronously."""
        return await asyncio.to_thread(self._has_content_hash_sync, content_hash)

    def _has_source_url_sync(self, url: str) -> bool:
        """Check if an external URL is already present in raw_signals or knowledge_notes."""
        with self._connection() as conn:
            sig_exists = conn.execute(
                "SELECT 1 FROM raw_signals WHERE url = ? OR source_url = ? LIMIT 1;",
                (url, url),
            ).fetchone()
            if sig_exists:
                return True

            note_exists = conn.execute(
                "SELECT 1 FROM knowledge_notes WHERE sources LIKE ? LIMIT 1;",
                (f"%{url}%",),
            ).fetchone()
            return bool(note_exists)

    async def has_source_url(self, url: str) -> bool:
        """Check if source URL is already indexed in database asynchronously."""
        return await asyncio.to_thread(self._has_source_url_sync, url)

    def _get_knowledge_note_by_slug_sync(self, slug: str) -> KnowledgeNote | None:
        """Query knowledge note by unique slug synchronously."""
        sql = "SELECT * FROM knowledge_notes WHERE slug = ?;"
        with self._connection() as conn:
            row = conn.execute(sql, (slug,)).fetchone()
            return _row_to_knowledge_note(row) if row else None

    async def get_knowledge_note_by_slug(self, slug: str) -> KnowledgeNote | None:
        """Fetch knowledge note by slug asynchronously."""
        return await asyncio.to_thread(self._get_knowledge_note_by_slug_sync, slug)

    def _list_knowledge_notes_sync(self, limit: int) -> list[KnowledgeNote]:
        """List knowledge notes ordered by creation time synchronously."""
        sql = "SELECT * FROM knowledge_notes ORDER BY created_at DESC LIMIT ?;"
        with self._connection() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
            return [_row_to_knowledge_note(row) for row in rows]

    async def list_knowledge_notes(self, limit: int = 50) -> list[KnowledgeNote]:
        """List knowledge notes asynchronously."""
        return await asyncio.to_thread(self._list_knowledge_notes_sync, limit)

    def _get_popular_tags_sync(self, limit: int = 30) -> list[str]:
        """Fetch most frequently used tags across all knowledge notes synchronously."""
        sql = "SELECT tags FROM knowledge_notes;"
        tag_counts: Counter[str] = Counter()
        with self._connection() as conn:
            rows = conn.execute(sql).fetchall()
            for row in rows:
                tags_raw = row["tags"] if isinstance(row, sqlite3.Row) else row[0]
                if not tags_raw:
                    continue
                try:
                    parsed = json.loads(tags_raw)
                    if isinstance(parsed, list):
                        for tag in parsed:
                            if isinstance(tag, str) and tag.strip():
                                tag_counts[tag.strip()] += 1
                except (json.JSONDecodeError, TypeError):
                    continue
        return [tag for tag, _ in tag_counts.most_common(limit)]

    async def get_popular_tags(self, limit: int = 30) -> list[str]:
        """Fetch most frequently used tags across all knowledge notes asynchronously."""
        return await asyncio.to_thread(self._get_popular_tags_sync, limit)


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

    def _search_notes_sync(
        self,
        query: str,
        query_embedding: list[float] | None,
        mode: str,
        limit: int,
        k: int,
    ) -> list[tuple[KnowledgeNote, float]]:
        """Execute hybrid, lexical, or semantic note retrieval using RRF fusion."""
        candidate_pool_size = max(limit * 5, 50)
        with self._connection() as conn:
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
        """Search knowledge notes using RRF fusion, lexical FTS5, or semantic vectors."""
        return await asyncio.to_thread(self._search_notes_sync, query, query_embedding, mode, limit, k)

