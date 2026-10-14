"""Ekko unified persistence and hybrid search package."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ekko.db.manager import DatabaseManager


def __getattr__(name: str) -> Any:
    if name == "DatabaseManager":
        from ekko.db.manager import DatabaseManager

        return DatabaseManager
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["DatabaseManager"]
