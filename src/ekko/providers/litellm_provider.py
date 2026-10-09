"""LiteLLM outbound adapter providing model-agnostic inference and tool calling."""

from collections.abc import AsyncIterator
import json
from typing import Any
import litellm

from ekko.core.errors import ProviderError
from ekko.core.models import Message, ModelResponse, ToolCall
from ekko.utils.logger import get_logger

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
    ) -> AsyncIterator[Any]:
        """Call LiteLLM with stream=True and yield streaming chunks."""
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

        try:
            response = await litellm.acompletion(**call_kwargs)
            if hasattr(response, "__aiter__"):
                async for chunk in response:
                    yield chunk
            else:
                for chunk in response:
                    yield chunk
        except Exception as err:
            logger.error("Streaming inference failure on model '%s': %s", self.model, err)
            raise ProviderError(f"LLM streaming inference failed: {err}", cause=err) from err


