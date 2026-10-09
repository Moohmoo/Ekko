"""Integration test verifying end-to-end ReAct flow with UrlReaderTool and EkkoEngine."""

from unittest.mock import AsyncMock, patch
import httpx
import pytest

from ekko.core.engine import EkkoEngine
from ekko.core.models import ModelResponse, ToolCall
from ekko.memory.in_memory import InMemoryMemory
from ekko.tools.registry import ToolRegistry
from ekko.tools.url_reader import UrlReaderTool


@pytest.mark.asyncio
async def test_url_reader_tool_integration_in_engine() -> None:
    """Ensure engine delegates to UrlReaderTool and synthesizes extracted content."""
    registry = ToolRegistry()
    registry.register(UrlReaderTool())

    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(
            content="",
            model_name="mock-llm",
            tool_calls=[
                ToolCall(
                    id="call_url",
                    name="url_reader",
                    arguments={"url": "https://example.com/post"},
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

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get, patch(
        "ekko.tools.url_reader.trafilatura.extract"
    ) as mock_extract:
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
    assert messages[2].tool_call_id == "call_url"
    assert "# Neuromorphic Breakthrough" in messages[2].content
    assert messages[3].role == "assistant"
