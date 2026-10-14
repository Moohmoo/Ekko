"""JSON-RPC 2.0 UNIX domain socket server routing requests to domain façades."""

import asyncio
from collections.abc import Coroutine
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from pydantic import ValidationError

from ekko.db.manager import DatabaseManager
from ekko.domains.buffer.index import scan_notes, search_notes
from ekko.domains.ingestion.index import (
    distill_file_background,
    distill_signal_background,
    distill_url_background,
    prepare_file_ingest,
    prepare_url_ingest,
)
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
from ekko.logger import get_logger
from ekko.settings import Settings

logger = get_logger("daemon.server")
DEFAULT_SOCKET_PATH = "/tmp/ekko.sock"


def _rpc_result(req_id: str | int | None, result: Any) -> str:
    """Format success JSON-RPC 2.0 string."""
    payload = {"jsonrpc": "2.0", "result": result, "id": req_id}
    return json.dumps(payload) + "\n"


def _rpc_error(req_id: str | int | None, code: int, message: str) -> str:
    """Format error JSON-RPC 2.0 string."""
    payload = {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": req_id}
    return json.dumps(payload) + "\n"


def _log_task_exception(task: asyncio.Task[object]) -> None:
    """Callback logging unhandled background task exceptions without crashing."""
    if not task.cancelled() and (exc := task.exception()):
        logger.error("Background task '%s' raised unhandled exception: %s", task.get_name(), exc, exc_info=True)


class IPCServer:
    """IPC UNIX Domain Socket server delegating to clean domain façades."""

    def __init__(
        self,
        socket_path: Path | str = DEFAULT_SOCKET_PATH,
        db_manager: DatabaseManager | None = None,
        distiller: Any | None = None,
        embedder: Any | None = None,
        coordinator: Any | None = None,
        settings: Settings | None = None,
        distillation_semaphore: asyncio.Semaphore | None = None,
        engine: Any | None = None,
    ) -> None:
        self.socket_path = Path(socket_path)
        self.db_manager = db_manager or DatabaseManager()
        self.distiller = distiller
        self.embedder = embedder
        self.coordinator = coordinator
        self.settings = settings or Settings()
        self._server: asyncio.Server | None = None
        self._background_tasks: set[asyncio.Task[object]] = set()
        self._active_writers: set[asyncio.StreamWriter] = set()
        self._distillation_semaphore = distillation_semaphore or asyncio.Semaphore(1)

    def _spawn_background_task(
        self,
        coro: Coroutine[object, object, object],
        name: str | None = None,
    ) -> asyncio.Task[object]:
        """Spawn and register a supervised background task with lifetime retention and error logging."""
        task = asyncio.create_task(coro, name=name)
        self._background_tasks.add(task)
        task.add_done_callback(_log_task_exception)
        task.add_done_callback(self._background_tasks.discard)
        return task

    async def broadcast_notification(self, method: str, params: dict[str, object]) -> None:
        """Broadcast a JSON-RPC 2.0 notification to all active client connections."""
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        raw = (json.dumps(payload) + "\n").encode("utf-8")
        stale: list[asyncio.StreamWriter] = []
        for writer in list(self._active_writers):
            try:
                writer.write(raw)
                await writer.drain()
            except Exception as exc:
                logger.warning("Failed to broadcast notification '%s': %s", method, exc)
                stale.append(writer)
        for w in stale:
            self._active_writers.discard(w)

    async def start(self) -> None:
        """Clean up stale socket file and bind asynchronous UNIX domain socket server."""
        if self.socket_path.exists():
            self.socket_path.unlink()
        self._server = await asyncio.start_unix_server(self._handle_client, path=str(self.socket_path))
        logger.info("IPC Server listening on UNIX socket %s", self.socket_path)

    async def stop(self) -> None:
        """Close server, disconnect writers, cancel background tasks, and clean up socket file."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        for writer in list(self._active_writers):
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        self._active_writers.clear()

        if self._background_tasks:
            for task in list(self._background_tasks):
                task.cancel()
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            self._background_tasks.clear()

        if self.socket_path.exists():
            self.socket_path.unlink()
        logger.info("IPC Server stopped and socket %s cleaned", self.socket_path)

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Process incoming client commands sequentially over a persistent connection."""
        self._active_writers.add(writer)
        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break
                await self._dispatch_line(line.decode("utf-8").strip(), writer)
        except Exception as exc:
            logger.debug("Client connection terminated: %s", exc)
        finally:
            self._active_writers.discard(writer)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _dispatch_line(self, line: str, writer: asyncio.StreamWriter) -> None:
        """Parse JSON-RPC line and route to appropriate handler."""
        if not line:
            return
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            writer.write(_rpc_error(None, -32700, "Parse error: invalid JSON").encode("utf-8"))
            await writer.drain()
            return

        if not isinstance(req, dict):
            writer.write(_rpc_error(None, -32600, "Invalid Request: root must be a JSON object").encode("utf-8"))
            await writer.drain()
            return

        req_id = req.get("id")
        method = req.get("method")
        raw_params = req.get("params")
        if raw_params is not None and not isinstance(raw_params, dict):
            writer.write(_rpc_error(req_id, -32602, "Invalid params: must be a JSON object").encode("utf-8"))
            await writer.drain()
            return
        params = raw_params or {}

        try:
            if method == "ping":
                now_iso = datetime.now(timezone.utc).isoformat()
                writer.write(_rpc_result(req_id, {"status": "ok", "timestamp": now_iso}).encode("utf-8"))
            elif method == "scan_inbox":
                res = await scan_inbox(self.db_manager, params)
                writer.write(_rpc_result(req_id, res).encode("utf-8"))
            elif method == "scan_notes":
                res = await scan_notes(self.db_manager, params)
                writer.write(_rpc_result(req_id, res).encode("utf-8"))
            elif method in ("query_knowledge", "search_notes"):
                res = await search_notes(self.db_manager, params, embedder=self.embedder)
                writer.write(_rpc_result(req_id, res).encode("utf-8"))
            elif method == "get_pending_signals":
                res = await get_pending_signals(self.db_manager, params)
                writer.write(_rpc_result(req_id, res).encode("utf-8"))
            elif method == "resolve_signal":
                res, to_distill = await resolve_signal(self.db_manager, params)
                writer.write(_rpc_result(req_id, res).encode("utf-8"))
                if to_distill:
                    self._spawn_background_task(
                        self._distill_signal_task(to_distill),
                        name=f"distill_signal_{to_distill.get('id')}",
                    )
            elif method == "resolve_all_pending_signals":
                res = await resolve_all_pending_signals(self.db_manager, params)
                writer.write(_rpc_result(req_id, res).encode("utf-8"))
            elif method == "ingest_file":
                reply, target_path = await prepare_file_ingest(self.db_manager, str(params.get("file_path") or params.get("path") or ""))
                writer.write(_rpc_result(req_id, reply).encode("utf-8"))
                if target_path:
                    self._spawn_background_task(
                        self._distill_file_task(target_path),
                        name=f"ingest_file_{target_path.name}",
                    )
            elif method == "ingest_url":
                reply, url = await prepare_url_ingest(self.db_manager, str(params.get("url") or params.get("uri") or ""))
                writer.write(_rpc_result(req_id, reply).encode("utf-8"))
                if url:
                    self._spawn_background_task(
                        self._distill_url_task(url),
                        name=f"ingest_url_{url[:30]}",
                    )
            elif method == "get_system_settings":
                res = get_system_settings(self.settings, self.socket_path)
                writer.write(_rpc_result(req_id, res).encode("utf-8"))
            elif method == "update_user_context":
                res = update_user_context(self.settings, params)
                writer.write(_rpc_result(req_id, res).encode("utf-8"))
            elif method == "update_sources":
                res = update_sources(self.settings, self.coordinator, params)
                writer.write(_rpc_result(req_id, res).encode("utf-8"))
            else:
                writer.write(_rpc_error(req_id, -32601, f"Method not found: '{method}'").encode("utf-8"))
        except FileNotFoundError as exc:
            writer.write(_rpc_error(req_id, -32001, str(exc)).encode("utf-8"))
        except PermissionError as exc:
            writer.write(_rpc_error(req_id, -32003, str(exc)).encode("utf-8"))
        except LookupError as exc:
            writer.write(_rpc_error(req_id, -32001, str(exc)).encode("utf-8"))
        except (ValueError, ValidationError) as exc:
            code = -32002 if ("Format" in str(exc) or "URL" in str(exc)) else -32602
            if isinstance(exc, ValidationError):
                err_msg = "; ".join(f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors())
                writer.write(_rpc_error(req_id, code, f"Validation error: {err_msg}").encode("utf-8"))
            else:
                writer.write(_rpc_error(req_id, code, str(exc)).encode("utf-8"))
        except Exception as exc:
            logger.error("Unhandled error dispatching method '%s': %s", method, exc, exc_info=True)
            writer.write(_rpc_error(req_id, -32000, str(exc)).encode("utf-8"))
        await writer.drain()

    async def _distill_file_task(self, target_path: Path) -> None:
        """Run background file distillation and broadcast note created."""
        try:
            if not self.distiller:
                logger.error("Distiller not available for file %s", target_path)
                return
            note = await distill_file_background(self.distiller, target_path, self._distillation_semaphore)
            await self.broadcast_notification("daemon:note_created", {
                "note_id": note.id,
                "title": note.title,
                "slug": note.slug,
                "summary": note.summary,
                "source": str(target_path),
            })
        except Exception as exc:
            logger.error("Background file distillation failed for %s: %s", target_path, exc)

    async def _distill_url_task(self, url: str) -> None:
        """Run background URL distillation and broadcast note created."""
        try:
            if not self.distiller:
                logger.error("Distiller not available for URL %s", url)
                return
            note = await distill_url_background(self.distiller, url, self._distillation_semaphore)
            await self.broadcast_notification("daemon:note_created", {
                "note_id": note.id,
                "title": note.title,
                "slug": note.slug,
                "summary": note.summary,
                "source": url,
            })
        except Exception as exc:
            logger.error("Background URL distillation failed for %s: %s", url, exc)

    async def _distill_signal_task(self, signal_data: dict[str, Any]) -> None:
        """Run background signal distillation and broadcast note created."""
        try:
            if not self.distiller:
                logger.error("Distiller not available for signal %s", signal_data.get("id"))
                return
            note = await distill_signal_background(self.distiller, signal_data, self._distillation_semaphore)
            await self.broadcast_notification("daemon:note_created", {
                "note_id": note.id,
                "title": note.title,
                "slug": note.slug,
                "summary": note.summary,
                "source": signal_data.get("url") or signal_data.get("title") or "signal",
            })
        except Exception as exc:
            logger.error("Background signal distillation failed: %s", exc)
