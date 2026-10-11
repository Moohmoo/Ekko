"""Asynchronous UNIX domain socket server driving Ekko via JSON-RPC 2.0."""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from ekko.core.engine import EkkoEngine
from ekko.daemon.distiller import SignalDistiller
from ekko.memory.hybrid_store import HybridStore
from ekko.memory.models import RawSignal, SignalStatus
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
        distiller: SignalDistiller | None = None,
    ) -> None:
        self.socket_path = Path(socket_path)
        self.db_manager = db_manager or HybridStore()
        self.engine = engine
        self.distiller = distiller
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
        elif method == "scan_notes":
            await self._handle_scan_notes(req_id, params, writer)
        elif method == "query_knowledge":
            await self._handle_query_knowledge(req_id, params, writer)
        elif method == "ingest_file":
            await self._handle_ingest_file(req_id, params, writer)
        elif method == "submit_prompt":
            await self._handle_submit_prompt(req_id, params, writer)
        else:
            writer.write(_rpc_error(req_id, -32601, f"Method not found: '{method}'").encode("utf-8"))
            await writer.drain()

    async def _handle_ingest_file(
        self,
        req_id: Any,
        params: dict[str, Any],
        writer: asyncio.StreamWriter,
    ) -> None:
        """Validate, extract, distill and persist a local file into a knowledge note."""
        file_path_str = params.get("file_path") or params.get("path")
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

        try:
            if suffix == ".pdf":
                import pypdf
                reader = pypdf.PdfReader(str(target_path))
                extracted_text = "".join(page.extract_text() or "" for page in reader.pages)
            else:
                extracted_text = target_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error("Failed to read file %s: %s", target_path, exc)
            writer.write(_rpc_error(req_id, -32003, f"Erreur de lecture du fichier : {exc}").encode("utf-8"))
            await writer.drain()
            return

        cleaned_text = extracted_text.strip()
        if not cleaned_text:
            writer.write(_rpc_error(req_id, -32004, "Le document ne contient aucun texte extractible").encode("utf-8"))
            await writer.drain()
            return

        if not self.distiller:
            writer.write(_rpc_error(req_id, -32603, "Moteur de distillation non configuré").encode("utf-8"))
            await writer.drain()
            return

        try:
            signal = RawSignal(
                id=f"file_{target_path.stem[:32]}_{abs(hash(str(target_path))) % 1000000}",
                source_id="local_drop",
                title=target_path.stem.replace("_", " ").replace("-", " ").title(),
                url=str(target_path),
                raw_content=cleaned_text[:12000],
                clean_content=cleaned_text[:12000],
                status=SignalStatus.PROCESSED,
            )
            note = await self.distiller._distill_single_signal(signal)
            result_payload = {
                "status": "ok",
                "note": {
                    "id": note.id,
                    "title": note.title,
                    "slug": note.slug,
                    "summary": note.summary,
                    "source": str(target_path),
                },
            }
            writer.write(_rpc_result(req_id, result_payload).encode("utf-8"))
            await writer.drain()
            logger.info("File %s successfully ingested and distilled into note %s", target_path, note.slug)
        except Exception as exc:
            logger.error("Distillation failed for file %s: %s", target_path, exc)
            writer.write(_rpc_error(req_id, -32005, f"Erreur de distillation : {exc}").encode("utf-8"))
            await writer.drain()

    async def _handle_scan_notes(
        self,
        req_id: Any,
        params: dict[str, Any],
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
