"""Tests unitaires pour les fonctions de stockage et normalisation de l'outil watch."""

from datetime import date
from pathlib import Path
import sqlite3
from tools.watch.storage import (
    get_today_briefing_path,
    is_already_generated,
    load_seen_urls,
    normalize_url,
    purge_old_urls,
    save_seen_urls,
    write_briefing,
)


def test_normalize_url() -> None:
    """Vérifie le nettoyage des paramètres de tracking, trailing slash/backslash et ancres."""
    url1 = "https://example.com/article/?utm_source=hn&utm_medium=web#comments"
    url2 = "https://example.com/article"
    assert normalize_url(url1) == url2

    url_with_backslash = "https://example.com/article/\\"
    assert normalize_url(url_with_backslash) == url2


def test_briefing_write_and_check(tmp_path: Path) -> None:
    """Vérifie la création du fichier briefing et l'indicateur d'idempotence."""
    briefing_path = get_today_briefing_path(tmp_path, "2026-10-06")
    assert not is_already_generated(briefing_path)

    write_briefing(briefing_path, "# Briefing du jour")
    assert is_already_generated(briefing_path)
    assert briefing_path.read_text(encoding="utf-8").strip() == "# Briefing du jour"


def test_sqlite_seen_urls(tmp_path: Path) -> None:
    """Vérifie l'enregistrement et le chargement d'URLs dans la base SQLite."""
    db_file = tmp_path / "test.db"
    save_seen_urls(db_file, ["https://example.com/1", "https://example.com/2/"])
    urls = load_seen_urls(db_file)
    assert "https://example.com/1" in urls
    assert "https://example.com/2" in urls


def test_sqlite_purge_old_urls(tmp_path: Path) -> None:
    """Vérifie la purge temporelle des anciennes URLs en SQLite."""
    db_file = tmp_path / "test.db"
    save_seen_urls(db_file, ["https://example.com/recent"])
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "INSERT INTO seen_articles (url, date_added) VALUES (?, ?)",
            ("https://example.com/old", "2020-01-01"),
        )
    purged_count = purge_old_urls(db_file, retention_days=60)
    assert purged_count == 1
    urls = load_seen_urls(db_file)
    assert "https://example.com/recent" in urls
    assert "https://example.com/old" not in urls
