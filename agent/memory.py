"""Alias de rétrocompatibilité pour le module storage."""

from .storage import DEFAULT_PROFILE_CONTENT, SQLiteMemory, SessionStorage, load_user_profile

__all__ = [
    "DEFAULT_PROFILE_CONTENT",
    "SQLiteMemory",
    "SessionStorage",
    "load_user_profile",
]
