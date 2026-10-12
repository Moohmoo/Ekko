"""LiteLLM outbound adapter providing model-agnostic inference and tool calling."""

from collections.abc import AsyncIterator
import json
from typing import Any
import litellm

from ekko.core.errors import ProviderError
from ekko.core.events import TokenChunk
from ekko.core.models import Message, ModelResponse, ToolCall
from ekko.logger import get_logger

logger = get_logger("providers.litellm")



def _format_single_message(msg: Message) -> dict[str, Any]:
    """Format single message into LiteLLM compatible structure."""
    if msg.role == "tool":
        return {
            "role": "tool",
            "content": msg.content or "",
            "tool_call_id": msg.tool_call_id,
        }
    item: dict[str, Any] = {"role": msg.role, "content": msg.content or None}
    if msg.role == "assistant" and msg.tool_calls:
        item["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else tc.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return item


def _format_messages(messages: list[Message]) -> list[dict[str, Any]]:
    """Convert domain messages into LiteLLM compatible dictionary payload."""
    return [_format_single_message(msg) for msg in messages]


def _extract_tokens(usage: Any) -> tuple[int, int]:
    """Safely extract token usage counts with fallback to 0."""
    if not usage:
        return 0, 0
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    return prompt_tokens, completion_tokens


def _parse_tool_calls(raw_calls: Any) -> list[ToolCall]:
    """Parse raw LiteLLM tool calls into domain ToolCall instances."""
    if not raw_calls:
        return []
    parsed: list[ToolCall] = []
    for tc in raw_calls:
        func = getattr(tc, "function", None)
        name = getattr(func, "name", "")
        raw_args = getattr(func, "arguments", "{}")
        args: dict[str, Any] = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
        parsed.append(ToolCall(id=tc.id, name=name, arguments=args))
    return parsed


def _extract_field(obj: Any, key: str, default: Any = None) -> Any:
    """Extract attribute or dict item safely."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _extract_delta(chunk: Any) -> Any:
    """Extract the delta object from an inference streaming chunk."""
    delta = chunk
    choices = _extract_field(delta, "choices")
    if choices and len(choices) > 0:
        delta = choices[0]
    inner_delta = _extract_field(delta, "delta")
    if inner_delta is not None:
        delta = inner_delta
    return delta


def _accumulate_tool_call_delta(
    raw_tc: Any,
    accumulated: dict[int, dict[str, str]],
) -> None:
    """Accumulate fragmented tool call parts into an indexed buffer."""
    idx = _extract_field(raw_tc, "index", 0)
    if idx is None:
        idx = 0
    if idx not in accumulated:
        accumulated[idx] = {"id": "", "name": "", "arguments": ""}

    tc_id = _extract_field(raw_tc, "id")
    if tc_id:
        accumulated[idx]["id"] += str(tc_id)

    func = _extract_field(raw_tc, "function")
    fn_name = _extract_field(func, "name") if func else _extract_field(raw_tc, "name")
    if fn_name:
        accumulated[idx]["name"] += str(fn_name)

    fn_args = _extract_field(func, "arguments") if func else _extract_field(raw_tc, "arguments")
    if fn_args:
        accumulated[idx]["arguments"] += str(fn_args)


def _build_accumulated_tool_calls(accumulated: dict[int, dict[str, str]]) -> list[ToolCall]:
    """Convert accumulated string buffers into valid domain ToolCall instances."""
    results: list[ToolCall] = []
    for idx in sorted(accumulated.keys()):
        item = accumulated[idx]
        name = item["name"].strip()
        if not name:
            continue
        raw_args = item["arguments"].strip()
        try:
            parsed_args = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError:
            logger.warning("Failed to parse tool call JSON arguments for '%s': %s", name, raw_args)
            parsed_args = {"raw_arguments": raw_args}

        tc_id = item["id"].strip() or f"call_{idx}"
        results.append(ToolCall(id=tc_id, name=name, arguments=parsed_args))
    return results


def _process_stream_chunk(
    chunk: Any,
    accumulated_calls: dict[int, dict[str, str]],
) -> TokenChunk | None:
    """Process a raw streaming chunk and return TokenChunk or accumulate tool call deltas."""
    delta = _extract_delta(chunk)
    tc_deltas = _extract_field(delta, "tool_calls")
    if tc_deltas:
        for tc in tc_deltas:
            _accumulate_tool_call_delta(tc, accumulated_calls)
        return None
    chunk_content = _extract_field(delta, "content")
    if chunk_content:
        return TokenChunk(delta=chunk_content)
    return None


class LiteLLMProvider:
    """Universal LLM adapter leveraging LiteLLM routing."""

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        api_base: str | None = None,
        temperature: float = 0.7,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self.temperature = temperature

    async def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Call LiteLLM and translate response to domain ModelResponse."""
        payload = _format_messages(messages)
        call_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": payload,
            "api_key": self.api_key,
            "api_base": self.api_base,
            "temperature": kwargs.get("temperature", self.temperature),
        }
        if tools:
            call_kwargs["tools"] = tools

        logger.debug("Inference targeting model: %s (tools: %d)", self.model, len(tools) if tools else 0)
        logger.debug("Inference prompt payload: %s", payload)

        try:
            response = await litellm.acompletion(**call_kwargs)
            message = response.choices[0].message
            content = message.content or ""
            p_tokens, c_tokens = _extract_tokens(getattr(response, "usage", None))
            tool_calls = _parse_tool_calls(getattr(message, "tool_calls", None))
            logger.debug("Inference raw tool_calls: %s", tool_calls)

            return ModelResponse(
                content=content,
                model_name=self.model,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                tool_calls=tool_calls,
            )
        except Exception as err:
            logger.error("Inference failure on model '%s': %s", self.model, err)
            raise ProviderError(f"LLM inference failed: {err}", cause=err) from err

    async def generate_stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[TokenChunk | ToolCall]:
        """Call LiteLLM with stream=True and yield normalized TokenChunk and ToolCall instances."""
        payload = _format_messages(messages)
        call_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": payload,
            "api_key": self.api_key,
            "api_base": self.api_base,
            "temperature": kwargs.get("temperature", self.temperature),
            "stream": True,
        }
        if tools:
            call_kwargs["tools"] = tools

        logger.debug("Streaming inference targeting model: %s (tools: %d)", self.model, len(tools) if tools else 0)

        accumulated_calls: dict[int, dict[str, str]] = {}
        try:
            response = await litellm.acompletion(**call_kwargs)
            if hasattr(response, "__aiter__"):
                async for chunk in response:
                    event = _process_stream_chunk(chunk, accumulated_calls)
                    if event is not None:
                        yield event
            else:
                for chunk in response:
                    event = _process_stream_chunk(chunk, accumulated_calls)
                    if event is not None:
                        yield event

            if accumulated_calls:
                for tc in _build_accumulated_tool_calls(accumulated_calls):
                    yield tc
        except Exception as err:
            logger.error("Streaming inference failure on model '%s': %s", self.model, err)
            raise ProviderError(f"LLM streaming inference failed: {err}", cause=err) from err


