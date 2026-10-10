"""Asynchronous UNIX domain socket server driving Ekko via JSON-RPC 2.0."""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from ekko.core.engine import EkkoEngine
from ekko.memory.hybrid_store import HybridStore
from ekko.memory.models import SignalStatus
from ekko.logger import get_logger

logger = get_logger("daemon.server")

DEFAULT_SOCKET_PATH = Path("/tmp/ekko.sock")


def _rpc_error(req_id: Any, code: int, message: str) -> str:
    """Format standard JSON-RPC 2.0 error line."""
    payload = {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": message},
        "id": req_id,
    }
    return json.dumps(payload) + "\n"


def _rpc_result(req_id: Any, result: Any) -> str:
    """Format standard JSON-RPC 2.0 success response line."""
    payload = {"jsonrpc": "2.0", "result": result, "id": req_id}
    return json.dumps(payload) + "\n"


class IPCServer:
    """UNIX socket server accepting JSON-RPC 2.0 requests and streaming events."""

    def __init__(
        self,
        socket_path: Path | str = DEFAULT_SOCKET_PATH,
        db_manager: HybridStore | None = None,
        engine: EkkoEngine | None = None,
    ) -> None:
        self.socket_path = Path(socket_path)
        self.db_manager = db_manager or HybridStore()
        self.engine = engine
        self._server: asyncio.Server | None = None

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
        """Stop server and delete the UNIX socket file."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self.socket_path.exists():
            self.socket_path.unlink()
        logger.info("IPC UNIX socket server stopped.")

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming client connection streaming and requests."""
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
            await self._dispatch_rpc(req, writer)
        writer.close()
        await writer.wait_closed()

    async def _dispatch_rpc(self, req: dict[str, Any], writer: asyncio.StreamWriter) -> None:
        """Route JSON-RPC method call to corresponding handler."""
        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params") or {}

        if method == "ping":
            now_iso = datetime.now(timezone.utc).isoformat()
            writer.write(_rpc_result(req_id, {"status": "ok", "timestamp": now_iso}).encode("utf-8"))
            await writer.drain()
        elif method == "scan_inbox":
            await self._handle_scan_inbox(req_id, params, writer)
        elif method == "query_knowledge":
            await self._handle_query_knowledge(req_id, params, writer)
        elif method == "submit_prompt":
            await self._handle_submit_prompt(req_id, params, writer)
        else:
            writer.write(_rpc_error(req_id, -32601, f"Method not found: '{method}'").encode("utf-8"))
            await writer.drain()

    async def _handle_scan_inbox(
        self,
        req_id: Any,
        params: dict[str, Any],
        writer: asyncio.StreamWriter,
    ) -> None:
        """Query raw signals inbox and write JSON-RPC result."""
        if not self.db_manager:
            writer.write(_rpc_result(req_id, []).encode("utf-8"))
            await writer.drain()
            return
        status_val = params.get("status")
        status = SignalStatus(status_val) if status_val else None
        source_id = params.get("source_id")
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
        req_id: Any,
        params: dict[str, Any],
        writer: asyncio.StreamWriter,
    ) -> None:
        """Execute hybrid search on knowledge notes and return JSON-RPC response."""
        if not self.db_manager:
            writer.write(_rpc_result(req_id, []).encode("utf-8"))
            await writer.drain()
            return
        query = params.get("query", "")
        mode = params.get("mode", "hybrid")
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
        req_id: Any,
        params: dict[str, Any],
        writer: asyncio.StreamWriter,
    ) -> None:
        """Stream EngineEvents line-by-line as NDJSON for prompt execution."""
        prompt = params.get("prompt", "")
        session_id = params.get("session_id", "default")
        if not self.engine:
            writer.write(_rpc_error(req_id, -32603, "Engine not available").encode("utf-8"))
            await writer.drain()
            return

        async for event in self.engine.run_stream(prompt, session_id=session_id):
            line = json.dumps(event.model_dump(mode="json")) + "\n"
            writer.write(line.encode("utf-8"))
            await writer.drain()
