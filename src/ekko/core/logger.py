"""Observability logger managing file persistence and isolated console output."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ekko.core.settings import Settings

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3


def _create_file_handler(file_path: str) -> RotatingFileHandler:
    """Create a rotating file handler after ensuring directory exists."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        filename=str(path),
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return handler


def setup_logger(settings: Settings | None = None) -> logging.Logger:
    """Configure root ekko logger with rotating file handler without console noise."""
    cfg = settings or Settings()
    logger = logging.getLogger("ekko")
    logger.setLevel(cfg.log_level.upper())

    # Clear existing handlers to prevent duplicate lines on multiple setups
    logger.handlers.clear()
    logger.propagate = False

    if cfg.log_file:
        logger.addHandler(_create_file_handler(cfg.log_file))

    return logger


def get_logger(name: str) -> logging.Logger:
    """Obtain a child logger partitioned under the ekko namespace."""
    if name == "ekko" or name.startswith("ekko."):
        return logging.getLogger(name)
    return logging.getLogger(f"ekko.{name}")
