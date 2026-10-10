"""Unit tests for QueryKnowledgeTool."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from ekko.infrastructure.database.models import KnowledgeNote
from ekko.tools.query_knowledge import QueryKnowledgeInput, QueryKnowledgeTool


@pytest.mark.asyncio
async def test_query_knowledge_formats_results_in_markdown() -> None:
    """Ensure QueryKnowledgeTool formats retrieved notes into clean Markdown."""
    mock_db = MagicMock()
    sample_note = KnowledgeNote(
        id="note_test",
        slug="2026-10-10-test-note",
        title="Test Knowledge Note",
        summary="A summary of test insights.",
        content="Full body text of the note.",
        tags=["test", "unit"],
        sources=["https://example.com/source"],
    )

    mock_db.search_notes = AsyncMock(return_value=[(sample_note, 0.032)])

    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1] * 384

    tool = QueryKnowledgeTool(db_manager=mock_db, embedder=mock_embedder)
    result = await tool._run(query="test insight", mode="hybrid", limit=3)

    assert result.success is True
    assert "Test Knowledge Note" in result.content
    assert "A summary of test insights." in result.content
    assert "Score" in result.content
    assert "https://example.com/source" in result.content


@pytest.mark.asyncio
async def test_query_knowledge_handles_empty_results() -> None:
    """Ensure tool returns clean message when no notes match."""
    mock_db = MagicMock()
    mock_db.search_notes = AsyncMock(return_value=[])

    tool = QueryKnowledgeTool(db_manager=mock_db)
    result = await tool._run(query="nonexistent term", mode="lexical")

    assert result.success is True
    assert "Aucune note de connaissance" in result.content
