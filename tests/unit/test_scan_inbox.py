"""Unit tests for ScanInboxTool."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from ekko.core.models import RawSignal, SignalStatus
from ekko.tools.catalog import ToolCatalog
from ekko.tools.scan_inbox import ScanInboxInput, ScanInboxTool


@pytest.mark.asyncio
async def test_scan_inbox_formats_signals() -> None:
    """Ensure ScanInboxTool displays retrieved signals in Markdown format."""
    mock_db = MagicMock()
    sig = RawSignal(
        id="sig_test_1",
        source_id="hn_tech",
        title="New Open Weights LLM",
        url="https://example.com/llm",
        author="karpathy",
        raw_content="Deep analysis of training recipe.",
        status=SignalStatus.PENDING,
    )
    mock_db.get_raw_signals = AsyncMock(return_value=[sig])

    tool = ScanInboxTool(db_manager=mock_db)
    result = await tool._run(status="pending", limit=5)

    assert result.success is True
    assert "New Open Weights LLM" in result.content
    assert "hn_tech" in result.content
    assert "https://example.com/llm" in result.content
    assert "karpathy" in result.content


@pytest.mark.asyncio
async def test_scan_inbox_handles_empty() -> None:
    """Ensure tool returns friendly message when no signals match."""
    mock_db = MagicMock()
    mock_db.get_raw_signals = AsyncMock(return_value=[])

    tool = ScanInboxTool(db_manager=mock_db)
    result = await tool._run(status="retained")

    assert result.success is True
    assert "Aucun signal brut trouvé" in result.content


def test_tool_catalog_includes_scan_inbox() -> None:
    """Ensure ToolCatalog registers ScanInboxTool by default."""
    catalog = ToolCatalog(include_defaults=True)
    assert catalog.get_class("scan_inbox") is ScanInboxTool
