"""JSON-RPC 2.0 UNIX domain socket transport server with dynamic method dispatch."""

import asyncio
from collections.abc import Coroutine
import json
from pathlib import Path
from typing import Any
from pydantic import ValidationError

from ekko.core.logger import get_logger
from ekko.core.settings import Settings
from ekko.daemon.handlers import METHOD_HANDLERS
from ekko.db.manager import DatabaseManager

logger = get_logger("daemon.server")
DEFAULT_SOCKET_PATH = "/tmp/ekko.sock"


def _rpc_result(req_id: str | int | None, result: Any) -> str:
    """Format success JSON-RPC 2.0 string."""
    return json.dumps({"jsonrpc": "2.0", "result": result, "id": req_id}) + "\n"


def _rpc_error(req_id: str | int | None, code: int, message: str) -> str:
    """Format error JSON-RPC 2.0 string."""
    return json.dumps({"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": req_id}) + "\n"


def _serialize_result(data: Any) -> Any:
    """Recursively serialize Pydantic models and collections to JSON primitives."""
    if hasattr(data, "model_dump"):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return [_serialize_result(item) for item in data]
    return data


def _log_task_exception(task: asyncio.Task[object]) -> None:
    """Callback logging unhandled background task exceptions without crashing."""
    if not task.cancelled() and (exc := task.exception()):
        logger.error("Background task '%s' raised unhandled exception: %s", task.get_name(), exc, exc_info=True)


def translate_rpc_exception(exc: Exception, method: str | None = None) -> tuple[int, str]:
    """Translate Python exceptions into standardized JSON-RPC 2.0 error code and message."""
    if isinstance(exc, (FileNotFoundError, LookupError)):
        return -32001, str(exc)
    if isinstance(exc, PermissionError):
        return -32003, str(exc)
    if isinstance(exc, ValidationError):
        code = -32002 if ("Format" in str(exc) or "URL" in str(exc)) else -32602
        err_msg = "; ".join(f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors())
        return code, f"Validation error: {err_msg}"
    if isinstance(exc, ValueError):
        code = -32002 if ("Format" in str(exc) or "URL" in str(exc)) else -32602
        return code, str(exc)
    logger.error("Unhandled error dispatching method '%s': %s", method, exc, exc_info=True)
    return -32000, str(exc)


class IPCServer:
    """IPC UNIX Domain Socket server delegating to registered RPC method handlers."""

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
        is_mock = hasattr(self.db_manager, "_mock_return_value")
        self.signals = self.db_manager if is_mock else getattr(self.db_manager, "signals", self.db_manager)
        self.notes = self.db_manager if is_mock else getattr(self.db_manager, "notes", self.db_manager)
        self.search = self.db_manager if is_mock else getattr(self.db_manager, "search", self.db_manager)
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
        raw = (json.dumps({"jsonrpc": "2.0", "method": method, "params": params}) + "\n").encode("utf-8")
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
        """Parse JSON-RPC line, look up handler, and write serialized outcome or error."""
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

        req_id, method, raw_params = req.get("id"), req.get("method"), req.get("params")
        if raw_params is not None and not isinstance(raw_params, dict):
            writer.write(_rpc_error(req_id, -32602, "Invalid params: must be a JSON object").encode("utf-8"))
            await writer.drain()
            return
        params = raw_params or {}

        try:
            handler = METHOD_HANDLERS.get(method) if method else None
            if not handler:
                writer.write(_rpc_error(req_id, -32601, f"Method not found: '{method}'").encode("utf-8"))
            else:
                result = await handler(self, params)
                writer.write(_rpc_result(req_id, _serialize_result(result)).encode("utf-8"))
        except Exception as exc:
            code, msg = translate_rpc_exception(exc, method)
            writer.write(_rpc_error(req_id, code, msg).encode("utf-8"))
        await writer.drain()
