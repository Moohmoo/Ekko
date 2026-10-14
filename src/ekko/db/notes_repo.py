"""Repository managing knowledge_notes, note_chunks, and vector embeddings in SQLite."""

import asyncio
from collections import Counter
from datetime import datetime
import json
import sqlite3

import sqlite_vec

from ekko.core.logger import get_logger
from ekko.db.connection import DatabaseConnection
from ekko.domains.buffer.entities import KnowledgeNote
from ekko.domains.ingestion.processing.chunking import chunk_markdown
from ekko.providers.embedder import EmbedderPort

logger = get_logger("db.notes_repo")


def _to_iso(dt: datetime | None) -> str | None:
    """Format datetime to ISO string safely."""
    return dt.isoformat() if dt else None


def _from_iso(val: str | None) -> datetime | None:
    """Parse ISO string back to datetime safely."""
    return datetime.fromisoformat(val) if val else None


def _row_to_knowledge_note(row: sqlite3.Row) -> KnowledgeNote:
    """Map database Row object to KnowledgeNote model."""
    return KnowledgeNote(
        id=row["id"],
        slug=row["slug"],
        title=row["title"],
        summary=row["summary"],
        content=row["content"],
        tags=json.loads(row["tags"]),
        sources=json.loads(row["sources"]),
        created_at=_from_iso(row["created_at"]) or datetime.now(),
        updated_at=_from_iso(row["updated_at"]) or datetime.now(),
    )


