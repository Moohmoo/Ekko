"""SQLite concrete persistence repository for Radar signals and source states."""

import asyncio
from datetime import datetime
from typing import Any

from ekko.core.logger import get_logger
from ekko.db.connection import DatabaseConnection
from ekko.domains.radar.entities import RawSignal, SignalStatus, SourceState

logger = get_logger("domains.radar.repository")


def _to_iso(dt: datetime | None) -> str | None:
    """Format datetime to ISO string safely."""
    return dt.isoformat() if dt else None


def _from_iso(val: str | None) -> datetime | None:
    """Parse ISO string back to datetime safely."""
    return datetime.fromisoformat(val) if val else None


class SqliteSignalRepository:
    """SQLite implementation of SignalRepositoryPort for Radar domain."""

    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def upsert_source_state_sync(self, state: SourceState) -> None:
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
        with self.connection.connection() as conn:
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
        await asyncio.to_thread(self.upsert_source_state_sync, state)

    def get_source_state_sync(self, source_id: str) -> SourceState | None:
        """Retrieve source state by identifier synchronously."""
        sql = "SELECT * FROM source_states WHERE id = ?;"
        with self.connection.connection() as conn:
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
        return await asyncio.to_thread(self.get_source_state_sync, source_id)

    def list_source_states_sync(self) -> list[SourceState]:
        """Fetch all source states synchronously."""
        sql = "SELECT * FROM source_states ORDER BY id ASC;"
        with self.connection.connection() as conn:
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
        return await asyncio.to_thread(self.list_source_states_sync)

    def save_raw_signals_sync(self, signals: list[RawSignal]) -> int:
        """Insert raw signals ignoring duplicates synchronously."""
        sql = """
        INSERT OR IGNORE INTO raw_signals (
            id, source_id, external_id, url, title, raw_content,
            clean_content, author, published_at, ingested_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        inserted_count = 0
        with self.connection.connection() as conn:
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
        return await asyncio.to_thread(self.save_raw_signals_sync, signals)

    def get_raw_signals_sync(
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

        with self.connection.connection() as conn:
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
        return await asyncio.to_thread(self.get_raw_signals_sync, source_id, status, limit)

    def update_signal_status_sync(self, signal_id: str, status: SignalStatus) -> None:
        """Update signal status synchronously."""
        sql = "UPDATE raw_signals SET status = ? WHERE id = ?;"
        with self.connection.connection() as conn:
            conn.execute(sql, (status.value, signal_id))

    async def update_signal_status(self, signal_id: str, status: SignalStatus) -> None:
        """Update signal status asynchronously."""
        await asyncio.to_thread(self.update_signal_status_sync, signal_id, status)

    async def mark_signal_status(self, signal_id: str, status: str | SignalStatus) -> None:
        """Update signal processing status with string or enum value."""
        target_status = status if isinstance(status, SignalStatus) else SignalStatus(status)
        await self.update_signal_status(signal_id, target_status)

    async def get_pending_signals(self, limit: int = 5) -> list[RawSignal]:
        """Retrieve un-distilled raw signals in retained status asynchronously."""
        return await self.get_raw_signals(status=SignalStatus.RETAINED, limit=limit)

    def get_retained_signals_sync(self, limit: int = 5) -> list[dict[str, str | None]]:
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

        with self.connection.connection() as conn:
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
        return await asyncio.to_thread(self.get_retained_signals_sync, limit)

    def get_retained_signals_count_sync(self) -> int:
        """Count total raw signals currently in retained status."""
        sql = "SELECT count(*) FROM raw_signals WHERE status = 'retained';"
        with self.connection.connection() as conn:
            row = conn.execute(sql).fetchone()
            return int(row[0]) if row else 0

    async def get_retained_signals_count(self) -> int:
        """Count total retained signals asynchronously."""
        return await asyncio.to_thread(self.get_retained_signals_count_sync)

    async def get_retained_signals_with_count(self, limit: int = 20) -> dict[str, object]:
        """Fetch retained signals along with total count of retained records asynchronously."""
        signals = await self.get_retained_signals(limit=limit)
        total_count = await self.get_retained_signals_count()
        return {"signals": signals, "total_count": total_count}

    def resolve_all_retained_signals_sync(self, action: str) -> int:
        """Resolve all currently retained signals with 'archive' -> 'archived' or 'discard' -> 'discarded'."""
        status_map = {"archive": "archived", "discard": "discarded"}
        new_status = status_map.get(action)
        if not new_status:
            raise ValueError(f"Invalid action '{action}'. Must be 'archive' or 'discard'.")

        sql_update = "UPDATE raw_signals SET status = ? WHERE status = 'retained';"
        with self.connection.connection() as conn:
            cursor = conn.execute(sql_update, (new_status,))
            return cursor.rowcount

    async def resolve_all_retained_signals(self, action: str) -> int:
        """Resolve all retained signals asynchronously."""
        return await asyncio.to_thread(self.resolve_all_retained_signals_sync, action)

    def get_raw_signal_by_id_sync(self, signal_id: str) -> dict[str, Any] | None:
        """Fetch raw signal record by ID synchronously."""
        sql = "SELECT * FROM raw_signals WHERE id = ?;"
        with self.connection.connection() as conn:
            row = conn.execute(sql, (signal_id,)).fetchone()
            return dict(row) if row else None

    async def get_raw_signal_by_id(self, signal_id: str) -> dict[str, Any] | None:
        """Fetch raw signal record by ID asynchronously."""
        return await asyncio.to_thread(self.get_raw_signal_by_id_sync, signal_id)

    def resolve_signal_sync(self, signal_id: str, action: str) -> bool:
        """Resolve signal by ID with 'archive' -> 'archived' or 'discard' -> 'discarded'."""
        status_map = {"archive": "archived", "discard": "discarded"}
        new_status = status_map.get(action)
        if not new_status:
            raise ValueError(f"Invalid action '{action}'. Must be 'archive' or 'discard'.")

        sql_check = "SELECT id FROM raw_signals WHERE id = ?;"
        sql_update = "UPDATE raw_signals SET status = ? WHERE id = ?;"
        with self.connection.connection() as conn:
            exists = conn.execute(sql_check, (signal_id,)).fetchone()
            if not exists:
                return False
            conn.execute(sql_update, (new_status, signal_id))
            return True

    async def resolve_signal(self, signal_id: str, action: str) -> bool:
        """Resolve signal asynchronously."""
        return await asyncio.to_thread(self.resolve_signal_sync, signal_id, action)

    def has_content_hash_sync(self, content_hash: str) -> bool:
        """Check if raw_signals has a record with this SHA-256 hash or text ID prefix."""
        with self.connection.connection() as conn:
            sig_exists = conn.execute(
                "SELECT 1 FROM raw_signals WHERE id LIKE ? OR external_id = ? LIMIT 1;",
                (f"%{content_hash}%", content_hash),
            ).fetchone()
            return bool(sig_exists)

    async def has_content_hash(self, content_hash: str) -> bool:
        """Check if content hash exists in raw signals asynchronously."""
        return await asyncio.to_thread(self.has_content_hash_sync, content_hash)

    def has_source_url_sync(self, url: str) -> bool:
        """Check if an external URL is already present in raw_signals."""
        with self.connection.connection() as conn:
            sig_exists = conn.execute(
                "SELECT 1 FROM raw_signals WHERE url = ? OR source_url = ? LIMIT 1;",
                (url, url),
            ).fetchone()
            return bool(sig_exists)

    async def has_source_url(self, url: str) -> bool:
        """Check if source URL is already indexed in raw signals asynchronously."""
        return await asyncio.to_thread(self.has_source_url_sync, url)
