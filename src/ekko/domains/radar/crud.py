"""Radar domain CRUD operations on raw signals."""

from typing import Any
from ekko.domains.radar.contracts import SignalRepositoryPort
from ekko.domains.radar.entities import RawSignal, SignalStatus


async def get_inbox_signals(
    repo: SignalRepositoryPort,
    source_id: str | None = None,
    status: SignalStatus | None = None,
    limit: int = 20,
) -> list[RawSignal]:
    """Retrieve raw signals matching source and status criteria."""
    return await repo.get_raw_signals(source_id=source_id, status=status, limit=limit)


async def get_retained_signals(
    repo: SignalRepositoryPort,
    limit: int = 20,
) -> dict[str, Any]:
    """Retrieve un-distilled signals and count for proactive UI display."""
    if hasattr(repo, "get_retained_signals_with_count"):
        return await repo.get_retained_signals_with_count(limit=limit)
    signals = await repo.get_retained_signals(limit=limit)
    return {"signals": signals, "total_count": len(signals)}


async def get_signal_by_id(repo: SignalRepositoryPort, signal_id: str) -> dict[str, Any] | None:
    """Fetch raw signal dictionary by ID."""
    return await repo.get_raw_signal_by_id(signal_id)


async def resolve_signal_in_db(repo: SignalRepositoryPort, signal_id: str, action: str) -> None:
    """Update single signal status in database."""
    await repo.resolve_signal(signal_id, action)


async def resolve_all_signals_in_db(repo: SignalRepositoryPort, action: str) -> int:
    """Resolve all retained signals in bulk."""
    return await repo.resolve_all_retained_signals(action)
