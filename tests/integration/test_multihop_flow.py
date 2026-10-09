"""Integration test validating autonomous multi-hop tool chaining in EkkoEngine."""

from unittest.mock import AsyncMock, patch
import httpx
import pytest

from ekko.core.engine import EkkoEngine
from ekko.core.models import ModelResponse, ToolCall
from ekko.memory.in_memory import InMemoryMemory
from ekko.tools.hacker_news import HackerNewsTool
from ekko.tools.registry import ToolRegistry
from ekko.tools.url_reader import UrlReaderTool


@pytest.mark.asyncio
async def test_multihop_autonomous_chaining_hacker_news_to_url_reader() -> None:
    """Ensure engine autonomously chains a radar tool call followed by a url_reader call.

    Scenario:
    1. User asks for in-depth technical analysis of the latest AI announcement on Hacker News.
    2. Step 1 (Model): calls 'hacker_news'.
    3. Engine executes 'hacker_news' and stores observation in memory.
    4. Step 2 (Model): inspects the observation, picks top URL and autonomously calls 'url_reader'.
    5. Engine executes 'url_reader' and stores observation in memory.
    6. Step 3 (Model): synthesizes extracted article body into final response without further tool calls.
    """
    registry = ToolRegistry()
    registry.register(HackerNewsTool())
    registry.register(UrlReaderTool())

    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        # Step 1: Model calls hacker_news
        ModelResponse(
            content="",
            model_name="mock-llm",
            tool_calls=[
                ToolCall(
                    id="call_hn_radar",
                    name="hacker_news",
                    arguments={"days": 7, "limit": 5},
                )
            ],
        ),
        # Step 2: Model sees hacker_news output and decides to fetch the article body
        ModelResponse(
            content="",
            model_name="mock-llm",
            tool_calls=[
                ToolCall(
                    id="call_url_reader",
                    name="url_reader",
                    arguments={"url": "https://example.com/mistral-large-4"},
                )
            ],
        ),
        # Step 3: Model receives extracted body and provides final synthesis
        ModelResponse(
            content=(
                "Synthèse approfondie : L'annonce Mistral Large 4 introduit un modèle de 128k "
                "avec raisonnement multi-modal natif et des gains significatifs en inférence."
            ),
            model_name="mock-llm",
        ),
    ]

    mock_hn_response = httpx.Response(
        200,
        json={
            "hits": [
                {
                    "title": "Mistral Large 4 Release and Benchmarks",
                    "url": "https://example.com/mistral-large-4",
                    "points": 750,
                    "num_comments": 340,
                    "created_at": "2026-10-09T00:00:00Z",
                    "objectID": "888111",
                }
            ]
        },
        request=httpx.Request("GET", "https://hn.algolia.com/api/v1/search"),
    )

    mock_article_html = (
        "<html><body><article>"
        "<h1>Mistral Large 4</h1>"
        "<p>Mistral Large 4 is our new frontier model with 128k context and native reasoning.</p>"
        "</article></body></html>"
    )
    mock_article_response = httpx.Response(
        200,
        text=mock_article_html,
        request=httpx.Request("GET", "https://example.com/mistral-large-4"),
    )

    memory = InMemoryMemory()
    engine = EkkoEngine(
        provider=mock_provider,
        memory=memory,
        tools=registry,
        max_iterations=5,
    )

    async def mock_get(url: str, *args, **kwargs) -> httpx.Response:
        if "algolia" in str(url):
            return mock_hn_response
        return mock_article_response

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as patch_get, patch(
        "ekko.tools.url_reader.trafilatura.extract"
    ) as mock_extract:
        patch_get.side_effect = mock_get
        mock_extract.return_value = (
            "# Mistral Large 4\n\nMistral Large 4 is our new frontier model with 128k context."
        )

        user_query = "Analyse en profondeur la dernière annonce majeure d'IA sur Hacker News."
        final_answer = await engine.process_message(user_query)

    # 1. Assertion on final answer
    assert "Mistral Large 4" in final_answer
    assert "raisonnement multi-modal" in final_answer

    # 2. Assertions on provider calls: exactly 3 turns
    assert mock_provider.generate.call_count == 3

    # 3. Assertions on message history structure: exactly 6 messages
    messages = await memory.get_messages("default")
    assert len(messages) == 6

    # Message 0: User prompt
    assert messages[0].role == "user"
    assert messages[0].content == user_query

    # Message 1: Assistant calling hacker_news
    assert messages[1].role == "assistant"
    assert messages[1].tool_calls is not None
    assert messages[1].tool_calls[0].name == "hacker_news"

    # Message 2: Tool result from hacker_news
    assert messages[2].role == "tool"
    assert messages[2].tool_call_id == "call_hn_radar"
    assert "Mistral Large 4 Release and Benchmarks" in messages[2].content

    # Message 3: Assistant calling url_reader
    assert messages[3].role == "assistant"
    assert messages[3].tool_calls is not None
    assert messages[3].tool_calls[0].name == "url_reader"
    assert messages[3].tool_calls[0].arguments["url"] == "https://example.com/mistral-large-4"

    # Message 4: Tool result from url_reader
    assert messages[4].role == "tool"
    assert messages[4].tool_call_id == "call_url_reader"
    assert "# Mistral Large 4" in messages[4].content

    # Message 5: Final assistant response
    assert messages[5].role == "assistant"
    assert "Synthèse approfondie" in messages[5].content
