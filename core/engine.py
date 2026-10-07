"""Moteur d'orchestration et boucle centrale ReAct pour Ekko (Brique 2).

Gère le cycle de raisonnement Thought -> Tool Call -> Observation
avec des garde-fous stricts contre les boucles infinies.
"""

import logging
from typing import Any, Callable
from config import Settings
from providers import LLMProvider
from tools.registry import ToolRegistry
from .memory import SQLiteMemory
from .router import AgentAction, decide_action

logger = logging.getLogger("ekko.core.engine")


def build_system_prompt(user_profile: str, tools_catalog: str) -> str:
    """Construit le prompt système global combinant profil utilisateur et catalogue d'outils."""
    return (
        "Tu es Ekko, un assistant personnel d'ingénierie autonome opérant sur la machine locale.\n\n"
        f"### PROFIL UTILISATEUR :\n{user_profile}\n\n"
        f"### OUTILS DISPONIBLES :\n{tools_catalog}\n\n"
        "### RÈGLES DE DÉCISION REACT :\n"
        "- Tu disposes de connaissances générales approfondies en informatique, bioinformatique, code et sciences : "
        "réponds directement via 'final_answer' sans exécuter d'outil pour ces questions.\n"
        "- Pour une salutation, un échange informel ou une question théorique, N'EXÉCUTE AUCUN OUTIL.\n"
        "- N'appelle un outil QUE si la demande exige concrètement son exécution (ex: veille, système).\n"
        "- Si une information requiert des données temps réel externes non couvertes par tes outils "
        "(ex: météo), indique sobrement dans 'final_answer' qu'aucun outil météo n'est disponible.\n"
        "- Produis systématiquement un 'thought' concis explicitant ton analyse.\n"
        "- Si une action technique est requise, fournis 'tool_name' et 'tool_arguments' ('final_answer' = null).\n"
        "- Dès qu'aucun outil n'est requis ou la tâche finie, fournis 'final_answer' ('tool_name' = null).\n"
        "- Réponses directes, précises et sans bavardage.\n"
        "- Formate tes réponses finales en Markdown aéré et structuré (listes à puces, sauts de ligne, "
        "mots-clés en gras) pour une lisibilité optimale dans le terminal."
    )


def format_history_block(history: list[dict[str, str]]) -> str:
    """Formate l'historique conversationnel récent avec garde-fou de taille."""
    if not history:
        return ""
    lines: list[str] = []
    for msg in history:
        role = "Utilisateur" if msg["role"] == "user" else "Ekko"
        content = " ".join(msg["content"].strip().split())
        short_content = content[:250] + "..." if len(content) > 250 else content
        lines.append(f"- {role} : {short_content}")
    return "### HISTORIQUE CONVERSATIONNEL RÉCENT :\n" + "\n".join(lines)


def format_step_prompt(
    user_query: str,
    observations: list[str],
    history_block: str = "",
) -> str:
    """Met en forme l'état de la demande, de l'historique et des observations."""
    sections: list[str] = []
    if history_block:
        sections.append(history_block)
    sections.append(f"Demande utilisateur : {user_query}")
    if observations:
        sections.append("Observations des outils précédents :\n" + "\n".join(observations))
    sections.append("Décide de l'action technique ou formule la réponse finale directement.")
    return "\n\n".join(sections)


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
        user_query: str,
        session_id: str = "default",
        callbacks: dict[str, Any] | None = None,
    ) -> str:
        """Exécute la boucle ReAct jusqu'à résolution ou limite d'itérations."""
        logger.debug("Nouvelle requête (session=%s): '%s'", session_id, user_query)
        cb = callbacks or {}
        system_prompt = build_system_prompt(self.user_profile, self.registry.get_prompt_catalog())
        history = self.memory.get_recent_messages(session_id, limit=6)
        history_block = format_history_block(history)
        observations: list[str] = []

        for step in range(self.max_steps):
            if cb.get("on_thinking_start"):
                cb["on_thinking_start"]()

            prompt = format_step_prompt(user_query, observations, history_block)
            action = await decide_action(self.provider, prompt, system_prompt)
            logger.debug(
                "Étape %d/%d: thought='%s', tool='%s'",
                step + 1, self.max_steps, action.thought, action.tool_name
            )

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
