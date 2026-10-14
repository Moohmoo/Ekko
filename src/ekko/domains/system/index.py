"""System domain façade exposing configuration and environment settings."""

from pathlib import Path
from typing import Any
from pydantic import ValidationError

from ekko.domains.system.loader import (
    load_sources_config,
    load_user_context,
    save_sources_config,
    save_user_context,
)
from ekko.domains.system.schemas import SourcesCatalogConfig, UserContextConfig
from ekko.logger import get_logger
from ekko.settings import Settings

logger = get_logger("domains.system")


def get_system_settings(settings: Settings, socket_path: Path | str) -> dict[str, Any]:
    """Return unified system settings, active sources, and user profile."""
    config_dir = settings.config_dir
    user_ctx = load_user_context(config_dir)
    sources_cfg = load_sources_config(config_dir)

    return {
        "status": "ok",
        "user_context": user_ctx.model_dump(mode="json"),
        "sources": sources_cfg.model_dump(mode="json"),
        "system": {
            "llm_provider": settings.llm_provider,
            "active_model": settings.active_model,
            "sqlite_db_path": str(settings.sqlite_db_path),
            "ipc_socket_path": str(socket_path),
            "status": "online",
        },
    }


def update_user_context(settings: Settings, params: dict[str, Any]) -> dict[str, Any]:
    """Validate, persist user context to YAML atomically."""
    new_ctx = UserContextConfig.model_validate(params)
    config_dir = settings.config_dir
    save_user_context(new_ctx, config_dir=config_dir)

    return {
        "status": "ok",
        "message": "User context successfully updated and reloaded",
        "user_context": new_ctx.model_dump(mode="json"),
    }


def update_sources(
    settings: Settings,
    coordinator: Any | None,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Validate, persist sources to YAML atomically, and notify ingestion coordinator."""
    new_catalog = SourcesCatalogConfig.model_validate(params)
    config_dir = settings.config_dir
    save_sources_config(new_catalog, config_dir=config_dir)

    if coordinator:
        coordinator.update_catalog(new_catalog)

    return {
        "status": "ok",
        "message": "Sources catalog successfully updated and reloaded",
        "sources": new_catalog.model_dump(mode="json"),
    }
