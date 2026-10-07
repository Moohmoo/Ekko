"""Configuration centralisée du système de journalisation pour Ekko.

Structure les événements de l'agent avec horodatage, alignement des niveaux
et composants, tout en isolant les flux des bibliothèques tierces bruyantes.
"""

import logging
from pathlib import Path

AGENT_LOG_FORMAT = "%(asctime)s [%(levelname)-7s] [%(name)s] %(message)s"
AGENT_DATE_FORMAT = "%H:%M:%S"
NOISY_LIBRARIES = ("markdown_it", "httpcore", "asyncio", "urllib3")


class Logger:
    """Gestionnaire de journalisation dédié pour les composants d'Ekko."""

    def __init__(self, name: str = "ekko") -> None:
        """Initialise une instance de journalisation avec son composant identifié."""
        self._logger = logging.getLogger(name)

    def info(self, message: str, *args: object) -> None:
        """Consigne un événement informatif."""
        self._logger.info(message, *args)

    def warning(self, message: str, *args: object) -> None:
        """Consigne un avertissement opérationnel."""
        self._logger.warning(message, *args)

    def error(self, message: str, *args: object) -> None:
        """Consigne une erreur d'exécution."""
        self._logger.error(message, *args)

    def debug(self, message: str, *args: object) -> None:
        """Consigne un détail technique réservé aux diagnostics."""
        self._logger.debug(message, *args)


def _configure_file_handler(log_file: Path) -> logging.FileHandler:
    """Initialise le gestionnaire de fichier avec formatage aligné pour agents."""
    handler = logging.FileHandler(log_file, encoding="utf-8")
    formatter = logging.Formatter(AGENT_LOG_FORMAT, datefmt=AGENT_DATE_FORMAT)
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    return handler


def _mute_noisy_libraries() -> None:
    """Réduit drastiquement le bruit des parseurs et connexions internes."""
    for name in NOISY_LIBRARIES:
        noisy_logger = logging.getLogger(name)
        noisy_logger.setLevel(logging.WARNING)
        noisy_logger.propagate = False


def setup_logging(log_dir: Path, debug: bool = False) -> None:
    """Configure la journalisation fichier et filtre les flux externes."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "ekko.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(_configure_file_handler(log_file))

    httpx_level = logging.DEBUG if debug else logging.INFO
    logging.getLogger("httpx").setLevel(httpx_level)

    _mute_noisy_libraries()
