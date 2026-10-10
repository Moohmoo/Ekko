"""Unit tests for JSON-RPC 2.0 UNIX socket IPC server."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from ekko.core.events import StepStarted, TokenChunk, TurnCompleted
from ekko.infrastructure.database.models import KnowledgeNote, RawSignal, SignalStatus
from ekko.interfaces.ipc.client import IPCClient
from ekko.interfaces.ipc.server import IPCServer


@pytest.fixture
def socket_path(tmp_path: Path) -> Path:
    """Provide temporary UNIX domain socket path."""
    return tmp_path / "test_ekko.sock"


@pytest.mark.asyncio
async def test_ipc_server_lifecycle_cleans_socket(socket_path: Path) -> None:
    """Ensure socket file is cleaned up upon start and stop."""
    # Pre-create a stale socket file
    socket_path.touch()
    assert socket_path.exists()

    server = IPCServer(socket_path=socket_path)
    await server.start()
    assert socket_path.exists()

    await server.stop()
    assert not socket_path.exists()


@pytest.mark.asyncio
async def test_ipc_server_ping_method(socket_path: Path) -> None:
    """Ensure ping method returns status ok via JSON-RPC 2.0."""
    server = IPCServer(socket_path=socket_path)
    await server.start()

    client = IPCClient(socket_path=socket_path)
    response = await client.call("ping")

    assert response.get("status") == "ok"
    assert "timestamp" in response

    await client.close()
    await server.stop()


@pytest.mark.asyncio
async def test_ipc_server_scan_inbox(socket_path: Path) -> None:
    """Ensure scan_inbox queries DatabaseManager and returns signals."""
    mock_db = MagicMock()
    sample_signal = RawSignal(
        id="sig_test",
        source_id="src1",
        title="Signal Title",
        status=SignalStatus.PENDING,
    )
    mock_db.get_raw_signals = AsyncMock(return_value=[sample_signal])

    server = IPCServer(socket_path=socket_path, db_manager=mock_db)
    await server.start()

    client = IPCClient(socket_path=socket_path)
    response = await client.call("scan_inbox", {"status": "pending", "limit": 10})

    assert len(response) == 1
    assert response[0]["id"] == "sig_test"
    assert response[0]["title"] == "Signal Title"

    await client.close()
    await server.stop()


@pytest.mark.asyncio
async def test_ipc_server_query_knowledge(socket_path: Path) -> None:
    """Ensure query_knowledge executes hybrid search and returns results."""
    mock_db = MagicMock()
    note = KnowledgeNote(
        id="n1",
        slug="note-1",
        title="Note 1",
        summary="Summary 1",
        content="Content 1",
        tags=["ai"],
        sources=[],
    )
    mock_db.search_notes = AsyncMock(return_value=[(note, 0.035)])

    server = IPCServer(socket_path=socket_path, db_manager=mock_db)
    await server.start()

    client = IPCClient(socket_path=socket_path)
    response = await client.call("query_knowledge", {"query": "AI research", "mode": "hybrid"})

    assert len(response) == 1
    assert response[0]["note"]["id"] == "n1"
    assert response[0]["score"] == 0.035

    await client.close()
    await server.stop()


@pytest.mark.asyncio
async def test_ipc_server_submit_prompt_streaming(socket_path: Path) -> None:
    """Ensure submit_prompt streams EngineEvent chunks over socket."""
    mock_engine = MagicMock()

    async def fake_stream(prompt: str, session_id: str):
        yield StepStarted(step_index=1, max_steps=1)
        yield TokenChunk(delta="Hello ")
        yield TokenChunk(delta="world!")
        yield TurnCompleted(content="Hello world!", total_steps=1)

    mock_engine.run_stream = fake_stream

    server = IPCServer(socket_path=socket_path, engine=mock_engine)
    await server.start()

    client = IPCClient(socket_path=socket_path)
    events: list[dict] = []
    async for event in client.stream_prompt("Hi Ekko"):
        events.append(event)

    assert len(events) == 4
    assert events[0]["type"] == "step_started"
    assert events[1]["type"] == "token_chunk"
    assert events[1]["delta"] == "Hello "
    assert events[3]["type"] == "turn_completed"

    await client.close()
    await server.stop()


@pytest.mark.asyncio
async def test_ipc_server_handles_unknown_method(socket_path: Path) -> None:
    """Ensure unknown method returns standard JSON-RPC 2.0 error -32601."""
    server = IPCServer(socket_path=socket_path)
    await server.start()

    client = IPCClient(socket_path=socket_path)
    with pytest.raises(Exception, match="Method not found"):
        await client.call("unknown_method")

    await client.close()
    await server.stop()


@pytest.mark.asyncio
async def test_ipc_client_context_manager_and_helpers(socket_path: Path) -> None:
    """Ensure IPCClient supports async context manager and convenience methods."""
    server = IPCServer(socket_path=socket_path)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        ping_resp = await client.ping()
        assert ping_resp["status"] == "ok"

        inbox_resp = await client.scan_inbox(limit=5)
        assert isinstance(inbox_resp, list)

        knowledge_resp = await client.query_knowledge(query="test")
        assert isinstance(knowledge_resp, list)

    await server.stop()
