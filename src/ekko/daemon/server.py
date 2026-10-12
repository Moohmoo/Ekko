"""Asynchronous UNIX domain socket server driving Ekko via JSON-RPC 2.0."""

import asyncio
from collections.abc import Coroutine
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from ekko.core.engine import EkkoEngine
from ekko.ingestion.distiller import SignalDistiller
from ekko.memory.hybrid_store import HybridStore
from ekko.core.models import RawSignal, SignalStatus
from ekko.logger import get_logger

logger = get_logger("daemon.server")

DEFAULT_SOCKET_PATH = Path("/tmp/ekko.sock")


def _rpc_error(req_id: str | int | None, code: int, message: str) -> str:
    """Format standard JSON-RPC 2.0 error line."""
    payload = {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": message},
        "id": req_id,
    }
    return json.dumps(payload) + "\n"


def _rpc_result(req_id: str | int | None, result: object) -> str:
    """Format standard JSON-RPC 2.0 success response line."""
    payload = {"jsonrpc": "2.0", "result": result, "id": req_id}
    return json.dumps(payload) + "\n"


def _log_task_exception(task: asyncio.Task[object]) -> None:
    """Done-callback that surfaces exceptions from fire-and-forget background tasks.

    asyncio silently discards unhandled task exceptions unless retrieved via
    task.exception(). Attaching this callback to every create_task() call
    ensures any failure is immediately emitted to the daemon log.
    """
    if task.cancelled():
        logger.warning("[BG_TASK] Background task was cancelled: %s", task.get_name())
        return
    exc = task.exception()
    if exc is not None:
        logger.error(
            "[BG_TASK_ERROR] Background task %s raised an unhandled exception: %s",
            task.get_name(),
            exc,
            exc_info=exc,
        )


