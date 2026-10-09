"""Integration test verifying end-to-end ReAct flow with ArxivTool and EkkoEngine."""

from unittest.mock import AsyncMock, patch
import httpx
import pytest

from ekko.core.engine import EkkoEngine
from ekko.core.models import ModelResponse, ToolCall
from ekko.memory.in_memory import InMemoryMemory
from ekko.tools.arxiv import ArxivTool
from ekko.tools.registry import ToolRegistry

MOCK_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2610.11111v1</id>
    <published>2026-10-09T00:00:00Z</published>
    <title>Generative Protein Folding with SE(3) Equivariant Diffusion</title>
    <summary>We present a diffusion model achieving state of the art results on de novo protein backbone design.</summary>
    <author><name>Marie Curie</name></author>
    <author><name>Alan Turing</name></author>
  </entry>
</feed>
"""


@pytest.mark.asyncio
async def test_arxiv_tool_integration_in_engine() -> None:
    """Ensure engine delegates to ArxivTool and synthesizes academic preprints."""
    registry = ToolRegistry()
    registry.register(ArxivTool())

    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(
            content="",
            model_name="mock-llm",
            tool_calls=[
                ToolCall(
                    id="call_arxiv",
                    name="arxiv",
                    arguments={"query": "protein folding", "limit": 3},
                )
            ],
        ),
        ModelResponse(
            content="Synthèse : Le papier propose un modèle de diffusion SE(3) équivariant pour le design de novo de protéines.",
            model_name="mock-llm",
        ),
    ]

    mock_response = httpx.Response(
        200,
        text=MOCK_ARXIV_XML,
        request=httpx.Request("GET", "https://export.arxiv.org/api/query"),
    )

    memory = InMemoryMemory()
    engine = EkkoEngine(provider=mock_provider, memory=memory, tools=registry)

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        reply = await engine.process_message("Quels sont les derniers papiers sur le repliement de protéines ?")

    assert "SE(3) équivariant" in reply
    messages = await memory.get_messages("default")
    assert len(messages) == 4
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[2].role == "tool"
    assert messages[2].tool_call_id == "call_arxiv"
    assert "Generative Protein Folding with SE(3)" in messages[2].content
    assert messages[3].role == "assistant"
