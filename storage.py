"""Gestion de la persistance locale et de l'idempotence pour Ekko.

Assure le stockage de l'historique anti-doublon (~/.history.json),
la purge temporelle et la génération des briefings Markdown (~/watch/YYYY-MM-DD.md).
"""

import json
from datetime import date, datetime, timedelta
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
    normalized = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        clean_path,
        parsed.params,
        clean_query,
        "",  # On supprime le fragment d'ancre
    ))
    return normalized



def load_history(path: Path) -> dict[str, str]:
    """Charge l'historique des URLs traitées depuis un fichier JSON."""
    clean_path = path.expanduser()
    if not clean_path.is_file():
        return {}
    try:
        data = json.loads(clean_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            # Rétrocompatibilité si l'historique était une simple liste
            return {normalize_url(item): date.today().isoformat() for item in data}
        if isinstance(data, dict):
            return {normalize_url(k): str(v) for k, v in data.items()}
    except (json.JSONDecodeError, OSError):
        return {}
    return {}


def purge_old_history(history: dict[str, str], retention_days: int) -> dict[str, str]:
    """Supprime les URLs plus anciennes que le seuil de rétention configuré."""
    threshold = date.today() - timedelta(days=retention_days)
    purged: dict[str, str] = {}
    for url, date_str in history.items():
        try:
            entry_date = datetime.fromisoformat(date_str).date()
            if entry_date >= threshold:
                purged[url] = date_str
        except (ValueError, TypeError):
            purged[url] = date.today().isoformat()
    return purged


def save_history(path: Path, history: dict[str, str]) -> None:
    """Sauvegarde l'historique des URLs au format JSON sur le disque."""
    clean_path = path.expanduser()
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = clean_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(clean_path)


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