class IPCServer:
    """UNIX socket server accepting JSON-RPC 2.0 requests and streaming events."""

    def __init__(
        self,
        socket_path: Path | str = DEFAULT_SOCKET_PATH,
        db_manager: HybridStore | None = None,
        engine: EkkoEngine | None = None,
        distiller: SignalDistiller | None = None,
    ) -> None:
        self.socket_path = Path(socket_path)
        self.db_manager = db_manager or HybridStore()
        self.engine = engine
        self.distiller = distiller
        self._server: asyncio.Server | None = None
        self._background_tasks: set[asyncio.Task[object]] = set()
        self._active_writers: set[asyncio.StreamWriter] = set()
        self._distillation_semaphore = asyncio.Semaphore(1)

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

    async def start(self) -> None:
        """Start listening on UNIX socket, cleaning up stale socket files."""
        if self.socket_path.exists():
            self.socket_path.unlink()
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self.socket_path),
        )
        logger.info("IPC UNIX socket server listening on %s", self.socket_path)

    async def stop(self) -> None:
        """Stop server, close active connections, cancel background tasks, and delete socket file."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        # Close all active client connections
        for writer in list(self._active_writers):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        self._active_writers.clear()

        # Cancel remaining background tasks
        if self._background_tasks:
            for task in list(self._background_tasks):
                task.cancel()
            await asyncio.gather(*list(self._background_tasks), return_exceptions=True)
            self._background_tasks.clear()

        if self.socket_path.exists():
            self.socket_path.unlink()
        logger.info("IPC UNIX socket server stopped.")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming client connection streaming and requests."""
        self._active_writers.add(writer)
        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break
                try:
                    req = json.loads(line.decode("utf-8"))
                except Exception:
                    writer.write(_rpc_error(None, -32700, "Parse error").encode("utf-8"))
                    await writer.drain()
                    continue

                if not isinstance(req, dict):
                    writer.write(_rpc_error(None, -32600, "Invalid Request: root must be a JSON object").encode("utf-8"))
                    await writer.drain()
                    continue

                await self._dispatch_rpc(req, writer)
        finally:
            self._active_writers.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _dispatch_rpc(self, req: dict[str, object], writer: asyncio.StreamWriter) -> None:
        """Route JSON-RPC method call to corresponding handler."""
        raw_id = req.get("id")
        req_id = raw_id if isinstance(raw_id, (str, int)) else None
        method = str(req.get("method") or "")
        raw_params = req.get("params")
        if raw_params is not None and not isinstance(raw_params, dict):
            writer.write(_rpc_error(req_id, -32602, "Invalid params: must be a JSON object").encode("utf-8"))
            await writer.drain()
            return
        params = raw_params or {}

        if method == "ping":
            now_iso = datetime.now(timezone.utc).isoformat()
            writer.write(_rpc_result(req_id, {"status": "ok", "timestamp": now_iso}).encode("utf-8"))
            await writer.drain()
        elif method == "scan_inbox":
            await self._handle_scan_inbox(req_id, params, writer)
        elif method == "scan_notes":
            await self._handle_scan_notes(req_id, params, writer)
        elif method == "query_knowledge":
            await self._handle_query_knowledge(req_id, params, writer)
        elif method == "ingest_file":
            await self._handle_ingest_file(req_id, params, writer)
        elif method == "get_pending_signals":
            await self._handle_get_pending_signals(req_id, params, writer)
        elif method == "resolve_signal":
            await self._handle_resolve_signal(req_id, params, writer)
        elif method == "submit_prompt":
            await self._handle_submit_prompt(req_id, params, writer)
        else:
            writer.write(_rpc_error(req_id, -32601, f"Method not found: '{method}'").encode("utf-8"))
            await writer.drain()

    async def _handle_ingest_file(
        self,
        req_id: str | int | None,
        params: dict[str, object],
        writer: asyncio.StreamWriter,
    ) -> None:
        """Validate, extract, distill and persist a local file into a knowledge note."""
        file_path_str = str(params.get("file_path") or params.get("path") or "")
        if not file_path_str:
            writer.write(_rpc_error(req_id, -32602, "Missing 'file_path' parameter").encode("utf-8"))
            await writer.drain()
            return

        target_path = Path(file_path_str).expanduser().resolve()
        if not target_path.exists():
            writer.write(_rpc_error(req_id, -32001, f"Fichier introuvable : {target_path}").encode("utf-8"))
            await writer.drain()
            return
        if not target_path.is_file():
            writer.write(_rpc_error(req_id, -32001, f"Le chemin n'est pas un fichier : {target_path}").encode("utf-8"))
            await writer.drain()
            return
        if not os.access(target_path, os.R_OK):
            writer.write(
                _rpc_error(
                    req_id,
                    -32003,
                    f"Fichier illisible sur le disque (permissions insuffisantes) : {target_path}",
                ).encode("utf-8")
            )
            await writer.drain()
            return

        valid_suffixes = {".pdf", ".md", ".markdown", ".txt"}
        suffix = target_path.suffix.lower()
        if suffix not in valid_suffixes:
            writer.write(
                _rpc_error(
                    req_id,
                    -32002,
                    f"Format non supporté ({suffix}). Formats acceptés : .pdf, .md, .txt",
                ).encode("utf-8")
            )
            await writer.drain()
            return

        # Return instant JSON-RPC response (< 50ms) as per Drop & Forget contract
        reply = {
            "status": "accepted",
            "filename": target_path.name,
            "message": "Document absorbé · Distillation en cours",
        }
        writer.write(_rpc_result(req_id, reply).encode("utf-8"))
        await writer.drain()

        # Supervised background task: lifetime retention + unhandled exception logging
        self._spawn_background_task(
            self._distill_and_save_async(target_path),
            name=f"ingest_file_{target_path.name}",
        )

    async def _distill_and_save_async(self, target_path: Path) -> None:
        """Background asynchronous text extraction and cognitive distillation."""
        try:
            if not self.distiller:
                logger.error("Distiller not available for background task on %s", target_path)
                return

            async with self._distillation_semaphore:
                note = await self.distiller.distill_file(target_path)
            logger.info("File %s successfully distilled in background into note %s", target_path, note.slug)
        except Exception as exc:
            logger.error("Background distillation failed for file %s: %s", target_path, exc)

    async def _handle_scan_notes(
        self,
        req_id: str | int | None,
        params: dict[str, object],
        writer: asyncio.StreamWriter,
    ) -> None:
        """Query knowledge notes and write JSON-RPC result."""
        if not self.db_manager:
            writer.write(_rpc_result(req_id, []).encode("utf-8"))
            await writer.drain()
            return
        limit = int(params.get("limit", 20))
        notes = await self.db_manager.list_knowledge_notes(limit=limit)
        serialized = [n.model_dump(mode="json") for n in notes]
        writer.write(_rpc_result(req_id, serialized).encode("utf-8"))
        await writer.drain()

    async def _handle_scan_inbox(
        self,
        req_id: str | int | None,
        params: dict[str, object],
        writer: asyncio.StreamWriter,
    ) -> None:
        """Query raw signals inbox and write JSON-RPC result."""
        if not self.db_manager:
            writer.write(_rpc_result(req_id, []).encode("utf-8"))
            await writer.drain()
            return
        status_val = params.get("status")
        status = SignalStatus(str(status_val)) if status_val else None
        source_id = str(params["source_id"]) if "source_id" in params and params["source_id"] is not None else None
        limit = int(params.get("limit", 20))
        signals = await self.db_manager.get_raw_signals(
            source_id=source_id,
            status=status,
            limit=limit,
        )
        serialized = [s.model_dump(mode="json") for s in signals]
        writer.write(_rpc_result(req_id, serialized).encode("utf-8"))
        await writer.drain()

    async def _handle_query_knowledge(
        self,
        req_id: str | int | None,
        params: dict[str, object],
        writer: asyncio.StreamWriter,
    ) -> None:
        """Execute hybrid search on knowledge notes and return JSON-RPC response."""
        if not self.db_manager:
            writer.write(_rpc_result(req_id, []).encode("utf-8"))
            await writer.drain()
            return
        query = str(params.get("query", ""))
        mode = str(params.get("mode", "hybrid"))
        limit = int(params.get("limit", 5))
        notes_with_scores = await self.db_manager.search_notes(query=query, mode=mode, limit=limit)
        results = [
            {"note": n.model_dump(mode="json"), "score": score}
            for n, score in notes_with_scores
        ]
        writer.write(_rpc_result(req_id, results).encode("utf-8"))
        await writer.drain()

    async def _handle_submit_prompt(
        self,
        req_id: str | int | None,
        params: dict[str, object],
        writer: asyncio.StreamWriter,
    ) -> None:
        """Stream EngineEvents line-by-line as NDJSON for prompt execution."""
        prompt = str(params.get("prompt", ""))
        session_id = str(params.get("session_id", "default"))
        if not self.engine:
            writer.write(_rpc_error(req_id, -32603, "Engine not available").encode("utf-8"))
            await writer.drain()
            return

        async for event in self.engine.run_stream(prompt, session_id=session_id):
            line = json.dumps(event.model_dump(mode="json")) + "\n"
            writer.write(line.encode("utf-8"))
            await writer.drain()

    async def _handle_get_pending_signals(
        self,
        req_id: str | int | None,
        params: dict[str, object],
        writer: asyncio.StreamWriter,
    ) -> None:
        """Query retained raw signals for UC-1 proactive alert display."""
        if not self.db_manager:
            writer.write(_rpc_result(req_id, []).encode("utf-8"))
            await writer.drain()
            return
        limit = int(params.get("limit", 5))
        signals = await self.db_manager.get_retained_signals(limit=limit)
        writer.write(_rpc_result(req_id, signals).encode("utf-8"))
        await writer.drain()

    async def _distill_signal_async(self, signal_data: dict[str, object]) -> None:
        """Background asynchronous cognitive distillation and note persistence for archived signal."""
        try:
            if not self.distiller:
                logger.warning(
                    "Distiller not available for background distillation of signal %s",
                    signal_data.get("id"),
                )
                return

            signal_id = str(signal_data.get("id", ""))
            title = str(signal_data.get("title", "") or "Signal")
            source_type = str(
                signal_data.get("source_type")
                or signal_data.get("source_id")
                or "proactive_signal"
            )
            source_url = str(signal_data.get("source_url") or signal_data.get("url") or "")
            raw_content = str(
                signal_data.get("raw_content")
                or signal_data.get("clean_content")
                or signal_data.get("summary")
                or title
            )

            signal = RawSignal(
                id=signal_id,
                source_id=source_type,
                title=title,
                url=source_url or None,
                raw_content=raw_content[:12000],
                clean_content=raw_content[:12000],
                status=SignalStatus.ARCHIVED,
            )
            async with self._distillation_semaphore:
                note = await self.distiller.distill_signal(signal)
            logger.info("Signal %s successfully distilled in background into note %s", signal_id, note.slug)
        except Exception as exc:
            logger.error(
                "Background distillation failed for signal %s: %s",
                signal_data.get("id"),
                exc,
                exc_info=True,
            )

    async def _handle_resolve_signal(
        self,
        req_id: str | int | None,
        params: dict[str, object],
        writer: asyncio.StreamWriter,
    ) -> None:
        """Resolve a signal by setting its status to archived or discarded."""
        signal_id = str(params.get("signal_id") or "")
        action = str(params.get("action") or "")
        if not signal_id:
            writer.write(_rpc_error(req_id, -32602, "Missing 'signal_id' parameter").encode("utf-8"))
            await writer.drain()
            return
        if action not in ("archive", "discard"):
            writer.write(
                _rpc_error(
                    req_id,
                    -32602,
                    f"Invalid action '{action}'. Must be 'archive' or 'discard'.",
                ).encode("utf-8")
            )
            await writer.drain()
            return

        if not self.db_manager:
            writer.write(_rpc_error(req_id, -32000, "Database manager not available").encode("utf-8"))
            await writer.drain()
            return

        signal_data = await self.db_manager.get_raw_signal_by_id(signal_id)
        if not signal_data:
            writer.write(_rpc_error(req_id, -32001, f"Signal introuvable : '{signal_id}'").encode("utf-8"))
            await writer.drain()
            return

        await self.db_manager.resolve_signal(signal_id, action)

        if action == "archive":
            # Supervised background task: lifetime retention + unhandled exception logging
            self._spawn_background_task(
                self._distill_signal_async(signal_data),
                name=f"distill_signal_{signal_id}",
            )
            reply = {
                "status": "ok",
                "signal_id": signal_id,
                "action": "archived",
                "message": "Signal archivé et distillation lancée",
            }
        else:
            reply = {
                "status": "ok",
                "signal_id": signal_id,
                "action": "discarded",
            }

        writer.write(_rpc_result(req_id, reply).encode("utf-8"))
        await writer.drain()
