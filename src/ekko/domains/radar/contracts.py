from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel
from ekko.domains.radar.entities import RawSignal, SignalStatus, SourceState


@runtime_checkable
class SignalRepositoryPort(Protocol):
    """Port defining persistence operations for Radar signals and source states."""

    async def upsert_source_state(self, state: SourceState) -> None: ...
    async def get_source_state(self, source_id: str) -> SourceState | None: ...
    async def list_source_states(self) -> list[SourceState]: ...
    async def save_raw_signals(self, signals: list[RawSignal]) -> int: ...
    async def get_raw_signals(
        self,
        source_id: str | None = None,
        status: SignalStatus | str | None = None,
        limit: int = 50,
    ) -> list[RawSignal]: ...
    async def update_signal_status(self, signal_id: str, status: SignalStatus) -> None: ...
    async def mark_signal_status(self, signal_id: str, status: str | SignalStatus) -> None: ...
    async def get_pending_signals(self, limit: int = 5) -> list[RawSignal]: ...
    async def get_retained_signals(self, limit: int = 5) -> list[dict[str, str | None]]: ...
    async def get_retained_signals_count(self) -> int: ...
    async def get_retained_signals_with_count(self, limit: int = 20) -> dict[str, object]: ...
    async def resolve_all_retained_signals(self, action: str) -> int: ...
    async def get_raw_signal_by_id(self, signal_id: str) -> dict[str, Any] | None: ...
    async def resolve_signal(self, signal_id: str, action: str) -> bool: ...
    async def has_content_hash(self, content_hash: str) -> bool: ...
    async def has_source_url(self, url: str) -> bool: ...



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
