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
