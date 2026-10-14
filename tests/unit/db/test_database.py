"""Unit tests for the unified SQLite database memory store."""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from ekko.db.manager import DatabaseManager
from ekko.domains.buffer.entities import KnowledgeNote
from ekko.domains.radar.entities import (
    RawSignal,
    SignalStatus,
    SourceState,
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Provide a temporary SQLite database path."""
    return tmp_path / "test_ekko.db"


@pytest.fixture
def db_manager(db_path: Path) -> DatabaseManager:
    """Provide an initialized DatabaseManager instance."""
    manager = DatabaseManager(db_path=db_path)
    manager.init_schema()
    return manager


def test_init_schema_creates_tables_and_wal(db_manager: DatabaseManager, db_path: Path) -> None:
    """Ensure database initialization creates expected tables and sets WAL mode."""
    assert db_path.exists()
    assert db_manager.is_wal_mode() is True

    tables = db_manager.get_table_names()
    assert "source_states" in tables
    assert "raw_signals" in tables
    assert "knowledge_notes" in tables


@pytest.mark.asyncio
async def test_upsert_and_get_source_state(db_manager: DatabaseManager) -> None:
    """Ensure source state can be created, retrieved, and updated."""
    state = SourceState(
        id="hn_tech",
        source_type="rest_api",
        url_or_path="https://hn.algolia.com/api/v1/search",
        etag='"etag123"',
        last_modified="Wed, 21 Oct 2025 07:28:00 GMT",
        consecutive_errors=0,
    )
    await db_manager.signals.upsert_source_state(state)

    fetched = await db_manager.signals.get_source_state("hn_tech")
    assert fetched is not None
    assert fetched.id == "hn_tech"
    assert fetched.etag == '"etag123"'
    assert fetched.consecutive_errors == 0

    # Update state
    updated_state = SourceState(
        id="hn_tech",
        source_type="rest_api",
        url_or_path="https://hn.algolia.com/api/v1/search",
        etag='"etag456"',
        last_modified="Thu, 22 Oct 2025 07:28:00 GMT",
        consecutive_errors=1,
    )
    await db_manager.signals.upsert_source_state(updated_state)

    fetched_again = await db_manager.signals.get_source_state("hn_tech")
    assert fetched_again is not None
    assert fetched_again.etag == '"etag456"'
    assert fetched_again.consecutive_errors == 1


@pytest.mark.asyncio
async def test_list_source_states(db_manager: DatabaseManager) -> None:
    """Ensure listing source states returns all registered states."""
    s1 = SourceState(id="s1", source_type="rss", url_or_path="https://feed1.xml")
    s2 = SourceState(id="s2", source_type="rest_api", url_or_path="https://api2.json")
    await db_manager.signals.upsert_source_state(s1)
    await db_manager.signals.upsert_source_state(s2)

    states = await db_manager.signals.list_source_states()
    assert len(states) == 2
    ids = {s.id for s in states}
    assert ids == {"s1", "s2"}


@pytest.mark.asyncio
async def test_save_and_query_raw_signals(db_manager: DatabaseManager) -> None:
    """Ensure raw signals can be saved and queried by source and status."""
    # Source state prerequisite for foreign key
    await db_manager.signals.upsert_source_state(
        SourceState(id="hn_feed", source_type="rss", url_or_path="https://hn.xml")
    )

    sig1 = RawSignal(
        id="sig_1",
        source_id="hn_feed",
        external_id="ext_1",
        url="https://example.com/1",
        title="Breakthrough in LLM Reasoning",
        raw_content="<p>Full raw content here</p>",
        clean_content="Full raw content here",
        author="Alice",
        status=SignalStatus.PENDING,
    )
    sig2 = RawSignal(
        id="sig_2",
        source_id="hn_feed",
        external_id="ext_2",
        url="https://example.com/2",
        title="Minor bugfix",
        raw_content="<p>Bugfix</p>",
        clean_content="Bugfix",
        status=SignalStatus.DISCARDED,
    )

    inserted = await db_manager.signals.save_raw_signals([sig1, sig2])
    assert inserted == 2

    # Query all pending
    pending = await db_manager.signals.get_raw_signals(status=SignalStatus.PENDING)
    assert len(pending) == 1
    assert pending[0].id == "sig_1"
    assert pending[0].title == "Breakthrough in LLM Reasoning"

    # Query all for source
    source_sigs = await db_manager.signals.get_raw_signals(source_id="hn_feed")
    assert len(source_sigs) == 2

    # Deduplication check on duplicate id
    duplicate_inserted = await db_manager.signals.save_raw_signals([sig1])
    assert duplicate_inserted == 0


@pytest.mark.asyncio
async def test_update_signal_status(db_manager: DatabaseManager) -> None:
    """Ensure signal status transition updates cleanly."""
    await db_manager.signals.upsert_source_state(
        SourceState(id="src_test", source_type="rss", url_or_path="https://test.xml")
    )
    sig = RawSignal(
        id="sig_update",
        source_id="src_test",
        title="Interesting Article",
        status=SignalStatus.PENDING,
    )
    await db_manager.signals.save_raw_signals([sig])

    await db_manager.signals.update_signal_status("sig_update", SignalStatus.RETAINED)
    signals = await db_manager.signals.get_raw_signals(status=SignalStatus.RETAINED)
    assert len(signals) == 1
    assert signals[0].id == "sig_update"

    # Test mark_signal_status with processed and failed string status
    await db_manager.signals.mark_signal_status("sig_update", "processed")
    assert (await db_manager.signals.get_raw_signals(status=SignalStatus.PROCESSED))[0].id == "sig_update"

    await db_manager.signals.mark_signal_status("sig_update", "failed")
    assert (await db_manager.signals.get_raw_signals(status=SignalStatus.FAILED))[0].id == "sig_update"

    # Test get_pending_signals
    assert len(await db_manager.signals.get_pending_signals()) == 0


@pytest.mark.asyncio
async def test_save_and_get_knowledge_note(db_manager: DatabaseManager) -> None:
    """Ensure knowledge notes can be saved, fetched by slug, and listed."""
    note = KnowledgeNote(
        id="note_1",
        slug="2026-10-10-mistral-architecture",
        title="Mistral Architecture",
        summary="Overview of Mistral Large 4 capabilities.",
        content="# Mistral Architecture\nDetailed insights.",
        tags=["ai", "llm", "mistral"],
        sources=["https://mistral.ai/news/large-4"],
    )
    await db_manager.notes.save_knowledge_note(note)

    fetched = await db_manager.notes.get_knowledge_note_by_slug("2026-10-10-mistral-architecture")
    assert fetched is not None
    assert fetched.title == "Mistral Architecture"
    assert fetched.tags == ["ai", "llm", "mistral"]
    assert fetched.sources == ["https://mistral.ai/news/large-4"]

    notes = await db_manager.notes.list_knowledge_notes(limit=10)
    assert len(notes) == 1
    assert notes[0].slug == "2026-10-10-mistral-architecture"

    # Upsert with same ID updates the note attributes properly
    updated_note = KnowledgeNote(
        id="note_1",
        slug="2026-10-10-mistral-architecture-updated",
        title="Mistral Architecture v2",
        summary="Updated summary.",
        content="# Mistral Architecture Updated",
        tags=["ai", "llm", "mistral", "v2"],
        sources=["https://mistral.ai/news/large-4"],
    )
    await db_manager.notes.save_knowledge_note(updated_note)

    fetched_updated = await db_manager.notes.get_knowledge_note_by_slug("2026-10-10-mistral-architecture-updated")
    assert fetched_updated is not None
    assert fetched_updated.title == "Mistral Architecture v2"
    assert fetched_updated.tags == ["ai", "llm", "mistral", "v2"]
    assert len(await db_manager.notes.list_knowledge_notes(limit=10)) == 1


@pytest.mark.asyncio
async def test_connection_closure_guaranteed(db_manager: DatabaseManager) -> None:
    """Ensure _connection context manager cleanly closes the connection upon completion."""
    captured_conn = None
    with db_manager._connection() as conn:
        captured_conn = conn
        assert conn.total_changes is not None  # Connection is open

    # After leaving the context, connection must be closed
    with pytest.raises(Exception):
        captured_conn.execute("SELECT 1;")


@pytest.mark.asyncio
async def test_get_popular_tags(db_manager: DatabaseManager) -> None:
    """Ensure get_popular_tags returns the most frequent tags sorted by count."""
    note1 = KnowledgeNote(
        id="n1",
        slug="s1",
        title="T1",
        summary="S1",
        content="C1",
        tags=["python", "ai", "fastapi"],
    )
    note2 = KnowledgeNote(
        id="n2",
        slug="s2",
        title="T2",
        summary="S2",
        content="C2",
        tags=["python", "ai", "llm"],
    )
    note3 = KnowledgeNote(
        id="n3",
        slug="s3",
        title="T3",
        summary="S3",
        content="C3",
        tags=["python", "rust"],
    )
    await db_manager.notes.save_knowledge_note(note1)
    await db_manager.notes.save_knowledge_note(note2)
    await db_manager.notes.save_knowledge_note(note3)

    popular = await db_manager.notes.get_popular_tags(limit=2)
    assert len(popular) == 2
    assert popular[0] == "python"
    assert popular[1] == "ai"

    all_popular = await db_manager.notes.get_popular_tags(limit=10)
    assert all_popular[0] == "python"
    assert all_popular[1] == "ai"
    assert set(all_popular[2:]) == {"fastapi", "llm", "rust"}


@pytest.mark.asyncio
async def test_database_manager_unit_of_work_context(db_path: Path) -> None:
    """Ensure DatabaseManager can be used as a transactional context manager Unit of Work."""
    with DatabaseManager(db_path=db_path) as db:
        note = KnowledgeNote(
            id="uow_note",
            slug="uow-note",
            title="Unit of Work Note",
            summary="UoW pattern verification",
            content="Context manager bound to session",
            tags=["uow", "architecture"],
        )
        await db.notes.save_knowledge_note(note)

    # Verification outside context
    manager = DatabaseManager(db_path=db_path)
    fetched = await manager.notes.get_knowledge_note_by_slug("uow-note")
    assert fetched is not None
    assert fetched.title == "Unit of Work Note"
