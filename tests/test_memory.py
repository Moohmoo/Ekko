"""Tests unitaires pour la gestion de mémoire et du profil utilisateur (Brique 4)."""

from pathlib import Path
from agent.memory import SQLiteMemory, load_user_profile


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



def test_sqlite_memory_clear_session_messages(tmp_path: Path) -> None:
    """Vérifie la suppression ciblée des messages d'une session."""
    db_file = tmp_path / "test_ekko.db"
    memory = SQLiteMemory(db_file)

    memory.record_message("sess_a", "user", "Hello A")
    memory.record_message("sess_b", "user", "Hello B")

    deleted = memory.clear_session_messages("sess_a")
    assert deleted == 1
    assert len(memory.get_recent_messages("sess_a")) == 0
    assert len(memory.get_recent_messages("sess_b")) == 1


def test_sqlite_memory_purge_old_history(tmp_path: Path) -> None:
    """Vérifie la purge globale des messages et tâches selon le TTL."""
    db_file = tmp_path / "test_ekko.db"
    memory = SQLiteMemory(db_file)

    memory.record_message("sess_old", "user", "Old message")
    memory.record_task_run("old_tool", "success", "Old summary")

    # Purge avec 0 jours (tout est antérieur ou égal à l'instant présent)
    res = memory.purge_old_history(retention_days=0)
    assert res["messages"] >= 1
    assert res["task_runs"] >= 1

