"""Unit tests for JSON-RPC 2.0 signal management methods in IPCServer."""

import asyncio
from pathlib import Path
import pytest

from ekko.daemon.ipc_client import IPCClient
from ekko.daemon.server import IPCServer
from ekko.memory.hybrid_store import HybridStore


@pytest.fixture
def socket_path(tmp_path: Path) -> Path:
    return tmp_path / "test_signals.sock"


@pytest.fixture
def db_store(tmp_path: Path) -> HybridStore:
    db_file = tmp_path / "test_signals.db"
    return HybridStore(db_path=db_file)


@pytest.mark.asyncio
async def test_get_pending_signals_empty(socket_path: Path, db_store: HybridStore) -> None:
    """When no retained signals exist, get_pending_signals returns empty list."""
    server = IPCServer(socket_path=socket_path, db_manager=db_store)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        signals = await client.call("get_pending_signals")
        assert signals == []

    await server.stop()


@pytest.mark.asyncio
async def test_get_pending_signals_nominal(socket_path: Path, db_store: HybridStore) -> None:
    """Ensure get_pending_signals returns retained signals with expected structure."""
    with db_store._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO raw_signals (id, source_type, source_url, title, raw_content, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "sig_test_1",
                "arxiv",
                "https://arxiv.org/abs/2602.01234",
                "WAL2 SQLite Concurrency",
                "Summary about concurrent WAL2 mode.",
                "retained",
                "2026-10-11T12:00:00",
            ),
        )

    server = IPCServer(socket_path=socket_path, db_manager=db_store)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        signals = await client.call("get_pending_signals")
        assert len(signals) == 1
        s = signals[0]
        assert s["id"] == "sig_test_1"
        assert s["title"] == "WAL2 SQLite Concurrency"
        assert s["source_type"] == "arxiv"
        assert s["source_url"] == "https://arxiv.org/abs/2602.01234"
        assert s["summary"] == "Summary about concurrent WAL2 mode."
        assert "created_at" in s

    await server.stop()


@pytest.mark.asyncio
async def test_resolve_signal_archive(socket_path: Path, db_store: HybridStore) -> None:
    """Resolving with action 'archive' transitions status to 'archived'."""
    with db_store._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO raw_signals (id, source_type, source_url, title, raw_content, status)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            ("sig_arch_1", "hackernews", "https://news.ycombinator.com", "HN Post", "Content", "retained"),
        )

    server = IPCServer(socket_path=socket_path, db_manager=db_store)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        res = await client.call("resolve_signal", {"signal_id": "sig_arch_1", "action": "archive"})
        assert res["status"] == "ok"
        assert res["signal_id"] == "sig_arch_1"
        assert res["action"] == "archive"

        # Signal should no longer be pending
        pending = await client.call("get_pending_signals")
        assert pending == []

    # Check status in SQLite
    with db_store._get_connection() as conn:
        row = conn.execute("SELECT status FROM raw_signals WHERE id = ?", ("sig_arch_1",)).fetchone()
        assert row["status"] == "archived"

    await server.stop()


@pytest.mark.asyncio
async def test_resolve_signal_discard(socket_path: Path, db_store: HybridStore) -> None:
    """Resolving with action 'discard' transitions status to 'discarded'."""
    with db_store._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO raw_signals (id, source_type, source_url, title, raw_content, status)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            ("sig_disc_1", "rss", "https://blog.com/feed", "Blog Post", "Content", "retained"),
        )

    server = IPCServer(socket_path=socket_path, db_manager=db_store)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        res = await client.call("resolve_signal", {"signal_id": "sig_disc_1", "action": "discard"})
        assert res["status"] == "ok"
        assert res["action"] == "discard"

    with db_store._get_connection() as conn:
        row = conn.execute("SELECT status FROM raw_signals WHERE id = ?", ("sig_disc_1",)).fetchone()
        assert row["status"] == "discarded"

    await server.stop()


@pytest.mark.asyncio
async def test_resolve_signal_errors(socket_path: Path, db_store: HybridStore) -> None:
    """Validate error cases: missing signal and invalid action."""
    server = IPCServer(socket_path=socket_path, db_manager=db_store)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        # Unknown signal
        with pytest.raises(Exception) as exc_info:
            await client.call("resolve_signal", {"signal_id": "unknown_id", "action": "archive"})
        assert "Signal introuvable" in str(exc_info.value)

        # Invalid action
        with pytest.raises(Exception) as exc_info2:
            await client.call("resolve_signal", {"signal_id": "any_id", "action": "invalid_action"})
        assert "Invalid action" in str(exc_info2.value)

    await server.stop()
