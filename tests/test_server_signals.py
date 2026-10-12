"""Unit tests for JSON-RPC 2.0 signal management methods in IPCServer."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock
import pytest

from ekko.core.models import ModelResponse
from ekko.ingestion.distiller import SignalDistiller
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
        assert res["action"] == "archived"
        assert res["message"] == "Signal archivé et distillation lancée"

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
        assert res["action"] == "discarded"

    with db_store._get_connection() as conn:
        row = conn.execute("SELECT status FROM raw_signals WHERE id = ?", ("sig_disc_1",)).fetchone()
        assert row["status"] == "discarded"

    await server.stop()


@pytest.mark.asyncio
async def test_resolve_signal_archive_triggers_background_distillation(
    socket_path: Path, db_store: HybridStore, tmp_path: Path
) -> None:
    """Archiving a signal triggers background distillation, creating note in DB and on disk.

    The test explicitly awaits all pending asyncio tasks so there is no
    time-based fragility — the assertion runs only after the background task
    has fully completed (or raised, which would cause the test to fail with a
    clear error rather than a timeout).
    """
    notes_dir = tmp_path / "notes"
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = ModelResponse(
        content=json.dumps({
            "title": "SQLite WAL2 Insights",
            "summary": "Deep dive into WAL2 concurrency advantages.",
            "key_points": ["Point 1: concurrency", "Point 2: checkpoints"],
            "tags": ["sqlite", "wal2"],
        }),
        model_name="mock-model",
    )
    distiller = SignalDistiller(store=db_store, llm_provider=mock_llm, notes_dir=notes_dir)

    with db_store._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO raw_signals (id, source_type, source_url, title, raw_content, status)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                "sig_bg_1",
                "hackernews",
                "https://news.ycombinator.com/item?id=9999",
                "SQLite WAL2 Article",
                "Detailed content about WAL2 concurrency.",
                "retained",
            ),
        )

    server = IPCServer(socket_path=socket_path, db_manager=db_store, distiller=distiller)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        res = await client.call("resolve_signal", {"signal_id": "sig_bg_1", "action": "archive"})
        assert res["status"] == "ok"
        assert res["action"] == "archived"
        assert res["message"] == "Signal archivé et distillation lancée"

    # Drain all pending asyncio tasks so the background distillation coroutine
    # runs to completion before we assert on its side effects.
    current = asyncio.current_task()
    pending = [t for t in asyncio.all_tasks() if t is not current]
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    # Verify status in raw_signals
    with db_store._get_connection() as conn:
        row = conn.execute("SELECT status FROM raw_signals WHERE id = ?", ("sig_bg_1",)).fetchone()
        assert row["status"] == "archived"

    # Verify note in SQLite knowledge_notes
    notes = await db_store.list_knowledge_notes(limit=5)
    assert len(notes) >= 1
    distilled = next((n for n in notes if n.title == "SQLite WAL2 Insights"), None)
    assert distilled is not None, (
        "Expected note 'SQLite WAL2 Insights' in knowledge_notes — "
        "background distillation task may have failed silently."
    )
    assert distilled.summary == "Deep dive into WAL2 concurrency advantages."
    assert "sqlite" in distilled.tags

    # Verify physical markdown note file on disk
    md_files = list(notes_dir.glob("*.md"))
    assert len(md_files) == 1, f"Expected 1 Markdown note, found {md_files}"
    note_content = md_files[0].read_text(encoding="utf-8")
    assert "SQLite WAL2 Insights" in note_content
    # Validate YAML frontmatter is present
    assert "---" in note_content
    assert "tags:" in note_content

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


@pytest.mark.asyncio
async def test_get_pending_signals_sanitizes_raw_json_leak(socket_path: Path, db_store: HybridStore) -> None:
    """Ensure signals with raw JSON or Algolia _highlightResult have their summary sanitized to empty string."""
    raw_algolia_json = '{"objectID": "999", "title": "HN Leaked Story", "_highlightResult": {"title": "..."}}'
    with db_store._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO raw_signals (id, source_type, source_url, title, raw_content, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "sig_leaked_json",
                "hn_tech",
                "https://news.ycombinator.com/item?id=999",
                "HN Leaked Story",
                raw_algolia_json,
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
        assert s["id"] == "sig_leaked_json"
        # Summary must NOT be the raw JSON
        assert s["summary"] == ""
        assert not s["summary"].startswith("{")
        assert "_highlightResult" not in s["summary"]

    await server.stop()
