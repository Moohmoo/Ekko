"""Unit tests for SQLite hybrid search (FTS5 BM25 + sqlite-vec + RRF k=60)."""

from pathlib import Path
import pytest

from ekko.memory.hybrid_store import HybridStore
from ekko.memory.models import KnowledgeNote


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Provide a temporary database path."""
    return tmp_path / "test_hybrid.db"


@pytest.fixture
def db_manager(db_path: Path) -> HybridStore:
    """Provide an initialized HybridStore."""
    manager = HybridStore(db_path=db_path)
    manager.init_schema()
    return manager


@pytest.mark.asyncio
async def test_hybrid_search_indexes_fts_and_vectors(db_manager: HybridStore) -> None:
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
async def test_hybrid_search_rrf_scoring_order(db_manager: HybridStore) -> None:
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
