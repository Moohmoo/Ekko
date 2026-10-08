"""Moteur d'orchestration et boucle centrale ReAct pour Ekko.

Gère le cycle de raisonnement Thought -> Tool Call -> Observation
suivi de la phase de validation critique (Pattern Enquêteur - Critique).
"""

import json
import time
from collections.abc import AsyncIterator
from typing import Any
from config import Settings
from core import Logger
from providers import LLMProvider
from tools.registry import ToolRegistry
from .memory import SQLiteMemory
from .prompts import build_system_prompt, format_history_block, format_step_prompt
from .schemas import (
    AgentAction,
    AgentEvent,
    AgentRequest,
    AgentResponse,
    DoneEvent,
    ThoughtEvent,
    ToolCallEvent,
    ToolResultEvent,
    ValidationEvent,
    decide_action,
)
from .validator import validate_draft

logger = Logger("ekko.agent.engine")


def normalize_request(request: AgentRequest | str, session_id: str = "default") -> AgentRequest:
    """Normalise l'entrée en un contrat AgentRequest immuable."""
    if isinstance(request, AgentRequest):
        return request
    return AgentRequest(query=request.strip(), session_id=session_id)


class EkkoEngine:
    """Moteur central d'exécution d'Ekko émettant un flux d'événements ReAct purs."""

    def __init__(
        self,
        settings: Settings,
        provider: LLMProvider,
        registry: ToolRegistry,
        memory: SQLiteMemory,
        user_profile: str,
        max_steps: int = 5,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.registry = registry
        self.memory = memory
        self.user_profile = user_profile
        self.max_steps = max_steps

    async def _execute_tool(self, tool_name: str, args: dict[str, Any]) -> str:
        """Exécute un outil du registre et persiste le run dans la mémoire SQLite."""
        obs = await self.registry.execute_tool(tool_name, args)
        self.memory.record_task_run(tool_name, "success", obs[:150])
        return obs

    def _save_final_turn(self, session_id: str, query: str, answer: str) -> None:
        """Enregistre le tour de dialogue complet dans la mémoire SQLite."""
        self.memory.record_message(session_id, "user", query)
        self.memory.record_message(session_id, "assistant", answer)

    async def _validate_and_finalize(
        self,
        query: str,
        answer: str,
        observations: list[str],
    ) -> tuple[str, float]:
        """Critique et épure la réponse finale via l'Agent Validateur."""
        if not observations and len(answer.strip().split()) < 25:
            return answer, 0.0
        t0 = time.perf_counter()
        validated = await validate_draft(
            self.provider, query, answer, observations, self.user_profile
        )
        return validated, time.perf_counter() - t0

    async def run_stream(
        self,
        request: AgentRequest | str,
        session_id: str = "default",
    ) -> AsyncIterator[AgentEvent]:
        """Exécute la boucle ReAct puis la validation en émettant un flux d'événements typés."""
        req = normalize_request(request, session_id)
        sys_prompt = build_system_prompt(self.user_profile, self.registry.get_prompt_catalog())
        history_block = format_history_block(self.memory.get_recent_messages(req.session_id, limit=6))
        observations: list[str] = []
        tools_used: list[str] = []
        executed_actions: set[tuple[str, str]] = set()
        last_thought: str = ""

        for _ in range(self.max_steps):
            prompt = format_step_prompt(req.query, observations, history_block)
            t_start = time.perf_counter()
            action = await decide_action(self.provider, prompt, sys_prompt)
            last_thought = action.thought
            yield ThoughtEvent(thought=action.thought, elapsed=time.perf_counter() - t_start)

            if action.final_answer and not action.tool_name:
                final_text, el_val = await self._validate_and_finalize(
                    req.query, action.final_answer, observations
                )
                if el_val > 0.0:
                    yield ValidationEvent(content=final_text, elapsed=el_val)
                self._save_final_turn(req.session_id, req.query, final_text)
                yield DoneEvent(
                    response=AgentResponse(
                        content=final_text,
                        tools_used=tools_used,
                        thought=action.thought,
                    )
                )
                return

            if action.tool_name:
                validated_args = self.registry.validate_arguments(action.tool_name, action.tool_arguments)
                clean_args = {k: v for k, v in validated_args.items() if v is not None}
                action_key = (action.tool_name, json.dumps(clean_args, sort_keys=True))
                if action_key in executed_actions:
                    logger.warning("Action redondante interceptée : %s", action_key)
                    obs = (
                        f"Action redondante : `{action.tool_name}` a déjà été exécuté avec ces arguments identiques. "
                        "Modifie tes mots-clés ou formule ta conclusion dans 'final_answer'."
                    )
                    yield ToolResultEvent(tool_name=action.tool_name, result=obs)
                    observations.append(obs)
                else:
                    executed_actions.add(action_key)
                    tools_used.append(action.tool_name)
                    yield ToolCallEvent(tool_name=action.tool_name, arguments=clean_args)
                    obs = await self._execute_tool(action.tool_name, clean_args)
                    yield ToolResultEvent(tool_name=action.tool_name, result=obs)
                    observations.append(f"- Résultat de `{action.tool_name}` : {obs}")

        limit_msg = "Limite maximale d'étapes de raisonnement atteinte sans conclusion."
        final_text, _ = await self._validate_and_finalize(req.query, limit_msg, observations)
        yield DoneEvent(response=AgentResponse(content=final_text, tools_used=tools_used, thought=last_thought))
