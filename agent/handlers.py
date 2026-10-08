"""Handlers spécialisés pour l'exécution des intentions utilisateur (Pattern Command/Handler).

Chaque handler encapsule un cycle d'exécution unique et autonome (SRP) :
- ChatHandler : échange conversationnel direct et rappels avec mémoire de travail.
- ResearchHandler : cadrage d'angle, collecte résiliente et synthèse technique en streaming.
- ActionHandler : exécution d'actions et inspection d'outils système.
"""

import json
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from core import Logger
from providers import LLMProvider
from tools.base import BaseTool
from tools.registry import ToolRegistry
from .context import ExecutionContext
from .pipeline import collect_sources, plan_research, synthesize_findings_stream
from .prompts import build_chat_prompt, build_system_prompt, format_step_prompt
from .schemas import (
    AgentAction,
    AgentEvent,
    AgentRequest,
    AgentResponse,
    DoneEvent,
    PlanEvent,
    RetrievalEvent,
    StreamChunkEvent,
    ThoughtEvent,
    ToolCallEvent,
    ToolResultEvent,
    ValidationEvent,
)
from .storage import SessionStorage
from .validator import validate_draft

logger = Logger("ekko.agent.handlers")


class BaseHandler(ABC):
    """Interface abstraite commune pour tous les gestionnaires d'intention."""

    @abstractmethod
    def handle_stream(
        self,
        req: AgentRequest,
        ctx: ExecutionContext,
    ) -> AsyncIterator[AgentEvent]:
        """Traite la requête et émet un flux asynchrone d'événements pour le présentateur."""


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
        sys_prompt = build_chat_prompt(ctx.current_date, ctx.user_profile)
        prompt = f"{ctx.history_block}\n\nUtilisateur : {req.query}" if ctx.history_block else req.query
        chunks: list[str] = []
        async for chunk in self.provider.stream_text(prompt=prompt, system_instruction=sys_prompt):
            chunks.append(chunk)
            yield StreamChunkEvent(delta=chunk)

        final_ans = "".join(chunks).strip()
        self.storage.record_message(req.session_id, "user", req.query)
        self.storage.record_message(req.session_id, "assistant", final_ans)
        yield DoneEvent(response=AgentResponse(content=final_ans, thought="Échange conversationnel direct."))


class ResearchHandler(BaseHandler):
    """Gère le workflow structuré de veille et recherche technique (Plan -> Collecte -> Synthèse)."""

    def __init__(
        self,
        provider: LLMProvider,
        storage: SessionStorage,
        search_tool: BaseTool,
    ) -> None:
        self.provider = provider
        self.storage = storage
        self.search_tool = search_tool

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
        sources, count, el_retrieval = await collect_sources(self.search_tool, plan)
        yield RetrievalEvent(source=plan.focus, count=count, elapsed=el_retrieval)

        if count == 0 or not sources.strip() or sources.startswith("Aucune source"):
            msg = f"Aucune source vérifiée récente n'a été trouvée pour '{req.query}'."
            yield StreamChunkEvent(delta=msg)
            self.storage.record_message(req.session_id, "user", req.query)
            self.storage.record_message(req.session_id, "assistant", msg)
            yield DoneEvent(response=AgentResponse(content=msg, tools_used=["search"], thought="Aucune source."))
            return

        # 3. Synthèse streaming
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


