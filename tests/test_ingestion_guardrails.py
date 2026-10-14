"""Unit tests for ingestion guardrails (max file size, SHA-256 deduplication, URL deduplication)."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from ekko.daemon.ipc_client import IPCClient
from ekko.daemon.server import IPCServer
from ekko.db.manager import DatabaseManager
from ekko.domains.ingestion.index import MAX_FILE_SIZE_BYTES


@pytest.fixture
def socket_path(tmp_path: Path) -> Path:
    """Provide temporary UNIX domain socket path."""
    return tmp_path / "test_guardrails.sock"


@pytest.fixture
def db_store(tmp_path: Path) -> DatabaseManager:
    """Provide isolated DatabaseManager instance."""
    db_file = tmp_path / "test_guardrails.db"
    return DatabaseManager(db_path=db_file)


@pytest.mark.asyncio
async def test_ingest_file_too_large_rejected(socket_path: Path, db_store: DatabaseManager, tmp_path: Path) -> None:
    """Files exceeding MAX_FILE_SIZE_BYTES (25 MB) are rejected with reason file_too_large."""
    large_file = tmp_path / "oversized.pdf"
    # Create sparse file > 25 MB without wasting actual disk blocks
    with large_file.open("wb") as f:
        f.seek(MAX_FILE_SIZE_BYTES + 1024)
        f.write(b"\0")

    server = IPCServer(socket_path=socket_path, db_manager=db_store)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        res = await client.call("ingest_file", {"file_path": str(large_file)})
        assert res["status"] == "rejected"
        assert res["reason"] == "file_too_large"
        assert res["max_bytes"] == MAX_FILE_SIZE_BYTES
        assert "trop volumineux" in res["message"]

    await server.stop()


@pytest.mark.asyncio
async def test_ingest_file_sha256_deduplication(socket_path: Path, db_store: DatabaseManager, tmp_path: Path) -> None:
    """Submitting the same document twice returns already_exists on the second call without re-distilling."""
    test_file = tmp_path / "architecture_notes.md"
    test_file.write_text("# Guide Architecture\n\nContenu unique et documenté sur les systèmes distribués.", encoding="utf-8")

    mock_distiller = MagicMock()
    mock_distiller.distill_file = AsyncMock()

    server = IPCServer(socket_path=socket_path, db_manager=db_store, distiller=mock_distiller)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        # First ingestion: accepted
        res1 = await client.call("ingest_file", {"file_path": str(test_file)})
        assert res1["status"] == "accepted"
        assert "content_hash" in res1
        content_hash = res1["content_hash"]
        assert len(content_hash) > 0

        # Simulate note persistence in db_store with the content_hash in note ID or sources
        with db_store._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_notes (id, slug, title, summary, content, tags, sources)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    f"note_{content_hash}",
                    "2026-10-12_guide-architecture",
                    "Guide Architecture",
                    "Summary",
                    "Content",
                    "[]",
                    f'["{str(test_file)}", "{content_hash}"]',
                ),
            )

        # Second ingestion: must detect existing hash and short-circuit immediately
        res2 = await client.call("ingest_file", {"file_path": str(test_file)})
        assert res2["status"] == "already_exists"
        assert res2["content_hash"] == content_hash
        assert "déjà indexé" in res2["message"]

    await server.stop()


@pytest.mark.asyncio
async def test_ingest_url_deduplication(socket_path: Path, db_store: DatabaseManager) -> None:
    """Submitting an already-indexed URL returns already_exists without re-fetching."""
    target_url = "https://arxiv.org/abs/2602.09999"

    # Pre-populate knowledge note with target URL in sources
    with db_store._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO knowledge_notes (id, slug, title, summary, content, tags, sources)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "note_arxiv_test",
                "2026-10-12_arxiv-test",
                "Arxiv Test",
                "Summary",
                "Content",
                "[]",
                f'["{target_url}"]',
            ),
        )

    server = IPCServer(socket_path=socket_path, db_manager=db_store)
    await server.start()

    async with IPCClient(socket_path=socket_path) as client:
        res = await client.call("ingest_url", {"url": target_url})
        assert res["status"] == "already_exists"
        assert res["url"] == target_url
        assert "déjà indexé" in res["message"]

    await server.stop()
