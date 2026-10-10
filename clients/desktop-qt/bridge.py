"""Qt bridge connecting QML UI to the Ekko Python daemon via UNIX domain socket."""

import json
from pathlib import Path
import socket
import threading
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from ekko.logger import get_logger

logger = get_logger("desktop_qt.bridge")

DEFAULT_SOCKET_PATH = Path("/tmp/ekko.sock")


def _send_jsonrpc_sync(payload: dict[str, Any], socket_path: Path = DEFAULT_SOCKET_PATH) -> dict[str, Any]:
    """Send a single JSON-RPC 2.0 request synchronously to UNIX domain socket."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    try:
        sock.connect(str(socket_path))
        data = (json.dumps(payload) + "\n").encode("utf-8")
        sock.sendall(data)
        buffer = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buffer += chunk
            if b"\n" in buffer:
                line = buffer.split(b"\n")[0]
                return json.loads(line.decode("utf-8"))
        raise RuntimeError("Connection closed without response")
    finally:
        sock.close()


class EkkoBridge(QObject):
    """QObject bridge exposing daemon methods and streaming signals to QML."""

    # Connection & status signals
    daemonStatusChanged = Signal(bool)  # is_online
    notesLoaded = Signal(list)  # list of notes dicts
    responseChunkReceived = Signal(str)  # streaming token
    promptCompleted = Signal(str)  # full response
    errorOccurred = Signal(str)  # error message

    def __init__(self, socket_path: Path = DEFAULT_SOCKET_PATH) -> None:
        super().__init__()
        self._socket_path = socket_path
        self._is_online = False

    @Slot()
    def checkDaemonStatus(self) -> None:
        """Ping the daemon in a background thread and emit daemonStatusChanged."""
        def _ping() -> None:
            try:
                res = _send_jsonrpc_sync(
                    {"jsonrpc": "2.0", "method": "ping", "id": 1},
                    self._socket_path,
                )
                online = res.get("result", {}).get("status") == "ok"
            except Exception as e:
                logger.debug("Ping error: %s", e)
                online = False
            self._is_online = online
            try:
                self.daemonStatusChanged.emit(online)
            except RuntimeError:
                pass

        threading.Thread(target=_ping, daemon=True).start()

    @Slot()
    def getNotes(self) -> None:
        """Fetch raw inbox signals from daemon and emit notesLoaded."""
        def _fetch() -> None:
            try:
                res = _send_jsonrpc_sync(
                    {"jsonrpc": "2.0", "method": "scan_inbox", "params": {"limit": 20}, "id": 2},
                    self._socket_path,
                )
                raw_items = res.get("result", [])
                notes: list[dict[str, Any]] = []
                for item in raw_items:
                    notes.append({
                        "id": str(item.get("id", "")),
                        "title": item.get("title") or "Signal brut",
                        "summary": item.get("clean_content") or "",
                        "tags": [item.get("source_id", "inbox")],
                        "source": item.get("source_id", "ekko"),
                    })
                try:
                    self.notesLoaded.emit(notes)
                except RuntimeError:
                    pass
            except Exception as e:
                logger.warning("Failed fetching daemon notes: %s", e)
                try:
                    self.errorOccurred.emit(f"Erreur notes: {e}")
                    self.notesLoaded.emit([])
                except RuntimeError:
                    pass

        threading.Thread(target=_fetch, daemon=True).start()

    @Slot(str)
    def submitPrompt(self, prompt: str) -> None:
        """Submit a prompt and stream response events via UNIX socket in background thread."""
        def _stream() -> None:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(60.0)
            full_response = ""
            try:
                sock.connect(str(self._socket_path))
                payload = {
                    "jsonrpc": "2.0",
                    "method": "submit_prompt",
                    "params": {"prompt": prompt, "session_id": "desktop_qt"},
                    "id": 3,
                }
                sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))

                buffer = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        if not line.strip():
                            continue
                        try:
                            evt = json.loads(line.decode("utf-8"))
                        except Exception:
                            continue

                        # Check for JSON-RPC error
                        if "error" in evt:
                            err_msg = evt["error"].get("message", "Erreur moteur")
                            try:
                                self.errorOccurred.emit(err_msg)
                            except RuntimeError:
                                pass
                            return

                        # EngineEvents NDJSON stream
                        evt_type = evt.get("type")
                        if evt_type == "token_chunk":
                            delta = evt.get("delta", "")
                            full_response += delta
                            try:
                                self.responseChunkReceived.emit(delta)
                            except RuntimeError:
                                pass
                        elif evt_type in ("turn_completed", "TurnCompleted"):
                            final_text = evt.get("response", full_response)
                            try:
                                self.promptCompleted.emit(final_text)
                            except RuntimeError:
                                pass
                            return
                        elif evt_type in ("engine_error", "EngineError"):
                            err_msg = evt.get("message", "Erreur moteur")
                            try:
                                self.errorOccurred.emit(err_msg)
                            except RuntimeError:
                                pass
                            return

                try:
                    self.promptCompleted.emit(full_response)
                except RuntimeError:
                    pass
            except Exception as e:
                logger.warning("IPC submit_prompt error: %s", e)
                try:
                    self.errorOccurred.emit("Daemon inaccessible. Lancez `uv run ekko daemon`.")
                except RuntimeError:
                    pass
            finally:
                sock.close()

        threading.Thread(target=_stream, daemon=True).start()

    @Slot(str)
    def ingestFilePath(self, file_path: str) -> None:
        """Ingest dropped local file or URL."""
        prompt = f"Analyse et indexe ce document déposé : {file_path}"
        self.submitPrompt(prompt)
