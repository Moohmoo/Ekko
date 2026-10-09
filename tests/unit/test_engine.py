"""Unit tests for the core conversation engine."""

from unittest.mock import AsyncMock
import pytest

from ekko.core.engine import EkkoEngine
from ekko.core.models import Message, ModelResponse
from ekko.memory.in_memory import InMemoryMemory


@pytest.mark.asyncio
async def test_engine_process_single_turn() -> None:
    """Ensure engine persists turn, sends prompt + history to provider, and returns reply."""
    mock_provider = AsyncMock()
    mock_provider.generate.return_value = ModelResponse(
        content="I am Ekko.",
        model_name="mock-model",
    )
    memory = InMemoryMemory()
    engine = EkkoEngine(
        provider=mock_provider,
        memory=memory,
        system_prompt="Custom system guardrail.",
    )

    reply = await engine.process_message("Who are you?", session_id="s1")

    assert reply == "I am Ekko."

    # Check that provider was called with system prompt followed by user turn
    call_args = mock_provider.generate.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0] == Message(role="system", content="Custom system guardrail.")
    assert call_args[1] == Message(role="user", content="Who are you?")

    # Check memory persistence
    messages = await memory.get_messages("s1")
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Who are you?"
    assert messages[1].role == "assistant"
    assert messages[1].content == "I am Ekko."


@pytest.mark.asyncio
async def test_engine_maintains_multi_turn_context() -> None:
    """Ensure subsequent turns include previous conversation history."""
    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(content="First reply", model_name="mock"),
        ModelResponse(content="Second reply", model_name="mock"),
    ]
    memory = InMemoryMemory()
    engine = EkkoEngine(provider=mock_provider, memory=memory)

    await engine.process_message("Turn 1", session_id="session-x")
    await engine.process_message("Turn 2", session_id="session-x")

    second_call_messages = mock_provider.generate.call_args_list[1][0][0]
    # system + user1 + asst1 + user2
    assert len(second_call_messages) == 4
    assert second_call_messages[1].content == "Turn 1"
    assert second_call_messages[2].content == "First reply"
    assert second_call_messages[3].content == "Turn 2"


@pytest.mark.asyncio
async def test_engine_rejects_empty_input() -> None:
    """Ensure blank inputs are rejected before hitting memory or provider."""
    mock_provider = AsyncMock()
    engine = EkkoEngine(provider=mock_provider, memory=InMemoryMemory())

    with pytest.raises(ValueError):
        await engine.process_message("   ")

    mock_provider.generate.assert_not_called()
