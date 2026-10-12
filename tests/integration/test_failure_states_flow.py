"""Integration tests verifying error and failure states on daemon IPC."""

import asyncio
from pathlib import Path
import pytest

from ekko.daemon.ipc_client import IPCClient
from ekko.daemon.server import IPCServer
from ekko.core.models import KnowledgeNote, RawSignal, SignalStatus
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_daemon_unreadable_file_rejection(tmp_path: Path) -> None:
    """Scenario 2: System permission failure (chmod 000)."""
    sock_path = tmp_path / "test_perms.sock"
    locked_pdf = tmp_path / "test_locked.pdf"
    locked_pdf.write_bytes(b"%PDF-1.4 test binary")
    locked_pdf.chmod(0o000)

    server = IPCServer(socket_path=sock_path)
    await server.start()

    try:
        async with IPCClient(socket_path=sock_path) as client:
            with pytest.raises(Exception) as exc_info:
                await client.call("ingest_file", {"file_path": str(locked_pdf)})
            assert "Fichier illisible sur le disque" in str(exc_info.value)
    finally:
        locked_pdf.chmod(0o644)
        await server.stop()


@pytest.mark.asyncio
async def test_daemon_unsupported_extension_rejection(tmp_path: Path) -> None:
    """Scenario 3: Format rejection (.png)."""
    sock_path = tmp_path / "test_format.sock"
    image_file = tmp_path / "image.png"
    image_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    server = IPCServer(socket_path=sock_path)
    await server.start()

    try:
        async with IPCClient(socket_path=sock_path) as client:
            with pytest.raises(Exception) as exc_info:
                await client.call("ingest_file", {"file_path": str(image_file)})
            assert "Format non supporté" in str(exc_info.value)
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_daemon_abrupt_disconnect_handling(tmp_path: Path) -> None:
    """Scenario 1: Daemon connection failure (socket does not exist or dies)."""
    non_existent_sock = tmp_path / "dead.sock"

    client = IPCClient(socket_path=non_existent_sock)
    with pytest.raises((FileNotFoundError, ConnectionRefusedError, OSError)):
        await client.call("ping")
