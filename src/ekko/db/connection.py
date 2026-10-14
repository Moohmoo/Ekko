"""Thread-safe SQLite connection and schema lifecycle management for Ekko."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
import sqlite3

import sqlite_vec

from ekko.core.logger import get_logger
from ekko.db.schema import INIT_UNIFIED_SCHEMA_SQL

logger = get_logger("db.connection")


class DatabaseConnection:
    """Manages SQLite database connections, extensions, and schema initialization."""

    def __init__(self, db_path: str | Path = "data/ekko.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def create_connection(self) -> sqlite3.Connection:
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
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager guaranteeing connection closure and transaction commit/rollback."""
        conn = self.create_connection()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Initialize unified database tables, FTS5 index, and vec0 virtual tables with schema migration."""
        with self.connection() as conn:
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
        logger.debug("Unified SQLite schema initialized at %s", self.db_path)

    def is_wal_mode(self) -> bool:
        """Check if SQLite is configured in WAL journal mode."""
        with self.connection() as conn:
            row = conn.execute("PRAGMA journal_mode;").fetchone()
            return bool(row and str(row[0]).lower() == "wal")

    def get_table_names(self) -> list[str]:
        """Fetch list of all user-defined table names in the database."""
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            ).fetchall()
            return [str(row["name"]) for row in rows]
