"""Moteur d'orchestration et boucle centrale ReAct pour Ekko (Brique 2).

Gère le cycle de raisonnement Thought -> Tool Call -> Observation
avec des garde-fous stricts contre les boucles infinies.
"""

from typing import Any, Callable
from config import Settings
from providers import LLMProvider
from tools.registry import ToolRegistry
from .memory import SQLiteMemory
from .router import AgentAction, decide_action


def build_system_prompt(user_profile: str, tools_catalog: str) -> str:
    """Construit le prompt système global combinant profil utilisateur et catalogue d'outils."""
    return (
        "Tu es Ekko, un assistant personnel d'ingénierie autonome opérant sur la machine locale.\n\n"
        f"### PROFIL UTILISATEUR :\n{user_profile}\n\n"
        f"### OUTILS DISPONIBLES :\n{tools_catalog}\n\n"
        "### RÈGLES DE DÉCISION REACT :\n"
        "- Pour une salutation ('salut', 'bonjour'), un échange informel ou une question sans action "
        "technique requise, N'EXÉCUTE AUCUN OUTIL : réponds immédiatement via 'final_answer'.\n"
        "- N'appelle un outil QUE si la demande exige concrètement son exécution.\n"
        "- Produis systématiquement un 'thought' concis explicitant ton analyse.\n"
        "- Si une action technique est requise, fournis 'tool_name' et 'tool_arguments' ('final_answer' = null).\n"
        "- Dès qu'aucun outil n'est requis ou la tâche finie, fournis 'final_answer' ('tool_name' = null).\n"
        "- Réponses directes, synthétiques et factuelles."
    )


def format_step_prompt(user_query: str, observations: list[str]) -> str:
    """Met en forme l'état de la demande et des observations accumulées."""
    prompt = f"Demande utilisateur : {user_query}\n"
    if observations:
        prompt += "\nObservations des outils précédents :\n"
        prompt += "\n".join(observations) + "\n"
    prompt += "\nDécide de l'action technique ou formule la réponse finale directement."
    return prompt


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
        if callbacks.get("on_tool_call"):
            callbacks["on_tool_call"](tool_name, action.tool_arguments)

        obs = await self.registry.execute_tool(tool_name, action.tool_arguments)

        if callbacks.get("on_tool_result"):
            callbacks["on_tool_result"](tool_name, obs)

        self.memory.record_task_run(tool_name, "success", obs[:150])
        return f"- Résultat de `{tool_name}` : {obs}"

    async def run(
        self,
        user_query: str,
        session_id: str = "default",
        callbacks: dict[str, Any] | None = None,
    ) -> str:
        """Exécute la boucle ReAct jusqu'à résolution ou limite d'itérations."""
        cb = callbacks or {}
        system_prompt = build_system_prompt(self.user_profile, self.registry.get_prompt_catalog())
        observations: list[str] = []

        for _ in range(self.max_steps):
            if cb.get("on_thinking_start"):
                cb["on_thinking_start"]()

            prompt = format_step_prompt(user_query, observations)
            action = await decide_action(self.provider, prompt, system_prompt)

            if cb.get("on_thought") and action.thought:
                cb["on_thought"](action.thought)

            if action.final_answer and not action.tool_name:
                self.memory.record_message(session_id, "user", user_query)
                self.memory.record_message(session_id, "assistant", action.final_answer)
                return action.final_answer

            if action.tool_name:
                obs = await self._handle_tool_step(action, cb)
                observations.append(obs)

        return "Limite maximale d'étapes de raisonnement atteinte sans conclusion."
