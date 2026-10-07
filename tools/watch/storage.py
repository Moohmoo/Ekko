"""Gestion de la persistance des briefings et normalisation d'URLs pour la veille."""

from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Paramètres de tracking à nettoyer pour la déduplication
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


def normalize_url(url: str) -> str:
    """Normalise une URL en retirant les ancres, slashes finaux et paramètres UTM."""
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


def get_today_briefing_path(watch_dir: Path, custom_date: str | None = None) -> Path:
    """Calcule le chemin absolu du fichier de veille pour la date donnée."""
    date_label = custom_date if custom_date else date.today().isoformat()
    return watch_dir.expanduser() / f"{date_label}.md"


def write_briefing(briefing_path: Path, content: str) -> None:
    """Écrit le contenu Markdown du briefing journalier sur le disque."""
    briefing_path.parent.mkdir(parents=True, exist_ok=True)
    briefing_path.write_text(content.strip() + "\n", encoding="utf-8")
