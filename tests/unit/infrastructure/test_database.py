"""Unit tests for the unified SQLite database infrastructure."""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from ekko.infrastructure.database.manager import DatabaseManager
from ekko.infrastructure.database.models import (
    KnowledgeNote,
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
    await db_manager.upsert_source_state(state)

    fetched = await db_manager.get_source_state("hn_tech")
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
    await db_manager.upsert_source_state(updated_state)

    fetched_again = await db_manager.get_source_state("hn_tech")
    assert fetched_again is not None
    assert fetched_again.etag == '"etag456"'
    assert fetched_again.consecutive_errors == 1


@pytest.mark.asyncio
async def test_list_source_states(db_manager: DatabaseManager) -> None:
    """Ensure listing source states returns all registered states."""
    s1 = SourceState(id="s1", source_type="rss", url_or_path="https://feed1.xml")
    s2 = SourceState(id="s2", source_type="rest_api", url_or_path="https://api2.json")
    await db_manager.upsert_source_state(s1)
    await db_manager.upsert_source_state(s2)

    states = await db_manager.list_source_states()
    assert len(states) == 2
    ids = {s.id for s in states}
    assert ids == {"s1", "s2"}


@pytest.mark.asyncio
async def test_save_and_query_raw_signals(db_manager: DatabaseManager) -> None:
    """Ensure raw signals can be saved and queried by source and status."""
    # Source state prerequisite for foreign key
    await db_manager.upsert_source_state(
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

    inserted = await db_manager.save_raw_signals([sig1, sig2])
    assert inserted == 2

    # Query all pending
    pending = await db_manager.get_raw_signals(status=SignalStatus.PENDING)
    assert len(pending) == 1
    assert pending[0].id == "sig_1"
    assert pending[0].title == "Breakthrough in LLM Reasoning"

    # Query all for source
    source_sigs = await db_manager.get_raw_signals(source_id="hn_feed")
    assert len(source_sigs) == 2

    # Deduplication check on duplicate id
    duplicate_inserted = await db_manager.save_raw_signals([sig1])
    assert duplicate_inserted == 0


@pytest.mark.asyncio
async def test_update_signal_status(db_manager: DatabaseManager) -> None:
    """Ensure signal status transition updates cleanly."""
    await db_manager.upsert_source_state(
        SourceState(id="src_test", source_type="rss", url_or_path="https://test.xml")
    )
    sig = RawSignal(
        id="sig_update",
        source_id="src_test",
        title="Interesting Article",
        status=SignalStatus.PENDING,
    )
    await db_manager.save_raw_signals([sig])

    await db_manager.update_signal_status("sig_update", SignalStatus.RETAINED)
    signals = await db_manager.get_raw_signals(status=SignalStatus.RETAINED)
    assert len(signals) == 1
    assert signals[0].id == "sig_update"


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
    await db_manager.save_knowledge_note(note)

    fetched = await db_manager.get_knowledge_note_by_slug("2026-10-10-mistral-architecture")
    assert fetched is not None
    assert fetched.title == "Mistral Architecture"
    assert fetched.tags == ["ai", "llm", "mistral"]
    assert fetched.sources == ["https://mistral.ai/news/large-4"]

    notes = await db_manager.list_knowledge_notes(limit=10)
    assert len(notes) == 1
    assert notes[0].slug == "2026-10-10-mistral-architecture"
