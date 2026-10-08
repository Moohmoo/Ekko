"""Module de persistance et stockage des sessions pour Ekko.

Gère l'enregistrement et la récupération de l'historique des messages
au sein d'une base relationnelle SQLite locale épurée.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

class SessionStorage:
    """Gestionnaire de persistance SQLite dédié à l'historique des messages."""

    def __init__(self, db_path: Path) -> None:
        """Initialise la base SQLite et crée la table des messages si absente."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Ouvre une connexion SQLite avec fermeture et validation garanties."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Initialise la table unique des messages, son index et le mode WAL."""
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA busy_timeout = 10000")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, id DESC)
            """)

    def record_message(self, session_id: str, role: str, content: str) -> None:
        """Enregistre un message horodaté dans la session spécifiée."""
        now = datetime.now().isoformat()
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, now),
            )

    def get_recent_messages(self, session_id: str, limit: int = 10) -> list[dict[str, str]]:
        """Récupère les derniers messages d'une session par ordre chronologique."""
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT role, content FROM messages
                WHERE session_id = ? ORDER BY id DESC LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [{"role": str(r["role"]), "content": str(r["content"])} for r in reversed(rows)]

    def clear_session_messages(self, session_id: str) -> int:
        """Supprime tous les messages associés à une session donnée."""
        with self._connection() as conn:
            return conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,)).rowcount

    def purge_old_history(self, days: int = 30, retention_days: int | None = None) -> dict[str, int]:
        """Supprime les messages antérieurs au seuil de rétention configuré."""
        effective_days = retention_days if retention_days is not None else days
        threshold = (datetime.now() - timedelta(days=effective_days)).isoformat()
        with self._connection() as conn:
            count = conn.execute("DELETE FROM messages WHERE timestamp <= ?", (threshold,)).rowcount
        return {"messages": count}



