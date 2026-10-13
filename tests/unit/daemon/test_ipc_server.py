"""Unit tests for JSON-RPC 2.0 UNIX socket IPC server."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from ekko.core.events import StepStarted, TokenChunk, TurnCompleted
from ekko.core.models import KnowledgeNote, RawSignal, SignalStatus
from ekko.daemon.ipc_client import IPCClient
from ekko.daemon.server import IPCServer


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
    """Ensure scan_inbox queries HybridStore and returns signals."""
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
    """Ensure query_knowledge and search_notes execute hybrid search and return results."""
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
    mock_embedder = MagicMock()
    mock_embedder.async_embed_query = AsyncMock(return_value=[0.1] * 384)

    server = IPCServer(socket_path=socket_path, db_manager=mock_db, embedder=mock_embedder)
    await server.start()

    client = IPCClient(socket_path=socket_path)
    # Test query_knowledge
    response = await client.call("query_knowledge", {"query": "AI research", "mode": "hybrid"})
    assert len(response) == 1
    assert response[0]["note"]["id"] == "n1"
    assert response[0]["score"] == 0.035
    mock_embedder.async_embed_query.assert_awaited_with("AI research")

    # Test search_notes alias/method
    response2 = await client.call("search_notes", {"query": "Deep learning", "mode": "hybrid"})
    assert len(response2) == 1
    assert response2[0]["note"]["id"] == "n1"

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


@pytest.mark.asyncio
async def test_ipc_server_ingest_file(socket_path: Path, tmp_path: Path) -> None:
    """Ensure ingest_file responds immediately with accepted status and distills asynchronously."""
    sample_file = tmp_path / "sample_note.md"
    sample_file.write_text("# Test Document\n\nThis is sample text for distillation.", encoding="utf-8")

    mock_distiller = MagicMock()
    mock_distiller.distill_file = AsyncMock(
        return_value=KnowledgeNote(
            id="note_test_doc",
            slug="2026-10-11_test-doc",
            title="Test Doc",
            summary="A short summary",
            content="Full note content",
            tags=["test"],
            sources=[str(sample_file)],
        )
    )

    server = IPCServer(socket_path=socket_path, distiller=mock_distiller)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        res = await client.call("ingest_file", {"file_path": str(sample_file)})
        assert res["status"] == "accepted"
        assert res["filename"] == "sample_note.md"
        assert "Distillation en cours" in res["message"]

    # Allow background asyncio task to execute
    await asyncio.sleep(0.05)
    mock_distiller.distill_file.assert_awaited_once_with(sample_file)

    await server.stop()


@pytest.mark.asyncio
async def test_ipc_server_distillation_serialized_by_semaphore(socket_path: Path, tmp_path: Path) -> None:
    """Ensure concurrent distillations are serialized by _distillation_semaphore (max concurrency 1)."""
    file1 = tmp_path / "doc1.md"
    file1.write_text("# Doc 1", encoding="utf-8")
    file2 = tmp_path / "doc2.md"
    file2.write_text("# Doc 2", encoding="utf-8")

    concurrent_count = 0
    max_concurrent = 0

    async def mock_distill(path: Path) -> KnowledgeNote:
        nonlocal concurrent_count, max_concurrent
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        await asyncio.sleep(0.05)
        concurrent_count -= 1
        return KnowledgeNote(
            id=f"note_{path.stem}",
            slug=f"2026-10-11_{path.stem}",
            title=path.stem,
            summary="Summary",
            content="Content",
            tags=[],
            sources=[str(path)],
        )

    mock_distiller = MagicMock()
    mock_distiller.distill_file = AsyncMock(side_effect=mock_distill)

    server = IPCServer(socket_path=socket_path, distiller=mock_distiller)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        await client.call("ingest_file", {"file_path": str(file1)})
        await client.call("ingest_file", {"file_path": str(file2)})

    # Wait for background tasks to complete
    await asyncio.sleep(0.2)
    assert max_concurrent == 1
    assert mock_distiller.distill_file.await_count == 2

    await server.stop()


@pytest.mark.asyncio
async def test_ipc_server_ingest_file_unreadable(socket_path: Path, tmp_path: Path) -> None:
    """Ensure ingest_file rejects unreadable locked files with standard RPC error."""
    locked_file = tmp_path / "locked.md"
    locked_file.write_text("# Locked Content", encoding="utf-8")
    locked_file.chmod(0o000)

    server = IPCServer(socket_path=socket_path)
    await server.start()

    try:
        async with IPCClient(socket_path=socket_path) as client:
            with pytest.raises(Exception) as exc_info:
                await client.call("ingest_file", {"file_path": str(locked_file)})
            assert "Fichier illisible sur le disque" in str(exc_info.value)
    finally:
        locked_file.chmod(0o644)
        await server.stop()


@pytest.mark.asyncio
async def test_ipc_server_malformed_json_and_invalid_request(socket_path: Path) -> None:
    """Ensure malformed JSON and invalid request structures return JSON-RPC error without crashing daemon."""
    server = IPCServer(socket_path=socket_path)
    await server.start()

    reader, writer = await asyncio.open_unix_connection(path=str(socket_path))

    # 1. Malformed JSON (-32700)
    writer.write(b"this is not json\n")
    await writer.drain()
    line = await reader.readline()
    resp1 = json.loads(line.decode("utf-8"))
    assert resp1["error"]["code"] == -32700

    # 2. JSON root that is not a dict (-32600)
    writer.write(b'["not", "a", "dict"]\n')
    await writer.drain()
    line = await reader.readline()
    resp2 = json.loads(line.decode("utf-8"))
    assert resp2["error"]["code"] == -32600

    # 3. Invalid params type: string instead of object (-32602)
    writer.write(b'{"jsonrpc": "2.0", "id": 42, "method": "ping", "params": "invalid"}\n')
    await writer.drain()
    line = await reader.readline()
    resp3 = json.loads(line.decode("utf-8"))
    assert resp3["error"]["code"] == -32602

    writer.close()
    await writer.wait_closed()
    await server.stop()


@pytest.mark.asyncio
async def test_ipc_server_supervised_tasks_cleanup_on_stop(socket_path: Path) -> None:
    """Ensure background tasks registered with _spawn_background_task are cleanly tracked and cancelled upon server.stop()."""
    server = IPCServer(socket_path=socket_path)
    await server.start()

    async def long_task() -> None:
        await asyncio.sleep(10.0)

    task = server._spawn_background_task(long_task(), name="test_long_task")
    assert task in server._background_tasks
    assert not task.done()

    await server.stop()
    assert task.done()
    assert len(server._background_tasks) == 0


@pytest.mark.asyncio
async def test_ipc_server_ingest_url(socket_path: Path) -> None:
    """Ensure ingest_url validates URL, responds immediately, and triggers background distillation."""
    mock_distiller = MagicMock()
    mock_distiller.distill_raw_content = AsyncMock(
        return_value=KnowledgeNote(
            id="note_arxiv",
            slug="2026-10-12_arxiv-test",
            title="Arxiv Paper",
            summary="A short summary",
            content="Full note content",
            tags=["arxiv"],
            sources=["https://arxiv.org/abs/2602.01234"],
        )
    )

    server = IPCServer(socket_path=socket_path, distiller=mock_distiller)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        # 1. Invalid URL (not http/https)
        with pytest.raises(Exception):
            await client.call("ingest_url", {"url": "ftp://example.com/file"})

        # 2. Valid URL
        res = await client.call("ingest_url", {"url": "https://arxiv.org/abs/2602.01234"})
        assert res["status"] == "accepted"
        assert res["url"] == "https://arxiv.org/abs/2602.01234"
        assert res["filename"] == "arxiv.org"
        assert "Distillation en cours" in res["message"]

    await server.stop()


@pytest.mark.asyncio
async def test_ipc_server_get_system_settings(socket_path: Path, tmp_path: Path) -> None:
    """Ensure get_system_settings returns user_context, sources and system info."""
    from ekko.settings import Settings

    settings = Settings(config_dir=str(tmp_path), sqlite_db_path="data/test.db")
    server = IPCServer(socket_path=socket_path, settings=settings)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        res = await client.call("get_system_settings")
        assert res["status"] == "ok"
        assert "user_context" in res
        assert "sources" in res
        assert "system" in res
        assert res["system"]["status"] == "online"
        assert res["system"]["llm_provider"] == settings.llm_provider

    await server.stop()


@pytest.mark.asyncio
async def test_ipc_server_update_user_context(socket_path: Path, tmp_path: Path) -> None:
    """Ensure update_user_context persists YAML, updates engine prompt, and handles validation errors."""
    from ekko.settings import Settings

    mock_engine = MagicMock()
    settings = Settings(config_dir=str(tmp_path))
    server = IPCServer(socket_path=socket_path, engine=mock_engine, settings=settings)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        # 1. Valid update
        payload = {
            "user_name": "Charlie",
            "preferred_language": "en",
            "preferences": ["Fast responses"],
        }
        res = await client.call("update_user_context", payload)
        assert res["status"] == "ok"
        assert res["user_context"]["user_name"] == "Charlie"
        assert res["user_context"]["preferred_language"] == "en"
        mock_engine.update_system_prompt.assert_called_once()

        # Check persisted file
        assert (tmp_path / "user_context.yaml").exists()

        # 2. Validation error (e.g. invalid type for preferences)
        with pytest.raises(Exception) as exc_info:
            await client.call("update_user_context", {"preferences": "not-a-list"})
        assert "Validation error" in str(exc_info.value)

    await server.stop()


@pytest.mark.asyncio
async def test_ipc_server_update_sources(socket_path: Path, tmp_path: Path) -> None:
    """Ensure update_sources persists YAML, notifies coordinator, and handles validation errors."""
    from ekko.settings import Settings

    mock_coordinator = MagicMock()
    settings = Settings(config_dir=str(tmp_path))
    server = IPCServer(socket_path=socket_path, coordinator=mock_coordinator, settings=settings)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        # 1. Valid update
        payload = {
            "sources": [
                {
                    "id": "new_source",
                    "type": "rss",
                    "url": "https://example.com/feed.xml",
                    "interval": "15m",
                }
            ]
        }
        res = await client.call("update_sources", payload)
        assert res["status"] == "ok"
        assert len(res["sources"]["sources"]) == 1
        assert res["sources"]["sources"][0]["id"] == "new_source"
        mock_coordinator.update_catalog.assert_called_once()

        # Check persisted file
        assert (tmp_path / "sources.yaml").exists()

        # 2. Validation error (missing required id or type)
        with pytest.raises(Exception) as exc_info:
            await client.call("update_sources", {"sources": [{"url": "https://example.com"}]})
        assert "Validation error" in str(exc_info.value)

    await server.stop()


