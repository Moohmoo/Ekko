"""Radar domain IPC contracts defining request/response structures."""

from dataclasses import dataclass
from pydantic import BaseModel
from ekko.domains.radar.entities import RawSignal


class PendingSignalItem(BaseModel):
    """Frontier contract representing an individual retained signal item for the Radar UI."""

    id: str
    title: str
    source_type: str = "unknown"
    source_url: str = ""
    summary: str = ""
    created_at: str | None = None


class PendingSignalsResponse(BaseModel):
    """Contract payload for get_pending_signals endpoint."""

    signals: list[PendingSignalItem]
    total_count: int


class SignalResolutionResult(BaseModel):
    """Contract payload returned when resolving an individual signal."""

    status: str = "ok"
    signal_id: str
    action: str
    message: str | None = None


class BulkResolutionResult(BaseModel):
    """Contract payload returned when resolving all retained signals."""

    status: str = "ok"
    action: str
    count: int


@dataclass(frozen=True)
class ResolvedSignalOutcome:
    """Internal contract separating immediate IPC response from background distillation task."""

    reply: SignalResolutionResult
    to_distill: RawSignal | None
