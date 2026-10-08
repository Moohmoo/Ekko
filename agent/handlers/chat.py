"""Handler pour les échanges conversationnels directs et rappels d'historique."""

from collections.abc import AsyncIterator

from agent.context import ExecutionContext
from agent.prompts import build_chat_prompt
from agent.schemas import (
    AgentEvent,
    AgentRequest,
    AgentResponse,
    DoneEvent,
    StreamChunkEvent,
)
from agent.storage import SessionStorage
from providers import LLMProvider
from .base import BaseHandler


class ChatHandler(BaseHandler):
    """Gère les échanges conversationnels directs et les rappels d'historique."""

    def __init__(self, provider: LLMProvider, storage: SessionStorage) -> None:
        self.provider = provider
        self.storage = storage

    async def handle_stream(
        self,
        req: AgentRequest,
        ctx: ExecutionContext,
    ) -> AsyncIterator[AgentEvent]:
        if not req.query.strip():
            msg = "Bonjour ! En quoi puis-je t'aider aujourd'hui ?"
            yield StreamChunkEvent(delta=msg)
            yield DoneEvent(response=AgentResponse(content=msg, thought="Requête vide."))
            return

        sys_prompt = build_chat_prompt(ctx.current_date, ctx.user_profile)
        prompt = f"{ctx.history_block}\n\nUtilisateur : {req.query}" if ctx.history_block else req.query
        chunks: list[str] = []
        async for chunk in self.provider.stream_text(prompt=prompt, system_instruction=sys_prompt):
            chunks.append(chunk)
            yield StreamChunkEvent(delta=chunk)

        final_ans = "".join(chunks).strip() or "Je n'ai pas pu générer de réponse. Peux-tu reformuler ?"
        self.storage.record_message(req.session_id, "user", req.query)
        self.storage.record_message(req.session_id, "assistant", final_ans)
        yield DoneEvent(response=AgentResponse(content=final_ans, thought="Échange conversationnel direct."))
