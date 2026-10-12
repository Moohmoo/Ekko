"""Unit tests for GetRecentNotesTool."""

from datetime import datetime
from unittest.mock import AsyncMock
import pytest

from ekko.core.models import KnowledgeNote
from ekko.tools.get_recent_notes import GetRecentNotesTool


@pytest.mark.asyncio
async def test_get_recent_notes_empty() -> None:
    """Ensure tool returns clean empty message when no notes are found."""
    mock_store = AsyncMock()
    mock_store.get_recent_notes.return_value = []
    tool = GetRecentNotesTool(db_manager=mock_store)

    result = await tool.execute(limit=5)
    assert result.success is True
    assert "Aucune note distillée trouvée" in result.content


@pytest.mark.asyncio
async def test_get_recent_notes_success() -> None:
    """Ensure tool formats recent notes chronologically."""
    mock_store = AsyncMock()
    mock_store.get_recent_notes.return_value = [
        KnowledgeNote(
            id="note-1",
            slug="2026-10-12_deep-learning",
            title="Deep Learning Breakthroughs",
            summary="Key points about model scale.",
            content="Full note text on attention mechanisms.",
            tags=["ai", "deep-learning"],
            sources=["https://arxiv.org/abs/1234"],
            created_at=datetime(2026, 10, 12, 14, 30),
        )
    ]
    tool = GetRecentNotesTool(db_manager=mock_store)

    result = await tool.execute(limit=1)
    assert result.success is True
    assert "Deep Learning Breakthroughs" in result.content
    assert "#ai, #deep-learning" in result.content
    assert "https://arxiv.org/abs/1234" in result.content


@pytest.mark.asyncio
async def test_get_recent_notes_error_handling() -> None:
    """Ensure tool handles database exceptions gracefully."""
    mock_store = AsyncMock()
    mock_store.get_recent_notes.side_effect = RuntimeError("DB locked")
    tool = GetRecentNotesTool(db_manager=mock_store)

    result = await tool.execute(limit=3)
    assert result.success is False
    assert result.error == "GetRecentNotesError"
    assert "Erreur lors de la récupération" in result.content