class NotesRepository:
    """Provides synchronous and asynchronous CRUD operations for notes, chunks, and tags."""

    def __init__(
        self,
        connection: DatabaseConnection,
        embedder: EmbedderPort | None = None,
    ) -> None:
        self.connection = connection
        self.embedder = embedder

    def backfill_chunks_if_needed(self, conn: sqlite3.Connection) -> None:
        """Idempotently backfill existing notes into note_chunks and knowledge_vectors if chunks table is empty."""
        try:
            note_count = conn.execute("SELECT count(*) FROM knowledge_notes;").fetchone()[0]
            chunk_count = conn.execute("SELECT count(*) FROM note_chunks;").fetchone()[0]
        except Exception:
            return

        if note_count > 0 and chunk_count == 0:
            logger.info("Backfilling %d existing knowledge notes into note_chunks...", note_count)
            rows = conn.execute("SELECT id, content FROM knowledge_notes;").fetchall()
            now_iso = datetime.now().isoformat()
            for row in rows:
                note_id = str(row["id"])
                content = str(row["content"])
                chunks = chunk_markdown(content)
                if not chunks:
                    continue

                vectors: list[list[float]] | None = None
                if self.embedder is not None and hasattr(self.embedder, "embed"):
                    try:
                        vectors = self.embedder.embed(chunks)
                    except Exception as exc:
                        logger.warning("Backfill embedding failed for note %s: %s", note_id, exc)

                for idx, chunk_text in enumerate(chunks):
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO note_chunks (note_id, chunk_index, content, created_at) VALUES (?, ?, ?, ?);",
                        (note_id, idx, chunk_text, now_iso),
                    )
                    chunk_rowid = cur.lastrowid
                    if vectors and idx < len(vectors):
                        serialized = sqlite_vec.serialize_float32(vectors[idx])
                        conn.execute(
                            "INSERT INTO knowledge_vectors (chunk_rowid, embedding) VALUES (?, ?);",
                            (chunk_rowid, serialized),
                        )

        # Also backfill knowledge_vectors if chunks exist but vectors table is empty
        try:
            chunk_count_now = conn.execute("SELECT count(*) FROM note_chunks;").fetchone()[0]
            vec_count = conn.execute("SELECT count(*) FROM knowledge_vectors;").fetchone()[0]
            if chunk_count_now > 0 and vec_count == 0 and self.embedder is not None and hasattr(self.embedder, "embed"):
                logger.info("Backfilling vectors for %d existing chunks in knowledge_vectors...", chunk_count_now)
                chunk_rows = conn.execute("SELECT id, content FROM note_chunks ORDER BY id ASC;").fetchall()
                if chunk_rows:
                    texts = [str(r["content"]) for r in chunk_rows]
                    vectors = self.embedder.embed(texts)
                    for r, vec in zip(chunk_rows, vectors):
                        serialized = sqlite_vec.serialize_float32(vec)
                        conn.execute(
                            "INSERT INTO knowledge_vectors (chunk_rowid, embedding) VALUES (?, ?);",
                            (r["id"], serialized),
                        )
        except Exception as exc:
            logger.warning("Vector backfill check failed: %s", exc)

    def save_knowledge_note_sync(
        self,
        note: KnowledgeNote,
        embedding: list[float] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> None:
        """Persist knowledge note, update FTS5, chunk content, and index vector embeddings."""
        insert_note_sql = """
        INSERT INTO knowledge_notes (
            id, slug, title, summary, content, tags, sources, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            slug = excluded.slug,
            title = excluded.title,
            summary = excluded.summary,
            content = excluded.content,
            tags = excluded.tags,
            sources = excluded.sources,
            updated_at = excluded.updated_at;
        """
        tags_json = json.dumps(note.tags)
        now_iso = _to_iso(note.updated_at) or datetime.now().isoformat()
        chunks = chunk_markdown(note.content)
        if not chunks:
            fallback = f"{note.title}\n{note.summary}".strip()
            chunks = [fallback] if fallback else [note.title]

        chunk_vectors: list[list[float]] | None = None
        if embeddings is not None:
            chunk_vectors = embeddings
        elif embedding is not None:
            chunk_vectors = [embedding] * len(chunks)
        elif self.embedder is not None and hasattr(self.embedder, "embed"):
            try:
                chunk_vectors = self.embedder.embed(chunks)
            except Exception as exc:
                logger.warning("Failed to generate embeddings for note %s: %s", note.id, exc)

        with self.connection.connection() as conn:
            conn.execute(
                insert_note_sql,
                (
                    note.id,
                    note.slug,
                    note.title,
                    note.summary,
                    note.content,
                    tags_json,
                    json.dumps(note.sources),
                    _to_iso(note.created_at),
                    _to_iso(note.updated_at),
                ),
            )
            # Update FTS5 virtual table
            conn.execute("DELETE FROM knowledge_fts WHERE note_id = ?;", (note.id,))
            conn.execute(
                "INSERT INTO knowledge_fts (note_id, title, summary, content, tags) VALUES (?, ?, ?, ?, ?);",
                (note.id, note.title, note.summary, note.content, tags_json),
            )
            # Idempotent cleanup of existing chunks and vectors for this note
            old_chunks = conn.execute("SELECT id FROM note_chunks WHERE note_id = ?;", (note.id,)).fetchall()
            for r in old_chunks:
                conn.execute("DELETE FROM knowledge_vectors WHERE chunk_rowid = ?;", (r["id"],))
            conn.execute("DELETE FROM note_chunks WHERE note_id = ?;", (note.id,))

            # Insert new chunks and vector embeddings
            for idx, chunk_text in enumerate(chunks):
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO note_chunks (note_id, chunk_index, content, created_at) VALUES (?, ?, ?, ?);",
                    (note.id, idx, chunk_text, now_iso),
                )
                chunk_rowid = cur.lastrowid
                if chunk_vectors and idx < len(chunk_vectors):
                    serialized = sqlite_vec.serialize_float32(chunk_vectors[idx])
                    conn.execute(
                        "INSERT INTO knowledge_vectors (chunk_rowid, embedding) VALUES (?, ?);",
                        (chunk_rowid, serialized),
                    )

    async def save_knowledge_note(
        self,
        note: KnowledgeNote,
        embedding: list[float] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> None:
        """Persist or update knowledge note and its chunked indexes asynchronously."""
        computed_embeddings = embeddings
        if embedding is None and embeddings is None and self.embedder is not None and hasattr(self.embedder, "embed_batch"):
            chunks = chunk_markdown(note.content)
            if not chunks:
                fallback = f"{note.title}\n{note.summary}".strip()
                chunks = [fallback] if fallback else [note.title]
            try:
                computed_embeddings = await self.embedder.embed_batch(chunks)
            except Exception as exc:
                logger.warning("Async batch embedding failed for note %s: %s", note.id, exc)

        await asyncio.to_thread(self.save_knowledge_note_sync, note, embedding, computed_embeddings)

    def delete_knowledge_note_sync(self, note_id: str) -> bool:
        """Delete a knowledge note, cleaning up its chunks, vectors, and FTS entries."""
        with self.connection.connection() as conn:
            exists = conn.execute("SELECT 1 FROM knowledge_notes WHERE id = ?;", (note_id,)).fetchone()
            if not exists:
                return False
            chunk_rows = conn.execute("SELECT id FROM note_chunks WHERE note_id = ?;", (note_id,)).fetchall()
            for r in chunk_rows:
                conn.execute("DELETE FROM knowledge_vectors WHERE chunk_rowid = ?;", (r["id"],))
            conn.execute("DELETE FROM note_chunks WHERE note_id = ?;", (note_id,))
            conn.execute("DELETE FROM knowledge_fts WHERE note_id = ?;", (note_id,))
            conn.execute("DELETE FROM knowledge_notes WHERE id = ?;", (note_id,))
            return True

    async def delete_knowledge_note(self, note_id: str) -> bool:
        """Delete a knowledge note and all associated indexes asynchronously."""
        return await asyncio.to_thread(self.delete_knowledge_note_sync, note_id)

    def get_note_chunks_sync(self, note_id: str) -> list[str]:
        """Fetch chunk contents for a given note_id ordered by chunk_index."""
        with self.connection.connection() as conn:
            rows = conn.execute(
                "SELECT content FROM note_chunks WHERE note_id = ? ORDER BY chunk_index ASC;",
                (note_id,),
            ).fetchall()
            return [str(r["content"]) for r in rows]

    async def get_note_chunks(self, note_id: str) -> list[str]:
        """Fetch chunk contents for a given note_id asynchronously."""
        return await asyncio.to_thread(self.get_note_chunks_sync, note_id)

    def get_knowledge_note_by_slug_sync(self, slug: str) -> KnowledgeNote | None:
        """Query knowledge note by unique slug synchronously."""
        sql = "SELECT * FROM knowledge_notes WHERE slug = ?;"
        with self.connection.connection() as conn:
            row = conn.execute(sql, (slug,)).fetchone()
            return _row_to_knowledge_note(row) if row else None

    async def get_knowledge_note_by_slug(self, slug: str) -> KnowledgeNote | None:
        """Fetch knowledge note by slug asynchronously."""
        return await asyncio.to_thread(self.get_knowledge_note_by_slug_sync, slug)

    def list_knowledge_notes_sync(self, limit: int) -> list[KnowledgeNote]:
        """List knowledge notes ordered by creation time synchronously."""
        sql = "SELECT id, slug, title, summary, content, tags, sources, created_at, updated_at FROM knowledge_notes ORDER BY created_at DESC LIMIT ?;"
        with self.connection.connection() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
            return [_row_to_knowledge_note(row) for row in rows]

    async def list_knowledge_notes(self, limit: int = 50) -> list[KnowledgeNote]:
        """List knowledge notes asynchronously."""
        return await asyncio.to_thread(self.list_knowledge_notes_sync, limit)

    async def get_recent_notes(self, limit: int = 5) -> list[KnowledgeNote]:
        """Retrieve most recent knowledge notes ordered by creation time DESC."""
        return await self.list_knowledge_notes(limit=limit)

    def get_popular_tags_sync(self, limit: int = 30) -> list[str]:
        """Fetch most frequently used tags across all knowledge notes synchronously."""
        sql = "SELECT tags FROM knowledge_notes;"
        tag_counts: Counter[str] = Counter()
        with self.connection.connection() as conn:
            rows = conn.execute(sql).fetchall()
            for row in rows:
                tags_raw = row["tags"] if isinstance(row, sqlite3.Row) else row[0]
                if not tags_raw:
                    continue
                try:
                    parsed = json.loads(tags_raw)
                    if isinstance(parsed, list):
                        for tag in parsed:
                            if isinstance(tag, str) and tag.strip():
                                tag_counts[tag.strip()] += 1
                except (json.JSONDecodeError, TypeError):
                    continue
        return [tag for tag, _ in tag_counts.most_common(limit)]

    async def get_popular_tags(self, limit: int = 30) -> list[str]:
        """Fetch most frequently used tags across all knowledge notes asynchronously."""
        return await asyncio.to_thread(self.get_popular_tags_sync, limit)

    def has_content_hash_sync(self, content_hash: str) -> bool:
        """Check if knowledge_notes id or sources contains this hash."""
        with self.connection.connection() as conn:
            note_exists = conn.execute(
                "SELECT 1 FROM knowledge_notes WHERE id LIKE ? OR sources LIKE ? LIMIT 1;",
                (f"%{content_hash}%", f"%{content_hash}%"),
            ).fetchone()
            return bool(note_exists)

    async def has_content_hash(self, content_hash: str) -> bool:
        """Check if document hash exists in knowledge notes asynchronously."""
        return await asyncio.to_thread(self.has_content_hash_sync, content_hash)

    def has_source_url_sync(self, url: str) -> bool:
        """Check if an external URL is already present in knowledge_notes sources."""
        with self.connection.connection() as conn:
            note_exists = conn.execute(
                "SELECT 1 FROM knowledge_notes WHERE sources LIKE ? LIMIT 1;",
                (f"%{url}%",),
            ).fetchone()
            return bool(note_exists)

    async def has_source_url(self, url: str) -> bool:
        """Check if source URL is already indexed in knowledge notes asynchronously."""
        return await asyncio.to_thread(self.has_source_url_sync, url)
