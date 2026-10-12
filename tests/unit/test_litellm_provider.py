"""Unit tests for the LiteLLM provider adapter."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import pytest

from ekko.core.errors import ProviderError
from ekko.core.events import TokenChunk
from ekko.core.models import Message, ModelResponse, ToolCall
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


@pytest.mark.asyncio
async def test_litellm_provider_generate_stream_success() -> None:
    """Ensure generate_stream calls litellm with stream=True and yields chunks."""
    fake_chunks = [
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Chunk 1"))]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Chunk 2"))]),
    ]

    async def fake_stream(*args, **kwargs):
        for c in fake_chunks:
            yield c

    with patch(
        "litellm.acompletion",
        new_callable=AsyncMock,
        return_value=fake_stream(),
    ) as mock_acompletion:
        provider = LiteLLMProvider(model="gemini/gemini-2.5-flash", api_key="test-key")
        messages = [Message(role="user", content="Stream please")]

        collected = [chunk async for chunk in provider.generate_stream(messages)]

        assert len(collected) == 2
        assert isinstance(collected[0], TokenChunk)
        assert collected[0].delta == "Chunk 1"
        assert isinstance(collected[1], TokenChunk)
        assert collected[1].delta == "Chunk 2"

        mock_acompletion.assert_awaited_once_with(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": "Stream please"}],
            api_key="test-key",
            api_base=None,
            temperature=0.7,
            stream=True,
        )


@pytest.mark.asyncio
async def test_litellm_provider_generate_stream_accumulates_tool_calls() -> None:
    """Ensure generate_stream accumulates fragmented tool call deltas and yields ToolCall."""
    fake_tool_chunks = [
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(
                        content=None,
                        tool_calls=[
                            SimpleNamespace(
                                index=0,
                                id="call_1",
                                function=SimpleNamespace(name="arxiv", arguments='{"query": '),
                            )
                        ],
                    )
                )
            ]
        ),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(
                        content=None,
                        tool_calls=[
                            SimpleNamespace(
                                index=0,
                                id=None,
                                function=SimpleNamespace(name=None, arguments='"llm"}'),
                            )
                        ],
                    )
                )
            ]
        ),
    ]

    async def fake_stream(*args, **kwargs):
        for c in fake_tool_chunks:
            yield c

    with patch(
        "litellm.acompletion",
        new_callable=AsyncMock,
        return_value=fake_stream(),
    ):
        provider = LiteLLMProvider(model="gemini/gemini-2.5-flash")
        messages = [Message(role="user", content="Search")]

        collected = [chunk async for chunk in provider.generate_stream(messages)]

        assert len(collected) == 1
        assert isinstance(collected[0], ToolCall)
        assert collected[0].id == "call_1"
        assert collected[0].name == "arxiv"
        assert collected[0].arguments == {"query": "llm"}


@pytest.mark.asyncio
async def test_litellm_provider_generate_stream_maps_exception() -> None:
    """Ensure exceptions in generate_stream are wrapped into ProviderError."""
    with patch(
        "litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Stream failure"),
    ):
        provider = LiteLLMProvider(model="ollama/llama3.1")
        messages = [Message(role="user", content="Ping")]

        with pytest.raises(ProviderError) as exc_info:
            async for _ in provider.generate_stream(messages):
                pass

        assert "LLM streaming inference failed" in str(exc_info.value)
        assert isinstance(exc_info.value.cause, RuntimeError)


@pytest.mark.asyncio
async def test_litellm_provider_generate_stream_accumulates_dict_chunks() -> None:
    """Ensure generate_stream accumulates dictionary-format tool calls seamlessly."""
    dict_chunks = [
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_d1", "name": "arxiv", "arguments": '{"query": "'}]}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "arguments": 'dict_test"'}]}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "arguments": '}'}]}}]},
        {"choices": [{"delta": {"content": "Et c'est tout."}}]},
    ]

    async def fake_stream(*args, **kwargs):
        for c in dict_chunks:
            yield c

    with patch(
        "litellm.acompletion",
        new_callable=AsyncMock,
        return_value=fake_stream(),
    ):
        provider = LiteLLMProvider(model="gemini/gemini-2.5-flash")
        messages = [Message(role="user", content="Test dict")]

        collected = [chunk async for chunk in provider.generate_stream(messages)]

        tokens = [c for c in collected if isinstance(c, TokenChunk)]
        calls = [c for c in collected if isinstance(c, ToolCall)]

        assert len(tokens) == 1
        assert tokens[0].delta == "Et c'est tout."
        assert len(calls) == 1
        assert calls[0].id == "call_d1"
        assert calls[0].name == "arxiv"
        assert calls[0].arguments == {"query": "dict_test"}


