"""Unit tests for core domain models."""

import pytest
from pydantic import ValidationError

from ekko.core.models import Message, ModelResponse


def test_message_valid_roles() -> None:
    """Ensure Message accepts valid standard roles."""
    msg_user = Message(role="user", content="Hello")
    msg_asst = Message(role="assistant", content="Hi there")
    msg_sys = Message(role="system", content="System instruction")

    assert msg_user.role == "user"
    assert msg_user.content == "Hello"
    assert msg_asst.role == "assistant"
    assert msg_sys.role == "system"


def test_message_invalid_role_raises_error() -> None:
    """Ensure Message rejects unexpected roles to preserve contract integrity."""
    with pytest.raises(ValidationError):
        Message(role="invalid_role", content="Test")


def test_message_empty_content_rejected() -> None:
    """Ensure Message content cannot be empty whitespace."""
    with pytest.raises(ValidationError):
        Message(role="user", content="   ")


def test_model_response_creation() -> None:
    """Ensure ModelResponse holds model output and token metrics."""
    response = ModelResponse(
        content="Response text",
        model_name="gemini-2.5-flash",
        prompt_tokens=10,
        completion_tokens=20,
    )

    assert response.content == "Response text"
    assert response.model_name == "gemini-2.5-flash"
    assert response.total_tokens == 30


def test_tool_call_and_result_creation() -> None:
    """Ensure ToolCall and ToolResult models instantiate with correct types."""
    from ekko.core.models import ToolCall, ToolResult

    call = ToolCall(id="call_123", name="search", arguments={"q": "ekko"})
    result = ToolResult(content="Found 1 result", success=True)

    assert call.id == "call_123"
    assert call.name == "search"
    assert call.arguments == {"q": "ekko"}
    assert result.content == "Found 1 result"
    assert result.success is True
    assert result.error is None


def test_message_assistant_with_tool_calls_allows_empty_or_none_content() -> None:
    """Ensure assistant messages with tool calls allow None or empty content."""
    from ekko.core.models import ToolCall

    call = ToolCall(id="call_1", name="search", arguments={})

    msg_none = Message(role="assistant", content=None, tool_calls=[call])
    msg_empty = Message(role="assistant", content="", tool_calls=[call])

    assert msg_none.content == ""
    assert len(msg_none.tool_calls) == 1
    assert msg_empty.content == ""


def test_message_tool_role_requires_tool_call_id() -> None:
    """Ensure role='tool' records tool_call_id and message content."""
    msg = Message(role="tool", content="Result text", tool_call_id="call_123")
    assert msg.role == "tool"
    assert msg.tool_call_id == "call_123"

    with pytest.raises(ValidationError):
        Message(role="tool", content="Result text", tool_call_id=None)


def test_model_response_supports_tool_calls() -> None:
    """Ensure ModelResponse holds list of tool calls."""
    from ekko.core.models import ToolCall

    call = ToolCall(id="call_99", name="bash", arguments={"cmd": "ls"})
    response = ModelResponse(
        content="",
        model_name="mock",
        tool_calls=[call],
    )

    assert response.content == ""
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "bash"


def test_core_domain_entities_instantiation() -> None:
    """Ensure core models RawSignal, KnowledgeNote, SourceState, and SignalStatus instantiate cleanly."""
    from ekko.core.models import KnowledgeNote, RawSignal, SignalStatus, SourceState

    state = SourceState(id="src_1", source_type="rss", url_or_path="https://example.com/rss")
    assert state.id == "src_1"
    assert state.consecutive_errors == 0

    signal = RawSignal(id="sig_1", title="New LLM Breakthrough", url="https://example.com/ai")
    assert signal.id == "sig_1"
    assert signal.status == SignalStatus.PENDING

    note = KnowledgeNote(
        id="note_1",
        slug="new-llm-breakthrough",
        title="New LLM Breakthrough",
        summary="A summary of the breakthrough",
        content="Full markdown content",
        tags=["ai", "research"],
        sources=["https://example.com/ai"],
    )
    assert note.id == "note_1"
    assert note.tags == ["ai", "research"]
    assert note.slug == "new-llm-breakthrough"

