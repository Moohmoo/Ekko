"""Routeur LLM agnostique pour l'agent Ekko (Brique 1).

Définit le schéma d'action ReAct et coordonne les décisions du modèle
quel que soit le fournisseur (Gemini ou modèle local Ollama).
"""

from typing import Any
from pydantic import BaseModel, Field, field_validator
from providers import LLMProvider


class AgentAction(BaseModel):
    """Structure de décision émise par le modèle à chaque étape de la boucle ReAct."""

    thought: str = Field(
        description="Réflexion technique, analyse de la situation et stratégie de résolution.",
    )
    tool_name: str | None = Field(
        default=None,
        description="Nom de l'outil à exécuter parmi les outils disponibles, ou null si la réponse est prête.",
    )
    tool_arguments_json: str = Field(
        default="{}",
        description="Chaîne JSON des arguments de l'outil (ex: '{\"force\": true}' ou '{}').",
    )
    final_answer: str | None = Field(
        default=None,
        description="Message final clair et direct à l'utilisateur lorsque la tâche est achevée.",
    )

    @field_validator("tool_name", mode="after")
    @classmethod
    def sanitize_tool_name(cls, value: str | None) -> str | None:
        """Nettoie les chaînes sentinelles 'null' ou 'none' générées par les LLMs."""
        if not value or value.strip().lower() in {"none", "null", "false", "undefined", ""}:
            return None
        return value.strip()

    @property
    def tool_arguments(self) -> dict[str, Any]:
        """Convertit de manière sûre la chaîne JSON d'arguments en dictionnaire."""
        if not self.tool_arguments_json:
            return {}
        try:
            import json
            data = json.loads(self.tool_arguments_json)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}


async def decide_action(
    provider: LLMProvider,
    prompt: str,
    system_prompt: str,
) -> AgentAction:
    """Interroge le LLM et extrait une action de décision typée et validée."""
    return await provider.generate_structured(
        prompt=prompt,
        schema=AgentAction,
        system_instruction=system_prompt,
    )
