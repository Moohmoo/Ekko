"""Integration test verifying end-to-end ReAct flow with ReadResourceTool and EkkoEngine."""

from pathlib import Path
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from ekko.core.engine import EkkoEngine
from ekko.core.models import ModelResponse, ToolCall
from ekko.memory.in_memory import InMemoryMemory
from ekko.tools.read_resource import ReadResourceTool
from ekko.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_read_resource_tool_integration_web_in_engine() -> None:
    """Ensure engine delegates to ReadResourceTool for web URLs and synthesizes extracted content."""
    registry = ToolRegistry()
    registry.register(ReadResourceTool())

    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(
            content="",
            model_name="mock-llm",
            tool_calls=[
                ToolCall(
                    id="call_res",
                    name="read_resource",
                    arguments={"uri": "https://example.com/post"},
                )
            ],
        ),
        ModelResponse(
            content="Résumé : L'article présente une percée majeure en calcul neuromorphique.",
            model_name="mock-llm",
        ),
    ]

    html_content = "<html><body><article><h1>Neuromorphic Breakthrough</h1><p>Breakthrough details.</p></article></body></html>"
    mock_response = httpx.Response(
        200,
        text=html_content,
        request=httpx.Request("GET", "https://example.com/post"),
    )

    memory = InMemoryMemory()
    engine = EkkoEngine(provider=mock_provider, memory=memory, tools=registry)

    with (
        patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get,
        patch("trafilatura.extract") as mock_extract,
        patch("ekko.tools.read_resource.SSRFValidator.validate_url", return_value="https://example.com/post"),
    ):
        mock_get.return_value = mock_response
        mock_extract.return_value = "# Neuromorphic Breakthrough\n\nBreakthrough details."

        reply = await engine.process_message(
            "Peux-tu lire cet article https://example.com/post et me le résumer ?"
        )

    assert "calcul neuromorphique" in reply
    messages = await memory.get_messages("default")
    assert len(messages) == 4
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[2].role == "tool"
    assert messages[2].tool_call_id == "call_res"
    assert "# Neuromorphic Breakthrough" in messages[2].content
    assert messages[3].role == "assistant"


@pytest.mark.asyncio
async def test_read_resource_tool_integration_local_file_in_engine(tmp_path: Path) -> None:
    """Ensure engine delegates to ReadResourceTool for local files and reads file content."""
    local_file = tmp_path / "paper_notes.md"
    local_file.write_text("# DNA Assembly\nStep-by-step protocol for assembly.", encoding="utf-8")

    registry = ToolRegistry()
    registry.register(ReadResourceTool())

    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(
            content="",
            model_name="mock-llm",
            tool_calls=[
                ToolCall(
                    id="call_file",
                    name="read_resource",
                    arguments={"uri": str(local_file)},
                )
            ],
        ),
        ModelResponse(
            content="J'ai lu vos notes locales : le protocole d'assemblage d'ADN est documenté.",
            model_name="mock-llm",
        ),
    ]

    memory = InMemoryMemory()
    engine = EkkoEngine(provider=mock_provider, memory=memory, tools=registry)

    reply = await engine.process_message(f"Lis mon fichier local {local_file}")
    assert "assemblage d'ADN" in reply

    messages = await memory.get_messages("default")
    assert len(messages) == 4
    assert "# DNA Assembly" in messages[2].content
