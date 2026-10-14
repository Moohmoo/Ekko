"""Unit tests for SQLite hybrid search (FTS5 BM25 + sqlite-vec + RRF k=60)."""

from pathlib import Path
import pytest

from ekko.core.models import KnowledgeNote
from ekko.db.manager import DatabaseManager


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Provide a temporary database path."""
    return tmp_path / "test_hybrid.db"


@pytest.fixture
def db_manager(db_path: Path) -> DatabaseManager:
    """Provide an initialized DatabaseManager."""
    manager = DatabaseManager(db_path=db_path)
    manager.init_schema()
    return manager


@pytest.mark.asyncio
async def test_hybrid_search_indexes_fts_and_vectors(db_manager: DatabaseManager) -> None:
    """Ensure saving a note indexes into both FTS5 and sqlite-vec tables."""
    # Synthetic 384-dimensional unit vectors
    vec_ai = [0.1] * 384
    vec_bio = [-0.1] * 384

    note_ai = KnowledgeNote(
        id="note_ai",
        slug="2026-10-10-reasoning-models",
        title="Reasoning in Compact Language Models",
        summary="Distillation methods for small 1B to 3B reasoning models.",
        content="Deep dive into chain-of-thought distillation and self-verification.",
        tags=["ai", "llm", "reasoning"],
        sources=["https://arxiv.org/abs/2610.0001"],
    )

    note_bio = KnowledgeNote(
        id="note_bio",
        slug="2026-10-10-crispr-editing",
        title="CRISPR Gene Editing with Transformer Guides",
        summary="Predicting off-target mutations using genomic transformers.",
        content="Genomic transformers allow precise target cutting with zero off-target effects.",
        tags=["biology", "crispr", "genomics"],
        sources=["https://biorxiv.org/content/10.1101/2026.01"],
    )

    await db_manager.save_knowledge_note(note_ai, embedding=vec_ai)
    await db_manager.save_knowledge_note(note_bio, embedding=vec_bio)

    # 1. Lexical search (FTS5 BM25)
    lex_results = await db_manager.search_notes(
        query="distillation reasoning",
        mode="lexical",
        limit=5,
    )
    assert len(lex_results) >= 1
    assert lex_results[0][0].id == "note_ai"

    # 2. Semantic search (sqlite-vec)
    query_vec = [0.09] * 384
    sem_results = await db_manager.search_notes(
        query="anything",
        query_embedding=query_vec,
        mode="semantic",
        limit=5,
    )
    assert len(sem_results) >= 1
    assert sem_results[0][0].id == "note_ai"

    # 3. Hybrid search (RRF fusion k=60)
    hybrid_results = await db_manager.search_notes(
        query="CRISPR gene editing",
        query_embedding=[-0.09] * 384,
        mode="hybrid",
        limit=5,
        k=60,
    )
    assert len(hybrid_results) >= 1
    assert hybrid_results[0][0].id == "note_bio"
    # Score should be positive combined RRF score
    assert hybrid_results[0][1] > 0.0


@pytest.mark.asyncio
async def test_hybrid_search_rrf_scoring_order(db_manager: DatabaseManager) -> None:
    """Ensure RRF score ranks items matching both lexical and semantic modalities first."""
    vec1 = [0.5] * 384
    vec2 = [0.2] * 384

    note1 = KnowledgeNote(
        id="n1",
        slug="n1",
        title="Transformer Optimization",
        summary="Flash attention and kernel fusion.",
        content="Hardware-aware optimizations for deep transformers.",
        tags=["optimization"],
        sources=[],
    )
    note2 = KnowledgeNote(
        id="n2",
        slug="n2",
        title="Kernel Fusion Guide",
        summary="General GPU compiler tricks.",
        content="CUDA tricks without transformers.",
        tags=["gpu"],
        sources=[],
    )

    await db_manager.save_knowledge_note(note1, embedding=vec1)
    await db_manager.save_knowledge_note(note2, embedding=vec2)

    # Query matches n1 in both lexical and vector, but n2 only partially
    results = await db_manager.search_notes(
        query="Transformer",
        query_embedding=[0.49] * 384,
        mode="hybrid",
        limit=5,
    )
    assert len(results) >= 1
    assert results[0][0].id == "n1"


@pytest.mark.asyncio
async def test_search_notes_handles_toxic_fts5_syntax(db_manager: DatabaseManager) -> None:
    """Ensure search_notes does not crash with syntax errors on toxic FTS5 query inputs."""
    note = KnowledgeNote(
        id="toxic_test_note",
        slug="toxic-test-note",
        title="Python Security & Resilience",
        summary="A guide on defensive database querying.",
        content="Testing reserved keywords and special punctuation in sqlite fts5.",
        tags=["python", "security"],
        sources=[],
    )
    await db_manager.save_knowledge_note(note)

    # Toxic inputs with reserved words, quotes, unmatched syntax, punctuation
    toxic_queries = [
        'NOT AND OR NEAR * " \' : ( )',
        '"""',
        "AND NOT",
        "---",
        "  ",
        "",
        "Python NOT",
        "Resilience: AND OR",
    ]

    for toxic in toxic_queries:
        # Must execute cleanly without sqlite3.OperationalError
        results = await db_manager.search_notes(query=toxic, mode="lexical", limit=5)
        assert isinstance(results, list)

    # Valid keyword should still find the note
    results_valid = await db_manager.search_notes(query="Python NOT", mode="lexical", limit=5)
    assert len(results_valid) == 1
    assert results_valid[0][0].id == "toxic_test_note"


