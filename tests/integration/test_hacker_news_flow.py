"""Integration test verifying end-to-end ReAct flow with HackerNewsTool and EkkoEngine."""

from unittest.mock import AsyncMock, patch
import httpx
import pytest

from ekko.core.engine import EkkoEngine
from ekko.core.models import ModelResponse, ToolCall
from ekko.memory.in_memory import InMemoryMemory
from ekko.tools.hacker_news import HackerNewsTool
from ekko.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_hacker_news_tool_integration_in_engine() -> None:
    """Ensure engine delegates to HackerNewsTool and synthesizes intelligence."""
    registry = ToolRegistry()
    registry.register(HackerNewsTool())

    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(
            content="",
            model_name="mock-llm",
            tool_calls=[
                ToolCall(
                    id="call_hn",
                    name="hacker_news",
                    arguments={"days": 7, "limit": 5},
                )
            ],
        ),
        ModelResponse(
            content="Synthèse : Une rupture majeure en supraconductivité quantique a été signalée sur HN.",
            model_name="mock-llm",
        ),
    ]

    mock_hn_response = httpx.Response(
        200,
        json={
            "hits": [
                {
                    "title": "Room-temperature quantum computing breakthrough",
                    "url": "https://example.com/quantum",
                    "points": 512,
                    "num_comments": 230,
                    "created_at": "2026-10-09T00:00:00Z",
                    "objectID": "999888",
                }
            ]
        },
        request=httpx.Request("GET", "https://hn.algolia.com/api/v1/search"),
    )

    memory = InMemoryMemory()
    engine = EkkoEngine(provider=mock_provider, memory=memory, tools=registry)

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_hn_response
        reply = await engine.process_message("Quelles sont les dernières nouvelles sur le quantique ?")

    assert "supraconductivité quantique" in reply
    messages = await memory.get_messages("default")
    assert len(messages) == 4
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[2].role == "tool"
    assert messages[2].tool_call_id == "call_hn"
    assert "Room-temperature quantum computing" in messages[2].content
    assert messages[3].role == "assistant"
