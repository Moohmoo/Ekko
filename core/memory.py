"""Gestionnaire d'état et de mémoire pour l'agent Ekko (Brique 4).

Combine une mémoire long terme documentaire (profil utilisateur Markdown)
et une mémoire moyen terme relationnelle (sessions et journal de bord SQLite).
"""

from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any

DEFAULT_PROFILE_CONTENT = """# Profil Utilisateur - Mohamed

- **Rôle :** Ingénieur informatique & Bioinformatique
- **Préférences de communication :**
  - Réponses directes, synthétiques et factuelles.
  - Zéro bavardage, pas de salutations ni de politesses superflues.
  - Précision technique et rigueur d'ingénierie logicielle.
- **Environnement technique :**
  - OS : Ubuntu Linux
  - Matériel : AMD Ryzen 7, NVIDIA GeForce RTX 5050 (8 Go VRAM), 16 Go RAM
  - Gestionnaire de paquets : uv
"""


def load_user_profile(memory_dir: Path) -> str:
    """Charge le profil Markdown de l'utilisateur ou initialise le gabarit par défaut."""
    profile_path = memory_dir / "user_profile.md"
    if not profile_path.is_file():
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(DEFAULT_PROFILE_CONTENT.strip() + "\n", encoding="utf-8")
    return profile_path.read_text(encoding="utf-8").strip()


class SQLiteMemory:
    """Mémoire relationnelle locale pour les sessions et le journal des tâches."""

    def __init__(self, db_path: Path) -> None:
        """Initialise la connexion SQLite et crée les tables au besoin."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Ouvre une connexion SQLite avec support de row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Crée les tables de sessions et de tâches si elles n'existent pas."""
        with self._get_connection() as conn:
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
                CREATE TABLE IF NOT EXISTS task_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_articles (
                    url TEXT PRIMARY KEY,
                    date_added TEXT NOT NULL
                )
            """)

    def record_message(self, session_id: str, role: str, content: str) -> None:
        """Enregistre un message dans l'historique de la session courante."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, now),
            )

    def get_recent_messages(self, session_id: str, limit: int = 10) -> list[dict[str, str]]:
        """Récupère les derniers messages d'une session par ordre chronologique."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT role, content FROM messages
                WHERE session_id = ? ORDER BY id DESC LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def record_task_run(self, tool_name: str, status: str, summary: str) -> None:
        """Consigne l'exécution d'un outil dans le journal de bord persistant."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO task_runs (tool_name, status, summary, timestamp) VALUES (?, ?, ?, ?)",
                (tool_name, status, summary, now),
            )

    def get_recent_tasks(self, limit: int = 5) -> list[dict[str, Any]]:
        """Récupère les dernières tâches exécutées par l'agent."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT tool_name, status, summary, timestamp FROM task_runs
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def is_article_seen(self, url: str) -> bool:
        """Vérifie si une URL a déjà été répertoriée dans la base."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT 1 FROM seen_articles WHERE url = ?", (url,)).fetchone()
            return row is not None

    def get_seen_urls(self) -> set[str]:
        """Récupère l'ensemble de toutes les URLs répertoriées."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT url FROM seen_articles").fetchall()
            return {row["url"] for row in rows}

    def record_seen_articles(self, urls: list[str]) -> None:
        """Enregistre un lot d'URLs avec la date courante."""
        if not urls:
            return
        today_str = datetime.now().date().isoformat()
        entries = [(url, today_str) for url in urls]
        with self._get_connection() as conn:
            conn.executemany("INSERT OR IGNORE INTO seen_articles (url, date_added) VALUES (?, ?)", entries)

