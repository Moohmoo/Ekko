"""Tests unitaires pour la configuration de journalisation centralisée (Logging)."""

import logging
from pathlib import Path
from core.logger import Logger, setup_logging


def test_setup_logging_creates_file_and_records(tmp_path: Path) -> None:
    """Vérifie la création du fichier de log et la capture des messages."""
    setup_logging(tmp_path, debug=False)
    log_file = tmp_path / "ekko.log"
    assert log_file.is_file()

    logger = logging.getLogger("test_ekko_app")
    logger.info("Message applicatif de test")

    content = log_file.read_text(encoding="utf-8")
    assert "Message applicatif de test" in content


def test_setup_logging_configures_libraries(tmp_path: Path) -> None:
    """Vérifie que les bibliothèques réseau sont routées vers le fichier à niveau INFO."""
    setup_logging(tmp_path, debug=False)
    httpx_logger = logging.getLogger("httpx")
    assert httpx_logger.level == logging.INFO


def test_setup_logging_debug_mode(tmp_path: Path) -> None:
    """Vérifie le maintien du niveau de debug en mode verbeux."""
    setup_logging(tmp_path, debug=True)
    root = logging.getLogger()
    assert root.level == logging.DEBUG


def test_logger_class_methods(tmp_path: Path) -> None:
    """Vérifie l'écriture via les méthodes dédiées de la classe Logger."""
    setup_logging(tmp_path, debug=True)
    log = Logger("test_component")
    log.info("Message info")
    log.warning("Message warning")
    log.debug("Message debug")
    log.error("Message error", exc_info=False)

    content = (tmp_path / "ekko.log").read_text(encoding="utf-8")
    assert "Message info" in content
    assert "Message warning" in content
    assert "Message debug" in content
    assert "Message error" in content
    assert "[test_component]" in content