class ActionHandler(BaseHandler):
    """Gère l'exécution d'outils et d'actions via un cycle ReAct structuré."""

    def __init__(
        self,
        provider: LLMProvider,
        storage: SessionStorage,
        registry: ToolRegistry,
        max_steps: int = 5,
    ) -> None:
        self.provider = provider
        self.storage = storage
        self.registry = registry
        self.max_steps = max_steps

    async def _validate_and_finalize(
        self,
        query: str,
        answer: str,
        observations: list[str],
        user_profile: str,
    ) -> tuple[str, float]:
        """Critique et épure la réponse finale via l'Agent Validateur."""
        if not observations and len(answer.strip().split()) < 25:
            return answer, 0.0
        t0 = time.perf_counter()
        validated = await validate_draft(
            self.provider, query, answer, observations, user_profile
        )
        return validated, time.perf_counter() - t0

    def _save_turn(self, session_id: str, query: str, answer: str) -> None:
        """Enregistre le tour de dialogue complet dans le stockage de session."""
        self.storage.record_message(session_id, "user", query)
        self.storage.record_message(session_id, "assistant", answer)

    async def _finalize_direct(
        self,
        req: AgentRequest,
        ctx: ExecutionContext,
        action: AgentAction,
        observations: list[str],
        tools_used: list[str],
    ) -> AsyncIterator[AgentEvent]:
        """Finalise et valide la réponse concluante."""
        final_text, el_val = await self._validate_and_finalize(
            req.query, action.final_answer or "", observations, ctx.user_profile
        )
        if el_val > 0.0:
            yield ValidationEvent(content=final_text, elapsed=el_val)
        self._save_turn(req.session_id, req.query, final_text)
        yield DoneEvent(
            response=AgentResponse(
                content=final_text,
                tools_used=tools_used,
                thought=action.thought,
            )
        )

    async def _step_tool(
        self,
        action: AgentAction,
        observations: list[str],
        tools_used: list[str],
        executed_actions: set[tuple[str, str]],
    ) -> AsyncIterator[AgentEvent]:
        """Exécute ou intercepte l'appel d'outil unitaire."""
        val_args = self.registry.validate_arguments(action.tool_name, action.tool_arguments)
        clean_args = {k: v for k, v in val_args.items() if v is not None}
        key = (action.tool_name or "", json.dumps(clean_args, sort_keys=True))
        if key in executed_actions:
            obs = (
                f"Action redondante : `{action.tool_name}` a déjà été exécuté avec ces arguments identiques. "
                "Modifie tes mots-clés ou formule ta conclusion dans 'final_answer'."
            )
            yield ToolResultEvent(tool_name=action.tool_name or "", result=obs)
            observations.append(obs)
            return

        executed_actions.add(key)
        tools_used.append(action.tool_name or "")
        yield ToolCallEvent(tool_name=action.tool_name or "", arguments=clean_args)
        obs = await self.registry.execute_tool(action.tool_name or "", clean_args)
        yield ToolResultEvent(tool_name=action.tool_name or "", result=obs)
        observations.append(f"- Résultat de `{action.tool_name}` : {obs}")

    async def _finalize_max_steps(
        self,
        req: AgentRequest,
        ctx: ExecutionContext,
        observations: list[str],
        tools_used: list[str],
        last_thought: str,
    ) -> AsyncIterator[AgentEvent]:
        """Émet la réponse de fin de quota d'étapes."""
        limit_msg = "Limite maximale d'étapes de raisonnement atteinte sans conclusion."
        final_text, _ = await self._validate_and_finalize(
            req.query, limit_msg, observations, ctx.user_profile
        )
        self._save_turn(req.session_id, req.query, final_text)
        yield DoneEvent(
            response=AgentResponse(
                content=final_text,
                tools_used=tools_used,
                thought=last_thought,
            )
        )

    async def handle_stream(
        self,
        req: AgentRequest,
        ctx: ExecutionContext,
    ) -> AsyncIterator[AgentEvent]:
        """Boucle d'exécution ReAct ordonnée (Thought -> Tool -> Observation)."""
        sys_prompt = build_system_prompt(ctx.user_profile, self.registry.get_prompt_catalog())
        observations: list[str] = []
        tools_used: list[str] = []
        executed_actions: set[tuple[str, str]] = set()
        last_thought: str = ""

        for _ in range(self.max_steps):
            prompt = format_step_prompt(req.query, observations, ctx.history_block)
            t_start = time.perf_counter()
            action = await self.provider.generate_structured(
                prompt=prompt,
                schema=AgentAction,
                system_instruction=sys_prompt,
            )
            last_thought = action.thought
            yield ThoughtEvent(thought=action.thought, elapsed=time.perf_counter() - t_start)

            if action.final_answer and not action.tool_name:
                async for ev in self._finalize_direct(req, ctx, action, observations, tools_used):
                    yield ev
                return

            if action.tool_name:
                async for ev in self._step_tool(action, observations, tools_used, executed_actions):
                    yield ev

        async for ev in self._finalize_max_steps(req, ctx, observations, tools_used, last_thought):
            yield ev
