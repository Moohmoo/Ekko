"""Tests unitaires pour la gestion de mémoire et du profil utilisateur (Brique 4)."""

from pathlib import Path
from core.memory import SQLiteMemory, load_user_profile


def test_load_user_profile_creates_default(tmp_path: Path) -> None:
    """Vérifie la création automatique du profil par défaut si absent."""
    profile_content = load_user_profile(tmp_path)
    assert "Profil Utilisateur" in profile_content
    assert (tmp_path / "user_profile.md").is_file()


def test_load_user_profile_reads_existing(tmp_path: Path) -> None:
    """Vérifie la lecture d'un profil personnalisé existant."""
    custom_file = tmp_path / "user_profile.md"
    custom_file.write_text("Custom user profile content", encoding="utf-8")

    profile_content = load_user_profile(tmp_path)
    assert profile_content == "Custom user profile content"


def test_sqlite_memory_messages_flow(tmp_path: Path) -> None:
    """Vérifie l'enregistrement et la restitution ordonnée des messages."""
    db_file = tmp_path / "test_ekko.db"
    memory = SQLiteMemory(db_file)

    memory.record_message("session_1", "user", "Message 1")
    memory.record_message("session_1", "assistant", "Réponse 1")
    memory.record_message("session_2", "user", "Message autre session")

    history = memory.get_recent_messages("session_1", limit=10)
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Message 1"}
    assert history[1] == {"role": "assistant", "content": "Réponse 1"}


def test_sqlite_memory_tasks_flow(tmp_path: Path) -> None:
    """Vérifie l'enregistrement et la consultation du journal des tâches."""
    db_file = tmp_path / "test_ekko.db"
    memory = SQLiteMemory(db_file)

    memory.record_task_run("test_tool", "success", "Opération terminée avec succès")
    tasks = memory.get_recent_tasks(limit=5)

    assert len(tasks) == 1
    assert tasks[0]["tool_name"] == "test_tool"
    assert tasks[0]["status"] == "success"
    assert "Opération terminée" in tasks[0]["summary"]


def test_sqlite_memory_seen_articles(tmp_path: Path) -> None:
    """Vérifie l'enregistrement et le statut d'articles répertoriés dans la mémoire."""
    db_file = tmp_path / "test_ekko.db"
    memory = SQLiteMemory(db_file)

    assert not memory.is_article_seen("https://example.com/art1")
    memory.record_seen_articles(["https://example.com/art1", "https://example.com/art2"])

    assert memory.is_article_seen("https://example.com/art1")
    assert memory.is_article_seen("https://example.com/art2")
    assert not memory.is_article_seen("https://example.com/art3")
    assert memory.get_seen_urls() == {"https://example.com/art1", "https://example.com/art2"}

