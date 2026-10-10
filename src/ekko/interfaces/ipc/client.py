"""Asynchronous client connecting to Ekko IPC UNIX socket."""

import asyncio
from collections.abc import AsyncIterator
import json
from pathlib import Path
from typing import Any

from ekko.core.errors import EkkoError
from ekko.interfaces.ipc.server import DEFAULT_SOCKET_PATH


class IPCClientError(EkkoError):
    """Exception raised upon IPC communication failure or RPC error."""


class IPCClient:
    """Client communicating with the Ekko IPC server over a UNIX domain socket."""

    def __init__(self, socket_path: Path | str = DEFAULT_SOCKET_PATH) -> None:
        self.socket_path = Path(socket_path)
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def __aenter__(self) -> "IPCClient":
        """Enter async context manager and connect."""
        await self._ensure_connection()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager and close connection."""
        await self.close()

    async def _ensure_connection(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Establish UNIX socket connection if not currently open."""
        if self._reader is None or self._writer is None:
            self._reader, self._writer = await asyncio.open_unix_connection(
                path=str(self.socket_path)
            )
        return self._reader, self._writer

    async def close(self) -> None:
        """Close client connection safely."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._reader = None
            self._writer = None

    async def ping(self) -> dict[str, Any]:
        """Send ping RPC command."""
        return await self.call("ping")

    async def scan_inbox(
        self,
        status: str | None = None,
        source_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Fetch raw signals matching criteria via JSON-RPC."""
        params = {"status": status, "source_id": source_id, "limit": limit}
        return await self.call("scan_inbox", params)

    async def query_knowledge(
        self,
        query: str,
        mode: str = "hybrid",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search local knowledge notes via JSON-RPC."""
        params = {"query": query, "mode": mode, "limit": limit}
        return await self.call("query_knowledge", params)

    async def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Issue JSON-RPC 2.0 call and return the unwrapped result."""
        reader, writer = await self._ensure_connection()
        req_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1,
        }
        writer.write((json.dumps(req_payload) + "\n").encode("utf-8"))
        await writer.drain()

        line = await reader.readline()
        if not line:
            raise IPCClientError("Connection closed unexpectedly by IPC server")

        resp = json.loads(line.decode("utf-8"))
        if "error" in resp:
            err = resp["error"]
            raise IPCClientError(f"RPC Error ({err.get('code')}): {err.get('message')}")

        return resp.get("result")

    async def stream_prompt(
        self,
        prompt: str,
        session_id: str = "default",
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream EngineEvents line-by-line emitted by submit_prompt."""
        reader, writer = await self._ensure_connection()
        req_payload = {
            "jsonrpc": "2.0",
            "method": "submit_prompt",
            "params": {"prompt": prompt, "session_id": session_id},
            "id": 1,
        }
        writer.write((json.dumps(req_payload) + "\n").encode("utf-8"))
        await writer.drain()

        while not reader.at_eof():
            line = await reader.readline()
            if not line:
                break
            event_data = json.loads(line.decode("utf-8"))
            yield event_data
            event_type = event_data.get("type") or event_data.get("event")
            if event_type in {"turn_completed", "TurnCompleted", "engine_error", "EngineError"}:
                break
