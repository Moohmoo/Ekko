"""Unit tests for immutable typed engine events."""

import pytest
from pydantic import ValidationError, TypeAdapter

from ekko.core.events import (
    BaseEngineEvent,
    EngineError,
    EngineEvent,
    StepStarted,
    TokenChunk,
    ToolCallCompleted,
    ToolCallStarted,
    TurnCompleted,
)


def test_step_started_event() -> None:
    """Validate StepStarted initialization and immutability."""
    event = StepStarted(step_index=1, max_steps=5)
    assert event.type == "step_started"
    assert event.step_index == 1
    assert event.max_steps == 5

    with pytest.raises(ValidationError):
        event.step_index = 2  # type: ignore[misc]


def test_tool_call_started_event() -> None:
    """Validate ToolCallStarted event properties and defaults."""
    event = ToolCallStarted(
        tool_call_id="call-123",
        tool_name="arxiv",
        arguments={"query": "quantum"},
    )
    assert event.type == "tool_call_started"
    assert event.tool_call_id == "call-123"
    assert event.tool_name == "arxiv"
    assert event.arguments == {"query": "quantum"}


def test_tool_call_completed_event() -> None:
    """Validate ToolCallCompleted event with timing information."""
    event = ToolCallCompleted(
        tool_call_id="call-123",
        tool_name="arxiv",
        success=True,
        summary="Retrieved 5 papers",
        duration_ms=125.5,
    )
    assert event.type == "tool_call_completed"
    assert event.success is True
    assert event.summary == "Retrieved 5 papers"
    assert event.duration_ms == 125.5


def test_token_chunk_event() -> None:
    """Validate TokenChunk event for incremental streaming."""
    event = TokenChunk(delta="Hello ")
    assert event.type == "token_chunk"
    assert event.delta == "Hello "


def test_turn_completed_event() -> None:
    """Validate TurnCompleted event attributes."""
    event = TurnCompleted(content="Final synthesized response", total_steps=2)
    assert event.type == "turn_completed"
    assert event.content == "Final synthesized response"
    assert event.total_steps == 2


def test_engine_error_event() -> None:
    """Validate EngineError event and actionable hints."""
    event = EngineError(
        error_type="ProviderUnavailable",
        message="Connection refused on port 11434",
        actionable_hint="Check if Ollama is running.",
    )
    assert event.type == "engine_error"
    assert event.error_type == "ProviderUnavailable"
    assert event.message == "Connection refused on port 11434"
    assert event.actionable_hint == "Check if Ollama is running."


def test_engine_event_polymorphic_deserialization() -> None:
    """Verify discriminated union parsing via Pydantic TypeAdapter."""
    adapter = TypeAdapter(EngineEvent)

    raw_data = {
        "type": "turn_completed",
        "content": "All done!",
        "total_steps": 1,
    }
    parsed = adapter.validate_python(raw_data)
    assert isinstance(parsed, TurnCompleted)
    assert parsed.content == "All done!"
    assert parsed.total_steps == 1
