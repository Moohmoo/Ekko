"""Moteur d'orchestration et boucle centrale ReAct pour Ekko.

Gère le cycle de raisonnement Thought -> Tool Call -> Observation
avec des garde-fous stricts contre les boucles infinies.
"""

import logging
from typing import Any
from config import Settings
from providers import LLMProvider
from tools.registry import ToolRegistry
from .memory import SQLiteMemory
from .prompts import build_system_prompt, format_history_block, format_step_prompt
from .schemas import AgentAction, AgentRequest, AgentResponse, decide_action

logger = logging.getLogger("ekko.agent.engine")


def normalize_request(request: AgentRequest | str, session_id: str = "default") -> AgentRequest:
    """Normalise l'entrée en un contrat AgentRequest immuable."""
    if isinstance(request, AgentRequest):
        return request
    return AgentRequest(query=request.strip(), session_id=session_id)


class EkkoEngine:
    """Moteur central d'exécution d'Ekko."""

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

    async def _handle_tool_step(
        self,
        action: AgentAction,
        callbacks: dict[str, Any],
    ) -> str:
        """Exécute un outil, invoque les callbacks graphiques et journalise l'action."""
        tool_name = action.tool_name or ""
        logger.debug("Exécution outil '%s' avec args=%s", tool_name, action.tool_arguments)
        if callbacks.get("on_tool_call"):
            callbacks["on_tool_call"](tool_name, action.tool_arguments)

        obs = await self.registry.execute_tool(tool_name, action.tool_arguments)
        logger.debug("Résultat outil '%s': %s", tool_name, obs[:150])

        if callbacks.get("on_tool_result"):
            callbacks["on_tool_result"](tool_name, obs)

        self.memory.record_task_run(tool_name, "success", obs[:150])
        return f"- Résultat de `{tool_name}` : {obs}"

    async def run(
        self,
        request: AgentRequest | str,
        session_id: str = "default",
        callbacks: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """Exécute la boucle ReAct jusqu'à résolution ou limite d'itérations."""
        req = normalize_request(request, session_id)
        logger.debug("Nouvelle requête (session=%s): '%s'", req.session_id, req.query)
        cb = callbacks or {}
        system_prompt = build_system_prompt(self.user_profile, self.registry.get_prompt_catalog())
        history = self.memory.get_recent_messages(req.session_id, limit=6)
        history_block = format_history_block(history)
        observations: list[str] = []
        tools_used: list[str] = []
        last_thought: str = ""

        for step in range(self.max_steps):
            if cb.get("on_thinking_start"):
                cb["on_thinking_start"]()

            prompt = format_step_prompt(req.query, observations, history_block)
            action = await decide_action(self.provider, prompt, system_prompt)
            last_thought = action.thought
            logger.debug(
                "Étape %d/%d: thought='%s', tool='%s'",
                step + 1, self.max_steps, action.thought, action.tool_name,
            )

            if cb.get("on_thought") and action.thought:
                cb["on_thought"](action.thought)

            if action.final_answer and not action.tool_name:
                self.memory.record_message(req.session_id, "user", req.query)
                self.memory.record_message(req.session_id, "assistant", action.final_answer)
                return AgentResponse(
                    content=action.final_answer,
                    tools_used=tools_used,
                    thought=action.thought,
                )

            if action.tool_name:
                tools_used.append(action.tool_name)
                obs = await self._handle_tool_step(action, cb)
                observations.append(obs)

        return AgentResponse(
            content="Limite maximale d'étapes de raisonnement atteinte sans conclusion.",
            tools_used=tools_used,
            thought=last_thought,
        )
