"""Handler pour le pipeline structuré de recherche technique et scientifique."""

import time
from collections.abc import AsyncIterator

from agent.context import ExecutionContext
from agent.pipeline import collect_sources, plan_research, synthesize_findings_stream
from agent.schemas import (
    AgentEvent,
    AgentRequest,
    AgentResponse,
    DoneEvent,
    PlanEvent,
    RetrievalEvent,
    StreamChunkEvent,
    ValidationEvent,
)
from agent.storage import SessionStorage
from providers import LLMProvider
from tools.base import BaseTool
from .base import BaseHandler


class ResearchHandler(BaseHandler):
    """Gère le workflow structuré de veille et recherche technique (Plan -> Collecte -> Synthèse)."""

    def __init__(
        self,
        provider: LLMProvider,
        storage: SessionStorage,
        search_tool: BaseTool | None = None,
    ) -> None:
        self.provider = provider
        self.storage = storage
        self.search_tool = search_tool

    async def _handle_no_sources(
        self,
        req: AgentRequest,
    ) -> AsyncIterator[AgentEvent]:
        msg = f"Aucune source vérifiée récente n'a été trouvée pour '{req.query}'."
        yield StreamChunkEvent(delta=msg)
        self.storage.record_message(req.session_id, "user", req.query)
        self.storage.record_message(req.session_id, "assistant", msg)
        yield DoneEvent(response=AgentResponse(content=msg, tools_used=["search"], thought="Aucune source."))

    async def _synthesize(
        self,
        req: AgentRequest,
        ctx: ExecutionContext,
        sources: str,
    ) -> AsyncIterator[AgentEvent]:
        t_synth = time.perf_counter()
        chunks: list[str] = []
        async for chunk in synthesize_findings_stream(self.provider, req.query, sources, ctx.user_profile):
            chunks.append(chunk)
            yield StreamChunkEvent(delta=chunk)

        final_ans = "".join(chunks).strip() or sources
        el_synth = max(0.1, time.perf_counter() - t_synth)
        yield ValidationEvent(content=final_ans, elapsed=el_synth)

        self.storage.record_message(req.session_id, "user", req.query)
        self.storage.record_message(req.session_id, "assistant", final_ans)
        yield DoneEvent(response=AgentResponse(content=final_ans, tools_used=["search"], thought="Synthèse certifiée."))

    async def handle_stream(
        self,
        req: AgentRequest,
        ctx: ExecutionContext,
    ) -> AsyncIterator[AgentEvent]:
        # 1. Cadrage
        t0 = time.perf_counter()
        plan = await plan_research(self.provider, req.query, ctx=ctx)
        el_plan = max(0.1, time.perf_counter() - t0)
        yield PlanEvent(focus=plan.focus, queries=plan.queries, elapsed=el_plan)

        # 2. Collecte
        if not self.search_tool:
            async for ev in self._handle_no_sources(req):
                yield ev
            return

        sources, count, el_retrieval = await collect_sources(self.search_tool, plan)
        yield RetrievalEvent(source=plan.focus, count=count, elapsed=el_retrieval)

        if count == 0 or not sources.strip():
            async for ev in self._handle_no_sources(req):
                yield ev
            return

        # 3. Synthèse streaming
        async for ev in self._synthesize(req, ctx, sources):
            yield ev
