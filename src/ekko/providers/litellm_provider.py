"""LiteLLM outbound adapter providing model-agnostic inference."""

from typing import Any
import litellm

from ekko.core.errors import ProviderError
from ekko.core.models import Message, ModelResponse
from ekko.logger import get_logger

logger = get_logger("providers.litellm")


def _format_single_message(msg: Message) -> dict[str, Any]:
    """Format single message into LiteLLM compatible structure."""
    return {"role": msg.role, "content": msg.content}


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
        for k, v in kwargs.items():
            if k not in call_kwargs:
                call_kwargs[k] = v

        logger.debug("Inference targeting model: %s", self.model)
        logger.debug("Inference prompt payload: %s", payload)

        try:
            response = await litellm.acompletion(**call_kwargs)
            message = response.choices[0].message
            content = message.content or ""
            p_tokens, c_tokens = _extract_tokens(getattr(response, "usage", None))

            return ModelResponse(
                content=content,
                model_name=self.model,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
            )
        except Exception as err:
            logger.error("Inference failure on model '%s': %s", self.model, err)
            raise ProviderError(f"LLM inference failed: {err}", cause=err) from err
