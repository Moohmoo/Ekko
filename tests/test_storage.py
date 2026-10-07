"""Tests unitaires pour les fonctions de stockage et normalisation de l'outil watch."""

from pathlib import Path
from tools.watch.storage import (
    get_today_briefing_path,
    normalize_url,
    write_briefing,
)


def test_normalize_url() -> None:
    """Vérifie le nettoyage des paramètres de tracking, trailing slash/backslash et ancres."""
    url1 = "https://example.com/article/?utm_source=hn&utm_medium=web#comments"
    url2 = "https://example.com/article"
    assert normalize_url(url1) == url2

    url_with_backslash = "https://example.com/article/\\"
    assert normalize_url(url_with_backslash) == url2


def test_briefing_write_and_path(tmp_path: Path) -> None:
    """Vérifie le calcul de chemin et la création du fichier briefing."""
    briefing_path = get_today_briefing_path(tmp_path, "2026-10-06")
    assert not briefing_path.is_file()

    write_briefing(briefing_path, "# Briefing du jour")
    assert briefing_path.is_file()
    assert briefing_path.read_text(encoding="utf-8").strip() == "# Briefing du jour"
