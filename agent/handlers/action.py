"""Handler pour l'exécution d'actions outillées via un cycle ReAct structuré."""

import json
import time
from collections.abc import AsyncIterator

from agent.context import ExecutionContext
from agent.prompts import build_system_prompt, format_step_prompt
from agent.schemas import (
    AgentAction,
    AgentEvent,
    AgentRequest,
    AgentResponse,
    DoneEvent,
    ThoughtEvent,
    ToolCallEvent,
    ToolResultEvent,
    ValidationEvent,
)
from agent.storage import SessionStorage
from agent.validator import validate_draft
from providers import LLMProvider
from tools.registry import ToolRegistry
from .base import BaseHandler


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
        if not observations:
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
        raw_answer = action.final_answer or (observations[-1] if observations else "")
        final_text, el_val = await self._validate_and_finalize(
            req.query, raw_answer, observations, ctx.user_profile
        )
        safe_answer = final_text.strip() or raw_answer or "Tâche achevée sans conclusion textuelle."
        if el_val > 0.0:
            yield ValidationEvent(content=safe_answer, elapsed=el_val)
        self._save_turn(req.session_id, req.query, safe_answer)
        yield DoneEvent(
            response=AgentResponse(
                content=safe_answer,
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
        key = (action.tool_name or "", json.dumps(clean_args, sort_keys=True, default=str))
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
        safe_answer = final_text.strip() or limit_msg
        self._save_turn(req.session_id, req.query, safe_answer)
        yield DoneEvent(
            response=AgentResponse(
                content=safe_answer,
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
            elif not action.final_answer:
                obs = "Format invalide : Spécifie soit un 'tool_name' à appeler, soit ta conclusion dans 'final_answer'."
                observations.append(obs)
                yield ToolResultEvent(tool_name="system", result=obs)

        async for ev in self._finalize_max_steps(req, ctx, observations, tools_used, last_thought):
            yield ev
