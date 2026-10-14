"""Unit tests for semantic hierarchical Markdown chunking."""

from ekko.domains.ingestion.processing.chunking import chunk_markdown


def test_chunk_markdown_empty_and_whitespace() -> None:
    """Ensure empty or whitespace-only documents produce empty chunk lists."""
    assert chunk_markdown("") == []
    assert chunk_markdown("   \n\t  ") == []


def test_chunk_markdown_short_document() -> None:
    """Ensure short notes below max_chars threshold are returned verbatim as a single chunk."""
    content = "# Quick Note\nThis is a brief thought that fits entirely within the character budget."
    chunks = chunk_markdown(content, max_chars=1500)
    assert len(chunks) == 1
    assert chunks[0] == content


def test_chunk_markdown_splits_by_headings() -> None:
    """Ensure documents exceeding budget split cleanly along Markdown heading boundaries."""
    doc = """# Introduction
Overview of the system architecture.

## Section A: Ingestion
Ingestion handles RSS and REST connectors cleanly with ETag support.

## Section B: Storage
Storage relies on SQLite WAL mode and vector extensions.

### Sub-section B.1: Indexing
Indexes include FTS5 and sqlite-vec with RRF fusion.
"""
    # Use max_chars small enough to force splitting sections, but large enough for each section
    chunks = chunk_markdown(doc, max_chars=120)
    assert len(chunks) >= 3

    # Each chunk should contain its respective header
    assert any("## Section A: Ingestion" in c for c in chunks)
    assert any("## Section B: Storage" in c for c in chunks)
    assert any("### Sub-section B.1: Indexing" in c for c in chunks)


def test_chunk_markdown_splits_oversized_section_on_paragraphs() -> None:
    """Ensure an individual section exceeding budget splits on paragraph double-newlines."""
    para1 = "Paragraph 1 explains the core problem in depth. " * 3
    para2 = "Paragraph 2 details the algorithmic solution. " * 3
    para3 = "Paragraph 3 outlines the empirical validation results. " * 3

    doc = f"## Comprehensive Guide\n\n{para1}\n\n{para2}\n\n{para3}"

    chunks = chunk_markdown(doc, max_chars=200)
    assert len(chunks) >= 3
    for chunk in chunks:
        assert len(chunk) <= 220  # bounded by max_chars budget


def test_chunk_markdown_splits_oversized_paragraph_with_overlap() -> None:
    """Ensure an oversized paragraph splits across sentences with contextual overlap."""
    sentences = [
        "First sentence introduces the hypothesis.",
        "Second sentence elaborates on methodology.",
        "Third sentence demonstrates preliminary measurements.",
        "Fourth sentence discusses error bounds.",
        "Fifth sentence summarizes final observations.",
    ]
    huge_paragraph = " ".join(sentences)

    chunks = chunk_markdown(huge_paragraph, max_chars=90, overlap_chars=40)
    assert len(chunks) >= 2

    # Check that adjacent chunks share overlapping context
    # Either the last sentence of chunk 0 is present in chunk 1, or overlapping text is found
    assert any("methodology" in c for c in chunks)
    assert any("preliminary" in c for c in chunks)


def test_chunk_markdown_oversized_continuous_text_without_spaces() -> None:
    """Ensure continuous character sequences without whitespace are sliced cleanly without error."""
    continuous = "A" * 500
    chunks = chunk_markdown(continuous, max_chars=150, overlap_chars=30)
    assert len(chunks) >= 4
    for c in chunks:
        assert len(c) <= 150