def test_sanitize_fts_query_preserves_domains_and_urls() -> None:
    """Ensure _sanitize_fts_query splits on punctuation instead of fusing domains."""
    from ekko.db.manager import _sanitize_fts_query

    # Dot should not fuse words together
    sanitized = _sanitize_fts_query("sqlite.org")
    assert sanitized == '"sqlite" OR "org"'

    # URLs with slashes and colons
    sanitized_url = _sanitize_fts_query("https://example.com/docs")
    assert sanitized_url == '"https" OR "example" OR "com" OR "docs"'


@pytest.mark.asyncio
async def test_multi_chunk_indexing_and_deep_paragraph_retrieval(db_manager: DatabaseManager) -> None:
    """Ensure long notes are chunked into multiple vectors and deep content is retrieved semantically."""
    # Build a long note (>3000 chars) with 3 distinct sections
    section1 = "## Overview\n" + ("Foundational theories of computation. " * 30)
    section2 = "## Intermediate Systems\n" + ("Distributed consensus algorithms and Paxos. " * 30)
    section3 = "## Frontier Research\n" + ("Quantum annealing solves specific quadratic unconstrained optimization problems. " * 30)
    long_content = f"{section1}\n\n{section2}\n\n{section3}"

    note = KnowledgeNote(
        id="note_deep",
        slug="deep-quantum-research",
        title="Comprehensive Modern Computing Survey",
        summary="A broad overview ranging from classical to quantum architectures.",
        content=long_content,
        tags=["quantum", "computing", "distributed"],
        sources=[],
    )

    # Chunks will be generated automatically
    chunks = await db_manager.get_note_chunks(note.id)
    assert len(chunks) == 0

    # Provide distinct vectors for each chunk: chunk 0 = vec_base, chunk 2 (deep) = vec_quantum
    vec_general = [0.1] * 384
    vec_quantum = [-0.8] * 384
    # We will pass embeddings for the 3 sections
    await db_manager.save_knowledge_note(note, embeddings=[vec_general, vec_general, vec_quantum])

    saved_chunks = await db_manager.get_note_chunks(note.id)
    assert len(saved_chunks) >= 3

    # Query matching specifically the deep 3rd chunk
    query_vec = [-0.79] * 384
    results = await db_manager.search_notes(query="anything", query_embedding=query_vec, mode="semantic", limit=5)
    assert len(results) >= 1
    assert results[0][0].id == "note_deep"


@pytest.mark.asyncio
async def test_save_knowledge_note_idempotence_purges_old_chunks(db_manager: DatabaseManager) -> None:
    """Ensure updating a note replaces old chunks and vectors completely without orphan rows."""
    note = KnowledgeNote(
        id="note_idempotent",
        slug="idempotent-test",
        title="Initial Note",
        summary="Summary v1",
        content="## Section 1\n" + ("A" * 1600) + "\n\n## Section 2\n" + ("B" * 1600),
        tags=["test"],
        sources=[],
    )
    vec1 = [0.2] * 384
    await db_manager.save_knowledge_note(note, embedding=vec1)
    chunks_v1 = await db_manager.get_note_chunks("note_idempotent")
    assert len(chunks_v1) >= 2

    # Update note with shorter single-chunk content
    updated_note = KnowledgeNote(
        id="note_idempotent",
        slug="idempotent-test",
        title="Updated Note",
        summary="Summary v2",
        content="# Short updated text\nNow fits entirely in one chunk.",
        tags=["test", "v2"],
        sources=[],
    )
    await db_manager.save_knowledge_note(updated_note, embedding=vec1)
    chunks_v2 = await db_manager.get_note_chunks("note_idempotent")
    assert len(chunks_v2) == 1
    assert "Short updated text" in chunks_v2[0]


@pytest.mark.asyncio
async def test_delete_knowledge_note_cascades_chunks_and_vectors(db_manager: DatabaseManager) -> None:
    """Ensure delete_knowledge_note cleans up notes, chunks, and vector table entries."""
    note = KnowledgeNote(
        id="note_to_delete",
        slug="note-to-delete",
        title="Ephemeral Note",
        summary="Will be deleted.",
        content="## Section A\n" + ("Content A " * 100) + "\n\n## Section B\n" + ("Content B " * 100),
        tags=["ephemeral"],
        sources=[],
    )
    await db_manager.save_knowledge_note(note, embedding=[0.3] * 384)
    chunks_before = await db_manager.get_note_chunks("note_to_delete")
    assert len(chunks_before) >= 2

    deleted = await db_manager.delete_knowledge_note("note_to_delete")
    assert deleted is True

    chunks_after = await db_manager.get_note_chunks("note_to_delete")
    assert len(chunks_after) == 0

    # Ensure search does not return it
    results = await db_manager.search_notes(query="Ephemeral", mode="lexical", limit=5)
    assert not any(n.id == "note_to_delete" for n, _ in results)


@pytest.mark.asyncio
async def test_backfill_existing_notes_into_chunks(tmp_path: Path) -> None:
    """Ensure init_schema backfills existing knowledge_notes into note_chunks when chunks are empty."""
    db_file = tmp_path / "backfill_test.db"
    store = DatabaseManager(db_path=db_file)

    # Manually insert note directly into knowledge_notes mimicking pre-migration state
    with store._connection() as conn:
        conn.execute(
            """
            INSERT INTO knowledge_notes (id, slug, title, summary, content, tags, sources, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "legacy_note_1",
                "legacy-note-1",
                "Legacy Research Note",
                "Summary",
                "## Chapter 1\nContent 1\n\n## Chapter 2\nContent 2",
                "[]",
                "[]",
                "2026-10-01T00:00:00",
                "2026-10-01T00:00:00",
            ),
        )
        # Clear note_chunks to simulate empty state
        conn.execute("DELETE FROM note_chunks;")

    # Run init_schema to trigger backfill
    store.init_schema()

    chunks = await store.get_note_chunks("legacy_note_1")
    assert len(chunks) >= 1

