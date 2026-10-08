"""Tests unitaires pour la persistance des sessions SQLite."""

from pathlib import Path
from agent.storage import SessionStorage


def test_session_storage_messages_flow(tmp_path: Path) -> None:
    """Vérifie l'enregistrement et la restitution ordonnée des messages."""
    db_file = tmp_path / "test_ekko.db"
    storage = SessionStorage(db_file)

    storage.record_message("session_1", "user", "Message 1")
    storage.record_message("session_1", "assistant", "Réponse 1")
    storage.record_message("session_2", "user", "Message autre session")

    history = storage.get_recent_messages("session_1", limit=10)
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Message 1"}
    assert history[1] == {"role": "assistant", "content": "Réponse 1"}


def test_session_storage_clear_session_messages(tmp_path: Path) -> None:
    """Vérifie la suppression ciblée des messages d'une session."""
    db_file = tmp_path / "test_ekko.db"
    storage = SessionStorage(db_file)

    storage.record_message("sess_a", "user", "Hello A")
    storage.record_message("sess_b", "user", "Hello B")

    deleted = storage.clear_session_messages("sess_a")
    assert deleted == 1
    assert len(storage.get_recent_messages("sess_a")) == 0
    assert len(storage.get_recent_messages("sess_b")) == 1


def test_session_storage_purge_old_history(tmp_path: Path) -> None:
    """Vérifie la purge globale des messages selon le TTL."""
    db_file = tmp_path / "test_ekko.db"
    storage = SessionStorage(db_file)

    storage.record_message("sess_old", "user", "Old message")

    # Purge avec 0 jours (tout est antérieur ou égal à l'instant présent)
    res = storage.purge_old_history(retention_days=0)
    assert res["messages"] >= 1

