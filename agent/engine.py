"""Moteur d'orchestration et boucle centrale ReAct pour Ekko.

Gère le cycle de raisonnement Thought -> Tool Call -> Observation
avec des garde-fous stricts contre les boucles infinies.
"""

import logging
import time
from collections.abc import AsyncIterator
from typing import Any
from config import Settings
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
    decide_action,
)

logger = logging.getLogger("ekko.agent.engine")


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

    def _dispatch_legacy_callback(self, event: AgentEvent, cb: dict[str, Any]) -> None:
        """Achemine les événements vers les anciens callbacks pour rétrocompatibilité."""
        if isinstance(event, ThoughtEvent) and cb.get("on_thought"):
            cb["on_thought"](event.thought)
        elif isinstance(event, ToolCallEvent) and cb.get("on_tool_call"):
            cb["on_tool_call"](event.tool_name, event.arguments)
        elif isinstance(event, ToolResultEvent) and cb.get("on_tool_result"):
            cb["on_tool_result"](event.tool_name, event.result)

    async def run_stream(
        self,
        request: AgentRequest | str,
        session_id: str = "default",
    ) -> AsyncIterator[AgentEvent]:
        """Exécute la boucle ReAct en émettant un flux d'événements typés."""
        req = normalize_request(request, session_id)
        sys_prompt = build_system_prompt(self.user_profile, self.registry.get_prompt_catalog())
        history_block = format_history_block(self.memory.get_recent_messages(req.session_id, limit=6))
        observations: list[str] = []
        tools_used: list[str] = []
        executed_actions: set[tuple[str, str]] = set()
        last_thought: str = ""

        for step in range(self.max_steps):
            prompt = format_step_prompt(req.query, observations, history_block)
            t_start = time.perf_counter()
            action = await decide_action(self.provider, prompt, sys_prompt)
            last_thought = action.thought
            yield ThoughtEvent(thought=action.thought, elapsed=time.perf_counter() - t_start)

            if action.final_answer and not action.tool_name:
                self._save_final_turn(req.session_id, req.query, action.final_answer)
                yield DoneEvent(
                    response=AgentResponse(
                        content=action.final_answer,
                        tools_used=tools_used,
                        thought=action.thought,
                    )
                )
                return

            if action.tool_name:
                action_key = (action.tool_name, action.tool_arguments_json.strip())
                if action_key in executed_actions:
                    logger.warning("Action redondante interceptée : %s", action_key)
                    obs = (
                        f"Action redondante : `{action.tool_name}` a déjà été exécuté avec ces arguments. "
                        "Tu ne dois pas le réexécuter. Conclus obligatoirement dans 'final_answer'."
                    )
                    yield ToolResultEvent(tool_name=action.tool_name, result=obs)
                    observations.append(obs)
                else:
                    executed_actions.add(action_key)
                    tools_used.append(action.tool_name)
                    yield ToolCallEvent(tool_name=action.tool_name, arguments=action.tool_arguments)
                    obs = await self._execute_tool(action.tool_name, action.tool_arguments)
                    yield ToolResultEvent(tool_name=action.tool_name, result=obs)
                    observations.append(f"- Résultat de `{action.tool_name}` : {obs}")

        limit_msg = "Limite maximale d'étapes de raisonnement atteinte sans conclusion."
        yield DoneEvent(response=AgentResponse(content=limit_msg, tools_used=tools_used, thought=last_thought))

    async def run(
        self,
        request: AgentRequest | str,
        session_id: str = "default",
        callbacks: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """Exécute la boucle ReAct de manière bloquante (rétrocompatible)."""
        cb = callbacks or {}
        async for event in self.run_stream(request, session_id):
            self._dispatch_legacy_callback(event, cb)
            if isinstance(event, DoneEvent):
                return event.response
        return AgentResponse(content="Erreur : flux d'événements interrompu sans conclusion.")
