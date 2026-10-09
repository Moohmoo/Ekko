"""Unit tests for the LiteLLM provider adapter."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import pytest

from ekko.core.errors import ProviderError
from ekko.core.models import Message, ModelResponse
from ekko.core.ports import LLMProviderPort
from ekko.providers.litellm_provider import LiteLLMProvider


def test_litellm_provider_implements_port() -> None:
    """Ensure LiteLLMProvider conforms to the domain LLMProviderPort protocol."""
    provider = LiteLLMProvider(model="gemini/gemini-flash")
    assert isinstance(provider, LLMProviderPort)


@pytest.mark.asyncio
async def test_litellm_provider_generate_success() -> None:
    """Ensure generate converts domain messages, calls LiteLLM, and returns ModelResponse."""
    fake_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Echo: Hello!"))],
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=8),
    )

    with patch(
        "litellm.acompletion",
        new_callable=AsyncMock,
        return_value=fake_completion,
    ) as mock_acompletion:
        provider = LiteLLMProvider(
            model="gemini/gemini-2.5-flash",
            api_key="test-key",
            temperature=0.2,
        )
        messages = [
            Message(role="system", content="Act as helper"),
            Message(role="user", content="Hello!"),
        ]

        result = await provider.generate(messages)

        assert isinstance(result, ModelResponse)
        assert result.content == "Echo: Hello!"
        assert result.model_name == "gemini/gemini-2.5-flash"
        assert result.prompt_tokens == 12
        assert result.completion_tokens == 8
        assert result.total_tokens == 20

        # Verify LiteLLM arguments
        mock_acompletion.assert_awaited_once_with(
            model="gemini/gemini-2.5-flash",
            messages=[
                {"role": "system", "content": "Act as helper"},
                {"role": "user", "content": "Hello!"},
            ],
            api_key="test-key",
            api_base=None,
            temperature=0.2,
        )


@pytest.mark.asyncio
async def test_litellm_provider_handles_local_api_base() -> None:
    """Ensure custom api_base is passed to LiteLLM for local LLM routing."""
    fake_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Local response"))],
        usage=None,
    )

    with patch(
        "litellm.acompletion",
        new_callable=AsyncMock,
        return_value=fake_completion,
    ) as mock_acompletion:
        provider = LiteLLMProvider(
            model="ollama/llama3.1",
            api_base="http://localhost:11434",
        )
        messages = [Message(role="user", content="Ping")]

        result = await provider.generate(messages)

        assert result.content == "Local response"
        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0

        mock_acompletion.assert_awaited_once_with(
            model="ollama/llama3.1",
            messages=[{"role": "user", "content": "Ping"}],
            api_key=None,
            api_base="http://localhost:11434",
            temperature=0.7,
        )


@pytest.mark.asyncio
async def test_litellm_provider_maps_exception_to_provider_error() -> None:
    """Ensure foreign network or API exceptions are wrapped into domain ProviderError."""
    with patch(
        "litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Connection refused by host"),
    ):
        provider = LiteLLMProvider(model="ollama/llama3.1")
        messages = [Message(role="user", content="Ping")]

        with pytest.raises(ProviderError) as exc_info:
            await provider.generate(messages)

        assert "LLM inference failed" in str(exc_info.value)
        assert isinstance(exc_info.value.cause, RuntimeError)


@pytest.mark.asyncio
async def test_litellm_provider_passes_tools_and_parses_tool_calls() -> None:
    """Ensure tools parameter is forwarded and tool_calls in response are converted."""
    from ekko.core.models import ToolCall

    fake_tool_call = SimpleNamespace(
        id="call_xyz",
        type="function",
        function=SimpleNamespace(
            name="calculator",
            arguments='{"a": 2, "b": 3}',
        ),
    )
    fake_completion = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[fake_tool_call],
                )
            )
        ],
        usage=None,
    )

    with patch(
        "litellm.acompletion",
        new_callable=AsyncMock,
        return_value=fake_completion,
    ) as mock_acompletion:
        provider = LiteLLMProvider(model="gemini/gemini-2.5-flash")
        messages = [Message(role="user", content="Calculate 2 + 3")]
        tool_schemas = [{"type": "function", "function": {"name": "calculator"}}]

        response = await provider.generate(messages, tools=tool_schemas)

        assert len(response.tool_calls) == 1
        assert response.tool_calls[0] == ToolCall(
            id="call_xyz",
            name="calculator",
            arguments={"a": 2, "b": 3},
        )
        assert response.content == ""

        mock_acompletion.assert_awaited_once_with(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": "Calculate 2 + 3"}],
            api_key=None,
            api_base=None,
            temperature=0.7,
            tools=tool_schemas,
        )


@pytest.mark.asyncio
async def test_litellm_provider_formats_assistant_tool_calls_and_tool_results() -> None:
    """Ensure Message with tool_calls and role='tool' are serialized for LiteLLM."""
    from ekko.core.models import ToolCall

    fake_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Final result: 5"))],
        usage=None,
    )

    with patch(
        "litellm.acompletion",
        new_callable=AsyncMock,
        return_value=fake_completion,
    ) as mock_acompletion:
        provider = LiteLLMProvider(model="gemini/gemini-2.5-flash")
        call = ToolCall(id="call_1", name="add", arguments={"x": 5})
        messages = [
            Message(role="user", content="Add 5"),
            Message(role="assistant", content=None, tool_calls=[call]),
            Message(role="tool", content="5", tool_call_id="call_1"),
        ]

        response = await provider.generate(messages)
        assert response.content == "Final result: 5"

        sent_messages = mock_acompletion.call_args.kwargs["messages"]
        assert sent_messages[0] == {"role": "user", "content": "Add 5"}
        assert sent_messages[1]["role"] == "assistant"
        assert sent_messages[1]["tool_calls"][0]["id"] == "call_1"
        assert sent_messages[2] == {
            "role": "tool",
            "content": "5",
            "tool_call_id": "call_1",
        }

