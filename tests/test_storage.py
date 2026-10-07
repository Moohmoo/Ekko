"""Tests unitaires pour les fonctions de stockage et normalisation."""

from datetime import date, timedelta
from pathlib import Path
from watch.storage import (
    get_today_briefing_path,
    is_already_generated,
    load_history,
    normalize_url,
    purge_old_history,
    save_history,
    write_briefing,
)


def test_normalize_url() -> None:
    """Vérifie le nettoyage des paramètres de tracking, trailing slash/backslash et ancres."""
    url1 = "https://example.com/article/?utm_source=hn&utm_medium=web#comments"
    url2 = "https://example.com/article"
    assert normalize_url(url1) == url2

    url_with_backslash = "https://example.com/article/\\"
    assert normalize_url(url_with_backslash) == url2


def test_history_roundtrip(tmp_path: Path) -> None:
    """Vérifie l'écriture et la relecture du fichier d'historique JSON."""
    history_file = tmp_path / ".history.json"
    initial_data = {
        "https://example.com/a": "2026-10-06",
        "https://example.com/b": "2026-10-05",
    }
    save_history(history_file, initial_data)
    loaded = load_history(history_file)
    assert loaded == initial_data


def test_history_legacy_list_support(tmp_path: Path) -> None:
    """Vérifie la compatibilité si l'historique précédent était une liste simple."""
    history_file = tmp_path / "legacy.json"
    history_file.write_text('["https://example.com/1", "https://example.com/2/"]', encoding="utf-8")
    loaded = load_history(history_file)
    assert "https://example.com/1" in loaded
    assert "https://example.com/2" in loaded


def test_purge_old_history() -> None:
    """Vérifie que les URLs plus anciennes que le seuil de rétention sont éliminées."""
    today = date.today()
    old_date = (today - timedelta(days=90)).isoformat()
    recent_date = (today - timedelta(days=10)).isoformat()

    history = {
        "https://old.com": old_date,
        "https://recent.com": recent_date,
    }
    purged = purge_old_history(history, retention_days=60)
    assert "https://recent.com" in purged
    assert "https://old.com" not in purged


def test_briefing_write_and_check(tmp_path: Path) -> None:
    """Vérifie la création du fichier briefing et l'indicateur d'idempotence."""
    briefing_path = get_today_briefing_path(tmp_path, "2026-10-06")
    assert not is_already_generated(briefing_path)

    write_briefing(briefing_path, "# Briefing du jour")
    assert is_already_generated(briefing_path)
    assert briefing_path.read_text(encoding="utf-8").strip() == "# Briefing du jour"
