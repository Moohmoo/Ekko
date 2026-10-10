"""Thread-safe SQLite database manager for Ekko unified persistence."""

import asyncio
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any

from ekko.infrastructure.database.models import (
    KnowledgeNote,
    RawSignal,
    SignalStatus,
    SourceState,
)
from ekko.infrastructure.database.schema import INIT_UNIFIED_SCHEMA_SQL
from ekko.utils.logger import get_logger

logger = get_logger("infrastructure.database")


def _to_iso(dt: datetime | None) -> str | None:
    """Format datetime to ISO string safely."""
    return dt.isoformat() if dt else None


def _from_iso(val: str | None) -> datetime | None:
    """Parse ISO string back to datetime safely."""
    return datetime.fromisoformat(val) if val else None


class DatabaseManager:
    """Manages asynchronous access to unified SQLite tables in WAL mode."""

    def __init__(self, db_path: str | Path = "data/ekko.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Create and configure a SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_schema(self) -> None:
        """Initialize unified database tables and indices synchronously."""
        with self._get_connection() as conn:
            conn.executescript(INIT_UNIFIED_SCHEMA_SQL)
        logger.debug("Unified SQLite schema initialized at %s", self.db_path)

    def is_wal_mode(self) -> bool:
        """Check if SQLite is configured in WAL journal mode."""
        with self._get_connection() as conn:
            row = conn.execute("PRAGMA journal_mode;").fetchone()
            return bool(row and row[0].lower() == "wal")

    def get_table_names(self) -> list[str]:
        """Fetch list of all user-defined table names in the database."""
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
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
        with self._get_connection() as conn:
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
        status: SignalStatus | None,
        limit: int,
    ) -> list[RawSignal]:
        """Query raw signals matching filters synchronously."""
        conditions: list[str] = []
        params: list[Any] = []
        if source_id:
            conditions.append("source_id = ?")
            params.append(source_id)
        if status:
            conditions.append("status = ?")
            params.append(status.value)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM raw_signals {where} ORDER BY ingested_at DESC LIMIT ?;"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [
                RawSignal(
                    id=row["id"],
                    source_id=row["source_id"],
                    external_id=row["external_id"],
                    url=row["url"],
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
        status: SignalStatus | None = None,
        limit: int = 50,
    ) -> list[RawSignal]:
        """Retrieve filtered raw signals asynchronously."""
        return await asyncio.to_thread(self._get_raw_signals_sync, source_id, status, limit)

    def _update_signal_status_sync(self, signal_id: str, status: SignalStatus) -> None:
        """Update signal status synchronously."""
        sql = "UPDATE raw_signals SET status = ? WHERE id = ?;"
        with self._get_connection() as conn:
            conn.execute(sql, (status.value, signal_id))

    async def update_signal_status(self, signal_id: str, status: SignalStatus) -> None:
        """Update signal status asynchronously."""
        await asyncio.to_thread(self._update_signal_status_sync, signal_id, status)

    def _save_knowledge_note_sync(self, note: KnowledgeNote) -> None:
        """Insert or replace knowledge note synchronously."""
        sql = """
        INSERT INTO knowledge_notes (
            id, slug, title, summary, content, tags, sources, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            title = excluded.title,
            summary = excluded.summary,
            content = excluded.content,
            tags = excluded.tags,
            sources = excluded.sources,
            updated_at = excluded.updated_at;
        """
        with self._get_connection() as conn:
            conn.execute(
                sql,
                (
                    note.id,
                    note.slug,
                    note.title,
                    note.summary,
                    note.content,
                    json.dumps(note.tags),
                    json.dumps(note.sources),
                    _to_iso(note.created_at),
                    _to_iso(note.updated_at),
                ),
            )

    async def save_knowledge_note(self, note: KnowledgeNote) -> None:
        """Persist or update knowledge note asynchronously."""
        await asyncio.to_thread(self._save_knowledge_note_sync, note)

    def _get_knowledge_note_by_slug_sync(self, slug: str) -> KnowledgeNote | None:
        """Query knowledge note by unique slug synchronously."""
        sql = "SELECT * FROM knowledge_notes WHERE slug = ?;"
        with self._get_connection() as conn:
            row = conn.execute(sql, (slug,)).fetchone()
            if not row:
                return None
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

    async def get_knowledge_note_by_slug(self, slug: str) -> KnowledgeNote | None:
        """Fetch knowledge note by slug asynchronously."""
        return await asyncio.to_thread(self._get_knowledge_note_by_slug_sync, slug)

    def _list_knowledge_notes_sync(self, limit: int) -> list[KnowledgeNote]:
        """List knowledge notes ordered by creation time synchronously."""
        sql = "SELECT * FROM knowledge_notes ORDER BY created_at DESC LIMIT ?;"
        with self._get_connection() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
            return [
                KnowledgeNote(
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
                for row in rows
            ]

    async def list_knowledge_notes(self, limit: int = 50) -> list[KnowledgeNote]:
        """List knowledge notes asynchronously."""
        return await asyncio.to_thread(self._list_knowledge_notes_sync, limit)
