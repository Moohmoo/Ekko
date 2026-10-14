"""Technical Unit of Work and connection coordinator for Ekko persistence."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Any

from ekko.db.connection import DatabaseConnection
from ekko.domains.buffer.repository import SqliteNoteRepository
from ekko.domains.buffer.search import SqliteHybridSearchEngine, _sanitize_fts_query
from ekko.domains.radar.repository import SqliteSignalRepository
from ekko.providers.embedder import EmbedderPort

__all__ = ["DatabaseManager", "_sanitize_fts_query"]


class _SingleConnectionAdapter:
    """Adapts a single persistent SQLite connection for transactional repository execution."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        yield self.conn


class DatabaseManager:
    """Technical Unit of Work and connection coordinator for Ekko persistence."""

    def __init__(
        self,
        db_path: str | Path = "data/ekko.db",
        auto_init: bool = True,
        embedder: EmbedderPort | None = None,
        connection: DatabaseConnection | None = None,
    ) -> None:
        self.connection = connection or DatabaseConnection(db_path=db_path)
        self.db_path = self.connection.db_path
        self.embedder = embedder
        self.signals = SqliteSignalRepository(self.connection)
        self.notes = SqliteNoteRepository(self.connection, embedder=embedder)
        self.search = SqliteHybridSearchEngine(self.connection)
        if auto_init:
            self.init_schema()

    def __enter__(self) -> "DatabaseManager":
        """Enter transactional context manager, binding domain repositories to an active connection."""
        self.conn = self.connection.create_connection()
        adapter = _SingleConnectionAdapter(self.conn)
        self.signals = SqliteSignalRepository(adapter)
        self.notes = SqliteNoteRepository(adapter, embedder=self.embedder)
        self.search = SqliteHybridSearchEngine(adapter)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit transactional context, committing or rolling back transaction and closing connection."""
        if hasattr(self, "conn"):
            try:
                if exc_type is not None:
                    self.conn.rollback()
                else:
                    self.conn.commit()
            finally:
                self.conn.close()

    def _create_connection(self) -> sqlite3.Connection:
        """Create standalone connection for backwards compatibility."""
        return self.connection.create_connection()

    def _get_connection(self) -> sqlite3.Connection:
        """Alias creating connection for backwards compatibility."""
        return self.connection.create_connection()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager guaranteeing connection closure and transaction commit/rollback."""
        with self.connection.connection() as conn:
            yield conn

    def init_schema(self) -> None:
        """Initialize database schema, migrations, and note chunk backfilling."""
        self.connection.init_schema()
        with self.connection.connection() as conn:
            self.notes.backfill_chunks_if_needed(conn)

    def is_wal_mode(self) -> bool:
        """Check if SQLite is running in WAL journal mode."""
        return self.connection.is_wal_mode()

    def get_table_names(self) -> list[str]:
        """List user-defined tables in database."""
        return self.connection.get_table_names()
