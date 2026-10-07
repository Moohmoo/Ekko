"""Configuration centralisée du système de journalisation pour Ekko (Logging).

Redirige les logs techniques et HTTP vers un fichier local horodaté
afin de préserver un terminal épuré pour l'interface console.
"""

import logging
from pathlib import Path


def _configure_file_handler(log_file: Path) -> logging.FileHandler:
    """Initialise le gestionnaire de fichier avec formatage horodaté."""
    handler = logging.FileHandler(log_file, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    return handler


def _configure_loggers(debug: bool) -> None:
    """Ajuste le niveau des bibliothèques réseau pour alimenter le journal disque."""
    level = logging.DEBUG if debug else logging.INFO
    for name in ("httpx", "httpcore", "google_genai", "urllib3"):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.handlers.clear()
        logger.propagate = True


def setup_logging(log_dir: Path, debug: bool = False) -> None:
    """Configure la journalisation fichier et assainit le flux standard."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "ekko.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(_configure_file_handler(log_file))

    _configure_loggers(debug)
