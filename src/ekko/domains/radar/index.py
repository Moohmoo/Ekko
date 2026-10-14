"""Radar domain façade exposing signal monitoring and inbox triage."""

from typing import Any
from ekko.domains.radar import crud
from ekko.domains.radar.contracts import (
    BulkResolutionResult,
    PendingSignalItem,
    PendingSignalsResponse,
    ResolvedSignalOutcome,
    SignalRepositoryPort,
    SignalResolutionResult,
)
from ekko.domains.radar.entities import RawSignal, SignalStatus


async def scan_inbox(repo: SignalRepositoryPort, params: dict[str, Any]) -> list[RawSignal]:
    """Scan raw signals matching optional source_id, status and limit."""
    status_val = params.get("status")
    status = SignalStatus(str(status_val)) if status_val else None
    source_id = str(params["source_id"]) if "source_id" in params and params["source_id"] is not None else None
    limit = int(params.get("limit", 20))

    return await crud.get_inbox_signals(repo, source_id=source_id, status=status, limit=limit)


async def get_pending_signals(repo: SignalRepositoryPort, params: dict[str, Any]) -> PendingSignalsResponse:
    """Query retained raw signals and total count for radar alert display."""
    limit = int(params.get("limit", 20))
    raw_data = await crud.get_retained_signals(repo, limit=limit)
    signals = [
        s if isinstance(s, PendingSignalItem) else PendingSignalItem.model_validate(s)
        for s in raw_data.get("signals", [])
    ]
    total_count = int(raw_data.get("total_count", len(signals)))
    return PendingSignalsResponse(signals=signals, total_count=total_count)


async def resolve_signal(
    repo: SignalRepositoryPort,
    params: dict[str, Any],
) -> ResolvedSignalOutcome:
    """Resolve single signal by ID and action (archive or discard)."""
    signal_id = str(params.get("signal_id") or "")
    action = str(params.get("action") or "")

    if not signal_id:
        raise ValueError("Missing 'signal_id' parameter")
    if action not in ("archive", "discard"):
        raise ValueError(f"Invalid action '{action}'. Must be 'archive' or 'discard'.")

    signal_data = await crud.get_signal_by_id(repo, signal_id)
    if not signal_data:
        raise LookupError(f"Signal introuvable : '{signal_id}'")

    await crud.resolve_signal_in_db(repo, signal_id, action)

    if action == "archive":
        reply = SignalResolutionResult(
            status="ok",
            signal_id=signal_id,
            action="archived",
            message="Signal archivé et distillation lancée",
        )
        to_distill = (
            signal_data if isinstance(signal_data, RawSignal) else RawSignal.model_validate(signal_data)
        )
        return ResolvedSignalOutcome(reply=reply, to_distill=to_distill)

    reply = SignalResolutionResult(
        status="ok",
        signal_id=signal_id,
        action="discarded",
    )
    return ResolvedSignalOutcome(reply=reply, to_distill=None)


async def resolve_all_pending_signals(repo: SignalRepositoryPort, params: dict[str, Any]) -> BulkResolutionResult:
    """Resolve all retained signals in bulk."""
    action = str(params.get("action") or "discard")
    if action not in ("archive", "discard"):
        raise ValueError(f"Invalid action '{action}'. Must be 'archive' or 'discard'.")

    count = await crud.resolve_all_signals_in_db(repo, action)
    action_name = "archived" if action == "archive" else "discarded"
    return BulkResolutionResult(
        status="ok",
        action=action_name,
        count=count,
    )
