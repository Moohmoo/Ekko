"""LiteLLM outbound adapter providing model-agnostic inference."""

from typing import Any
import litellm

from ekko.core.errors import ProviderError
from ekko.core.models import Message, ModelResponse


def _format_messages(messages: list[Message]) -> list[dict[str, str]]:
    """Convert domain messages into LiteLLM compatible dictionary payload."""
    return [{"role": msg.role, "content": msg.content} for msg in messages]


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
        temperature = kwargs.get("temperature", self.temperature)

        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=payload,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=temperature,
            )
            content = response.choices[0].message.content or ""
            p_tokens, c_tokens = _extract_tokens(getattr(response, "usage", None))

            return ModelResponse(
                content=content,
                model_name=self.model,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
            )
        except Exception as err:
            # Trap foreign vendor exceptions to avoid leaking infrastructure into domain
            raise ProviderError(f"LLM inference failed: {err}", cause=err) from err
