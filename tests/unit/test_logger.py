"""Unit tests for file-based logging and console isolation."""

import logging
from pathlib import Path
import pytest

from ekko.settings import Settings
from ekko.utils.logger import get_logger, setup_logger


def test_settings_has_logging_defaults() -> None:
    """Ensure Settings includes default log level and log file destination."""
    settings = Settings(_env_file=None)
    assert settings.log_level == "INFO"
    assert settings.log_file == "logs/ekko.log"


def test_setup_logger_creates_directory_and_writes_to_file(tmp_path: Path) -> None:
    """Ensure setup_logger creates log directory and writes formatted records."""
    log_file = tmp_path / "nested" / "test_ekko.log"
    settings = Settings(
        log_level="DEBUG",
        log_file=str(log_file),
        _env_file=None,
    )

    logger = setup_logger(settings=settings)
    logger.info("Application started")
    logger.debug("Debug trace step")

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "[INFO] ekko: Application started" in content
    assert "[DEBUG] ekko: Debug trace step" in content


def test_logger_does_not_pollute_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ensure INFO, DEBUG, and WARNING logs do not leak into standard console output."""
    log_file = tmp_path / "quiet.log"
    settings = Settings(
        log_level="DEBUG",
        log_file=str(log_file),
        _env_file=None,
    )

    logger = setup_logger(settings=settings)
    logger.info("Secret info log")
    logger.warning("Secret warning log")

    captured = capsys.readouterr()
    assert "Secret info log" not in captured.out
    assert "Secret info log" not in captured.err
    assert "Secret warning log" not in captured.out


def test_get_logger_returns_child_logger() -> None:
    """Ensure get_logger returns logger under root namespace."""
    logger = get_logger("engine")
    assert logger.name.startswith("ekko")
