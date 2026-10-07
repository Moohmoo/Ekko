"""Schémas Pydantic et contrats d'échange pour l'agent Ekko.

Centralise les structures de données d'entrée (AgentRequest),
de sortie (AgentResponse) et de décision ReAct (AgentAction).
"""

from typing import Any
from pydantic import BaseModel, Field, field_validator
from providers.base import LLMProvider


class AgentRequest(BaseModel):
    """Contrat d'entrée représentant la requête utilisateur normalisée."""

    query: str = Field(description="Demande textuelle de l'utilisateur.")
    session_id: str = Field(default="default", description="Identifiant unique de la session.")


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


class AgentResponse(BaseModel):
    """Contrat de sortie représentant le résultat d'exécution de l'agent."""

    content: str = Field(description="Contenu textuel final formulé par l'agent ou ses outils.")
    tools_used: list[str] = Field(default_factory=list, description="Liste des noms des outils exécutés.")
    thought: str = Field(default="", description="Dernière réflexion ayant conduit à la conclusion.")


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
