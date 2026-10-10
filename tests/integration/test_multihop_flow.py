"""Integration test validating autonomous multi-hop tool chaining in EkkoEngine."""

from datetime import datetime
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from ekko.core.engine import EkkoEngine
from ekko.core.models import ModelResponse, ToolCall
from ekko.memory.in_memory import InMemoryMemory
from ekko.memory.models import RawSignal, SignalStatus
from ekko.tools.read_resource import ReadResourceTool
from ekko.tools.registry import ToolRegistry
from ekko.tools.scan_inbox import ScanInboxTool


@pytest.mark.asyncio
async def test_multihop_autonomous_chaining_scan_inbox_to_read_resource() -> None:
    """Ensure engine autonomously chains scan_inbox followed by read_resource.

    Scenario:
    1. User asks to inspect incoming intelligence and read the main linked article.
    2. Step 1 (Model): calls 'scan_inbox'.
    3. Engine executes 'scan_inbox' and returns pending raw signals.
    4. Step 2 (Model): inspects the observation, picks top URL and autonomously calls 'read_resource'.
    5. Engine executes 'read_resource' and stores observation in memory.
    6. Step 3 (Model): synthesizes extracted article body into final response without further tool calls.
    """
    mock_db = AsyncMock()
    mock_db.get_raw_signals.return_value = [
        RawSignal(
            id="sig_test_1",
            source_id="hn_tech",
            title="Mistral Large 4 Release and Benchmarks",
            url="https://example.com/mistral-large-4",
            raw_content="Mistral Large 4 announced with 128k context.",
            clean_content="Mistral Large 4 announced with 128k context.",
            author="dev_ai",
            status=SignalStatus.PENDING,
            ingested_at=datetime(2026, 10, 10, 12, 0),
        )
    ]

    registry = ToolRegistry()
    registry.register(ScanInboxTool(db_manager=mock_db))
    registry.register(ReadResourceTool())

    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        # Step 1: Model calls scan_inbox
        ModelResponse(
            content="",
            model_name="mock-llm",
            tool_calls=[
                ToolCall(
                    id="call_scan_inbox",
                    name="scan_inbox",
                    arguments={"limit": 5},
                )
            ],
        ),
        # Step 2: Model sees scan_inbox output and decides to fetch article body
        ModelResponse(
            content="",
            model_name="mock-llm",
            tool_calls=[
                ToolCall(
                    id="call_read_resource",
                    name="read_resource",
                    arguments={"uri": "https://example.com/mistral-large-4"},
                )
            ],
        ),
        # Step 3: Model receives extracted body and provides final synthesis
        ModelResponse(
            content=(
                "Synthèse approfondie : L'annonce Mistral Large 4 introduit un modèle de 128k "
                "avec raisonnement multi-modal avancé."
            ),
            model_name="mock-llm",
            tool_calls=[],
        ),
    ]

    memory = InMemoryMemory()
    engine = EkkoEngine(
        provider=mock_provider,
        memory=memory,
        tools=registry,
        max_iterations=5,
    )

    mock_response = httpx.Response(
        200,
        text="<html>mock</html>",
        request=httpx.Request("GET", "https://example.com/mistral-large-4"),
    )

    with (
        patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_http_get,
        patch("trafilatura.extract") as mock_extract,
        patch("ekko.tools.read_resource.SSRFValidator.validate_url", return_value="https://example.com/mistral-large-4"),
    ):
        mock_http_get.return_value = mock_response
        mock_extract.return_value = (
            "# Mistral Large 4\n\nMistral Large 4 is our new frontier model with 128k context."
        )

        user_query = "Analyse en profondeur les signaux récents de la boîte de réception."
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

    # Message 1: Assistant calling scan_inbox
    assert messages[1].role == "assistant"
    assert messages[1].tool_calls is not None
    assert messages[1].tool_calls[0].name == "scan_inbox"

    # Message 2: Tool result from scan_inbox
    assert messages[2].role == "tool"
    assert messages[2].tool_call_id == "call_scan_inbox"
    assert "Mistral Large 4 Release and Benchmarks" in messages[2].content

    # Message 3: Assistant calling read_resource
    assert messages[3].role == "assistant"
    assert messages[3].tool_calls is not None
    assert messages[3].tool_calls[0].name == "read_resource"
    assert messages[3].tool_calls[0].arguments["uri"] == "https://example.com/mistral-large-4"

    # Message 4: Tool result from read_resource
    assert messages[4].role == "tool"
    assert messages[4].tool_call_id == "call_read_resource"
    assert "# Mistral Large 4" in messages[4].content
