"""JSON-RPC 2.0 method registry and dispatch handlers for daemon IPC server."""

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ekko.core.logger import get_logger
from ekko.domains.buffer.index import scan_notes, search_notes
from ekko.domains.ingestion.index import (
    distill_file_background,
    distill_signal_background,
    distill_url_background,
    prepare_file_ingest,
    prepare_url_ingest,
)
from ekko.domains.radar.entities import RawSignal
from ekko.domains.radar.index import (
    get_pending_signals,
    resolve_all_pending_signals,
    resolve_signal,
    scan_inbox,
)
from ekko.domains.system.index import (
    get_system_settings,
    update_sources,
    update_user_context,
)

if TYPE_CHECKING:
    from ekko.daemon.server import IPCServer

logger = get_logger("daemon.handlers")

HandlerFunc = Callable[["IPCServer", dict[str, Any]], Awaitable[Any]]


async def _distill_file_task(server: "IPCServer", target_path: Path) -> None:
    """Run background file distillation and broadcast note created."""
    try:
        if not server.distiller:
            logger.error("Distiller not available for file %s", target_path)
            return
        note = await distill_file_background(server.distiller, target_path, server._distillation_semaphore)
        await server.broadcast_notification("daemon:note_created", {
            "note_id": note.id,
            "title": note.title,
            "slug": note.slug,
            "summary": note.summary,
            "source": str(target_path),
        })
    except Exception as exc:
        logger.error("Background file distillation failed for %s: %s", target_path, exc)


async def _distill_url_task(server: "IPCServer", url: str) -> None:
    """Run background URL distillation and broadcast note created."""
    try:
        if not server.distiller:
            logger.error("Distiller not available for URL %s", url)
            return
        note = await distill_url_background(server.distiller, url, server._distillation_semaphore)
        await server.broadcast_notification("daemon:note_created", {
            "note_id": note.id,
            "title": note.title,
            "slug": note.slug,
            "summary": note.summary,
            "source": url,
        })
    except Exception as exc:
        logger.error("Background URL distillation failed for %s: %s", url, exc)


async def _distill_signal_task(server: "IPCServer", signal_data: RawSignal | dict[str, Any]) -> None:
    """Run background signal distillation and broadcast note created."""
    try:
        if not server.distiller:
            sig_id = signal_data.id if isinstance(signal_data, RawSignal) else signal_data.get("id")
            logger.error("Distiller not available for signal %s", sig_id)
            return
        note = await distill_signal_background(server.distiller, signal_data, server._distillation_semaphore)
        sig_source = (
            (signal_data.url or signal_data.title or "signal")
            if isinstance(signal_data, RawSignal)
            else (signal_data.get("url") or signal_data.get("title") or "signal")
        )
        await server.broadcast_notification("daemon:note_created", {
            "note_id": note.id,
            "title": note.title,
            "slug": note.slug,
            "summary": note.summary,
            "source": sig_source,
        })
    except Exception as exc:
        logger.error("Background signal distillation failed: %s", exc)


async def handle_ping(server: "IPCServer", params: dict[str, Any]) -> dict[str, str]:
    now_iso = datetime.now(timezone.utc).isoformat()
    return {"status": "ok", "timestamp": now_iso}


async def handle_scan_inbox(server: "IPCServer", params: dict[str, Any]) -> Any:
    return await scan_inbox(server.db_manager, params)


async def handle_scan_notes(server: "IPCServer", params: dict[str, Any]) -> Any:
    return await scan_notes(server.db_manager, params)


async def handle_search_notes(server: "IPCServer", params: dict[str, Any]) -> Any:
    return await search_notes(server.db_manager, params, embedder=server.embedder)


async def handle_get_pending_signals(server: "IPCServer", params: dict[str, Any]) -> Any:
    return await get_pending_signals(server.db_manager, params)


async def handle_resolve_signal(server: "IPCServer", params: dict[str, Any]) -> Any:
    outcome = await resolve_signal(server.db_manager, params)
    if outcome.to_distill:
        server._spawn_background_task(
            _distill_signal_task(server, outcome.to_distill),
            name=f"distill_signal_{outcome.to_distill.id}",
        )
    return outcome.reply


async def handle_resolve_all_pending_signals(server: "IPCServer", params: dict[str, Any]) -> Any:
    return await resolve_all_pending_signals(server.db_manager, params)


async def handle_ingest_file(server: "IPCServer", params: dict[str, Any]) -> Any:
    file_path = str(params.get("file_path") or params.get("path") or "")
    prepared = await prepare_file_ingest(server.db_manager, file_path)
    if prepared.target_path:
        server._spawn_background_task(
            _distill_file_task(server, prepared.target_path),
            name=f"ingest_file_{prepared.target_path.name}",
        )
    return prepared.reply


async def handle_ingest_url(server: "IPCServer", params: dict[str, Any]) -> Any:
    url = str(params.get("url") or params.get("uri") or "")
    prepared = await prepare_url_ingest(server.db_manager, url)
    if prepared.url:
        server._spawn_background_task(
            _distill_url_task(server, prepared.url),
            name=f"ingest_url_{prepared.url[:30]}",
        )
    return prepared.reply


async def handle_get_system_settings(server: "IPCServer", params: dict[str, Any]) -> Any:
    return get_system_settings(server.settings, server.socket_path)


async def handle_update_user_context(server: "IPCServer", params: dict[str, Any]) -> Any:
    return update_user_context(server.settings, params)


async def handle_update_sources(server: "IPCServer", params: dict[str, Any]) -> Any:
    return update_sources(server.settings, server.coordinator, params)


METHOD_HANDLERS: dict[str, HandlerFunc] = {
    "ping": handle_ping,
    "scan_inbox": handle_scan_inbox,
    "scan_notes": handle_scan_notes,
    "search_notes": handle_search_notes,
    "query_knowledge": handle_search_notes,
    "get_pending_signals": handle_get_pending_signals,
    "resolve_signal": handle_resolve_signal,
    "resolve_all_pending_signals": handle_resolve_all_pending_signals,
    "ingest_file": handle_ingest_file,
    "ingest_url": handle_ingest_url,
    "get_system_settings": handle_get_system_settings,
    "update_user_context": handle_update_user_context,
    "update_sources": handle_update_sources,
}
