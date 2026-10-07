"""Gestion de la persistance des briefings et déduplication des URLs pour l'outil de veille.

Gère la normalisation des URLs, l'écriture des fichiers Markdown journaliers
et délègue la déduplication SQLite à la mémoire centrale.
"""

from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Paramètres de tracking à nettoyer pour la déduplication
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


def normalize_url(url: str) -> str:
    """Normalise une URL en retirant les ancres, slashes/antislashs finaux et paramètres UTM."""
    cleaned_input = url.strip().rstrip("/\\")
    parsed = urlparse(cleaned_input)
    query_params = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS
    ]
    clean_query = urlencode(query_params)
    clean_path = parsed.path.rstrip("/\\")
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        clean_path,
        parsed.params,
        clean_query,
        "",
    ))


def load_seen_urls(db_path: Path) -> set[str]:
    """Charge l'ensemble des URLs déjà traitées depuis la base SQLite."""
    from agent.memory import SQLiteMemory
    return SQLiteMemory(db_path).get_seen_urls()


def save_seen_urls(db_path: Path, urls: list[str]) -> None:
    """Enregistre de nouvelles URLs dans la base SQLite."""
    from agent.memory import SQLiteMemory
    clean_urls = [normalize_url(u) for u in urls]
    SQLiteMemory(db_path).record_seen_articles(clean_urls)


def purge_old_urls(db_path: Path, retention_days: int) -> int:
    """Supprime les URLs antérieures au seuil de rétention configuré."""
    from agent.memory import SQLiteMemory
    return SQLiteMemory(db_path).purge_seen_articles(retention_days)


def get_today_briefing_path(watch_dir: Path, custom_date: str | None = None) -> Path:
    """Calcule le chemin absolu du fichier de veille pour la date donnée."""
    date_label = custom_date if custom_date else date.today().isoformat()
    return watch_dir.expanduser() / f"{date_label}.md"


def is_already_generated(briefing_path: Path) -> bool:
    """Vérifie si le briefing du jour a déjà été produit."""
    return briefing_path.is_file()


def write_briefing(briefing_path: Path, content: str) -> None:
    """Écrit le contenu Markdown du briefing journalier sur le disque."""
    briefing_path.parent.mkdir(parents=True, exist_ok=True)
    briefing_path.write_text(content.strip() + "\n", encoding="utf-8")
