"""Radar domain façade exposing signal monitoring and inbox triage."""

from typing import Any
from ekko.core.models import SignalStatus
from ekko.db.manager import DatabaseManager
from ekko.domains.radar import crud


async def scan_inbox(db_manager: DatabaseManager, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Scan raw signals matching optional source_id, status and limit."""
    status_val = params.get("status")
    status = SignalStatus(str(status_val)) if status_val else None
    source_id = str(params["source_id"]) if "source_id" in params and params["source_id"] is not None else None
    limit = int(params.get("limit", 20))

    signals = await crud.get_inbox_signals(db_manager, source_id=source_id, status=status, limit=limit)
    return [s.model_dump(mode="json") for s in signals]


async def get_pending_signals(db_manager: DatabaseManager, params: dict[str, Any]) -> dict[str, Any]:
    """Query retained raw signals and total count for radar alert display."""
    limit = int(params.get("limit", 20))
    return await crud.get_retained_signals(db_manager, limit=limit)


async def resolve_signal(
    db_manager: DatabaseManager,
    params: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Resolve single signal by ID and action (archive or discard)."""
    signal_id = str(params.get("signal_id") or "")
    action = str(params.get("action") or "")

    if not signal_id:
        raise ValueError("Missing 'signal_id' parameter")
    if action not in ("archive", "discard"):
        raise ValueError(f"Invalid action '{action}'. Must be 'archive' or 'discard'.")

    signal_data = await crud.get_signal_by_id(db_manager, signal_id)
    if not signal_data:
        raise LookupError(f"Signal introuvable : '{signal_id}'")

    await crud.resolve_signal_in_db(db_manager, signal_id, action)

    if action == "archive":
        reply = {
            "status": "ok",
            "signal_id": signal_id,
            "action": "archived",
            "message": "Signal archivé et distillation lancée",
        }
        return reply, signal_data

    reply = {
        "status": "ok",
        "signal_id": signal_id,
        "action": "discarded",
    }
    return reply, None


async def resolve_all_pending_signals(db_manager: DatabaseManager, params: dict[str, Any]) -> dict[str, Any]:
    """Resolve all retained signals in bulk."""
    action = str(params.get("action") or "discard")
    if action not in ("archive", "discard"):
        raise ValueError(f"Invalid action '{action}'. Must be 'archive' or 'discard'.")

    count = await crud.resolve_all_signals_in_db(db_manager, action)
    action_name = "archived" if action == "archive" else "discarded"
    return {
        "status": "ok",
        "action": action_name,
        "count": count,
    }
