"""Ingestion domain IPC contracts defining absorption and background distillation results."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from pydantic import BaseModel


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
