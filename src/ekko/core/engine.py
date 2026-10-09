"""Core orchestrator executing conversational turns without tool delegation."""

from ekko.core.models import Message
from ekko.core.ports import LLMProviderPort, MemoryPort

DEFAULT_SYSTEM_PROMPT = (
    "You are Ekko, a modular agentic OS assistant. Be precise, helpful, and concise."
)


def _validate_user_input(text: str) -> str:
    """Validate and sanitize user input before passing down the pipeline."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("User input cannot be empty")
    return cleaned


class EkkoEngine:
    """Central orchestrator managing conversation turns between user, memory, and LLM."""

    def __init__(
        self,
        provider: LLMProviderPort,
        memory: MemoryPort,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self.provider = provider
        self.memory = memory
        self.system_prompt = system_prompt

    async def process_message(
        self,
        user_input: str,
        session_id: str = "default",
    ) -> str:
        """Process a conversational turn, record history, and return assistant reply."""
        sanitized_input = _validate_user_input(user_input)
        user_message = Message(role="user", content=sanitized_input)
        await self.memory.add_message(session_id, user_message)

        history = await self.memory.get_messages(session_id)
        prompt_payload = [
            Message(role="system", content=self.system_prompt),
            *history,
        ]

        response = await self.provider.generate(prompt_payload)
        assistant_message = Message(role="assistant", content=response.content)
        await self.memory.add_message(session_id, assistant_message)

        return response.content
