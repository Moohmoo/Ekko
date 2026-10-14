"""Ingestion domain IPC contracts defining absorption and background distillation results."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel


@runtime_checkable
class DeduplicationPort(Protocol):
    """Port defining deduplication queries against existing content and URLs."""

    async def has_content_hash(self, content_hash: str) -> bool: ...
    async def has_source_url(self, url: str) -> bool: ...


@runtime_checkable
class ResourceManagerPort(Protocol):
    """Port defining hardware resource management and VRAM lifecycle coordination."""

    def inject_unload_vram(
        self,
        params: dict[str, Any] | None = None,
        keep_alive: str | int = "5m",
    ) -> dict[str, Any]:
        """Inject parameters directing local LLM providers to unload models after inference."""
        ...



class IngestionStatus(str, Enum):
    """Status outcome of a resource absorption attempt."""

    ACCEPTED = "accepted"
    ALREADY_EXISTS = "already_exists"
    REJECTED = "rejected"


class IngestionResponse(BaseModel):
    """Immediate response contract returned to IPC client (Drop & Forget < 50ms)."""

    status: IngestionStatus
    message: str
    filename: str | None = None
    content_hash: str | None = None
    url: str | None = None
    reason: str | None = None
    max_bytes: int | None = None


@dataclass(frozen=True)
class PreparedFileIngestion:
    """Internal contract separating immediate IPC response from background distillation file path."""

    reply: IngestionResponse
    target_path: Path | None


@dataclass(frozen=True)
class PreparedUrlIngestion:
    """Internal contract separating immediate IPC response from background distillation URL."""

    reply: IngestionResponse
    url: str | None
