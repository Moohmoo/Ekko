"""Unified database manager façade composing specialized SQLite repositories and search."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Any

from ekko.db.connection import DatabaseConnection
from ekko.db.notes_repo import NotesRepository
from ekko.db.search import HybridSearchEngine, _sanitize_fts_query
from ekko.db.signals_repo import SignalsRepository
from ekko.domains.buffer.entities import KnowledgeNote
from ekko.domains.radar.entities import RawSignal, SignalStatus, SourceState
from ekko.providers.embedder import EmbedderPort

__all__ = ["DatabaseManager", "_sanitize_fts_query"]


class DatabaseManager:
    """Façade orchestrating database connection, signal repository, notes repository, and search."""

    def __init__(
        self,
        db_path: str | Path = "data/ekko.db",
        auto_init: bool = True,
        embedder: EmbedderPort | None = None,
    ) -> None:
        self.connection = DatabaseConnection(db_path=db_path)
        self.db_path = self.connection.db_path
        self.embedder = embedder
        self.signals = SignalsRepository(self.connection)
        self.notes = NotesRepository(self.connection, embedder=embedder)
        self.search = HybridSearchEngine(self.connection)
        if auto_init:
            self.init_schema()

    def _create_connection(self) -> sqlite3.Connection:
        """Create standalone connection for backwards compatibility."""
        return self.connection.create_connection()

    def _get_connection(self) -> sqlite3.Connection:
        """Alias creating connection for backwards compatibility."""
        return self.connection.create_connection()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager guaranteeing connection closure and transaction commit/rollback."""
        with self.connection.connection() as conn:
            yield conn

    def init_schema(self) -> None:
        """Initialize database schema, migrations, and note chunk backfilling."""
        self.connection.init_schema()
        with self.connection.connection() as conn:
            self.notes.backfill_chunks_if_needed(conn)

    def is_wal_mode(self) -> bool:
        """Check if SQLite is running in WAL journal mode."""
        return self.connection.is_wal_mode()

    def get_table_names(self) -> list[str]:
        """List user-defined tables in database."""
        return self.connection.get_table_names()

    # --- Source State operations ---
    async def upsert_source_state(self, state: SourceState) -> None:
        await self.signals.upsert_source_state(state)

    async def get_source_state(self, source_id: str) -> SourceState | None:
        return await self.signals.get_source_state(source_id)

    async def list_source_states(self) -> list[SourceState]:
        return await self.signals.list_source_states()

    # --- Raw Signal operations ---
    async def save_raw_signals(self, signals: list[RawSignal]) -> int:
        return await self.signals.save_raw_signals(signals)

    async def get_raw_signals(
        self,
        source_id: str | None = None,
        status: SignalStatus | str | None = None,
        limit: int = 50,
    ) -> list[RawSignal]:
        return await self.signals.get_raw_signals(source_id=source_id, status=status, limit=limit)

    async def update_signal_status(self, signal_id: str, status: SignalStatus) -> None:
        await self.signals.update_signal_status(signal_id, status)

    async def mark_signal_status(self, signal_id: str, status: str | SignalStatus) -> None:
        await self.signals.mark_signal_status(signal_id, status)

    async def get_pending_signals(self, limit: int = 5) -> list[RawSignal]:
        return await self.signals.get_pending_signals(limit=limit)

    async def get_retained_signals(self, limit: int = 5) -> list[dict[str, str | None]]:
        return await self.signals.get_retained_signals(limit=limit)

    async def get_retained_signals_count(self) -> int:
        return await self.signals.get_retained_signals_count()

    async def get_retained_signals_with_count(self, limit: int = 20) -> dict[str, object]:
        return await self.signals.get_retained_signals_with_count(limit=limit)

    async def resolve_all_retained_signals(self, action: str) -> int:
        return await self.signals.resolve_all_retained_signals(action)

    async def get_raw_signal_by_id(self, signal_id: str) -> dict[str, Any] | None:
        return await self.signals.get_raw_signal_by_id(signal_id)

    async def resolve_signal(self, signal_id: str, action: str) -> bool:
        return await self.signals.resolve_signal(signal_id, action)

    # --- Knowledge Note operations ---
    async def save_knowledge_note(
        self,
        note: KnowledgeNote,
        embedding: list[float] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> None:
        await self.notes.save_knowledge_note(note, embedding=embedding, embeddings=embeddings)

    async def delete_knowledge_note(self, note_id: str) -> bool:
        return await self.notes.delete_knowledge_note(note_id)

    async def get_knowledge_note_by_slug(self, slug: str) -> KnowledgeNote | None:
        return await self.notes.get_knowledge_note_by_slug(slug)

    async def get_note_by_slug(self, slug: str) -> KnowledgeNote | None:
        return await self.notes.get_knowledge_note_by_slug(slug)

    async def list_knowledge_notes(self, limit: int = 50) -> list[KnowledgeNote]:
        return await self.notes.list_knowledge_notes(limit=limit)

    async def get_recent_notes(self, limit: int = 5) -> list[KnowledgeNote]:
        return await self.notes.get_recent_notes(limit=limit)

    async def get_popular_tags(self, limit: int = 30) -> list[str]:
        return await self.notes.get_popular_tags(limit=limit)

    async def get_note_chunks(self, note_id: str) -> list[str]:
        return await self.notes.get_note_chunks(note_id)

    # --- Deduplication queries across domains ---
    async def has_content_hash(self, content_hash: str) -> bool:
        if await self.signals.has_content_hash(content_hash):
            return True
        return await self.notes.has_content_hash(content_hash)

    async def has_source_url(self, url: str) -> bool:
        if await self.signals.has_source_url(url):
            return True
        return await self.notes.has_source_url(url)

    # --- Search operations ---
    async def search_notes(
        self,
        query: str,
        query_embedding: list[float] | None = None,
        mode: str = "hybrid",
        limit: int = 5,
        k: int = 60,
    ) -> list[tuple[KnowledgeNote, float]]:
        return await self.search.search_notes(
            query=query,
            query_embedding=query_embedding,
            mode=mode,
            limit=limit,
            k=k,
        )
