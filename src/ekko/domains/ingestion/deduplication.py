"""Deduplication storage service checking collision against raw signals and knowledge notes."""

from typing import Any


__all__ = ["SqliteDeduplicationStore"]


class SqliteDeduplicationStore:
    """Implements DeduplicationPort by delegating collision checks across signal and note repositories."""

    def __init__(self, signals_repo: Any, notes_repo: Any) -> None:
        self.signals_repo = signals_repo
        self.notes_repo = notes_repo

    async def has_content_hash(self, content_hash: str) -> bool:
        """Check if SHA256 content hash already exists in raw signals or knowledge notes."""
        if hasattr(self.signals_repo, "has_content_hash"):
            if await self.signals_repo.has_content_hash(content_hash):
                return True
        if hasattr(self.notes_repo, "has_content_hash"):
            if await self.notes_repo.has_content_hash(content_hash):
                return True
        return False

    async def has_source_url(self, url: str) -> bool:
        """Check if canonical source URL already exists in raw signals or knowledge notes."""
        if hasattr(self.signals_repo, "has_source_url"):
            if await self.signals_repo.has_source_url(url):
                return True
        if hasattr(self.notes_repo, "has_source_url"):
            if await self.notes_repo.has_source_url(url):
                return True
        return False
