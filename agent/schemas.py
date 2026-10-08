"""Schémas Pydantic et contrats d'échange pour l'agent Ekko.

Centralise les structures de données d'entrée (AgentRequest),
de sortie (AgentResponse) et de décision ReAct (AgentAction).
"""

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator
from providers.base import LLMProvider


class UserIntent(BaseModel):
    """Classification de l'intention utilisateur en amont de l'orchestration."""

    thought: str = Field(
        default="",
        description="Courte réflexion pour déterminer si la demande nécessite une recherche externe web/scientifique, ou s'il s'agit d'une discussion, rappel ou réponse directe.",
    )
    intent: Literal["chat", "research", "action"] = Field(
        default="chat",
        description="Type d'intention : 'chat' (discussion directe, salutation, rappel), "
        "'research' (veille, SOTA, articles, code), 'action' (todo, fichiers, commandes).",
    )

    @field_validator("intent", mode="before")
    @classmethod
    def normalize_intent(cls, value: Any) -> str:
        """Tolère les dicts de schéma ou variations lexicales."""
        if isinstance(value, dict) and "default" in value:
            value = value["default"]
        if not isinstance(value, str):
            return "chat"
        val = value.lower().strip()
        if val in {"research", "search", "recherche"}:
            return "research"
        if val in {"action", "tool", "tools"}:
            return "action"
        return "chat"


class SearchPlan(BaseModel):
    """Plan de recherche formulé lors du cadrage de la demande."""

    model_config = {"extra": "ignore"}

    is_search_needed: bool = Field(
        default=True,
        description="True si la question nécessite une recherche externe, False pour salutation, conversation ou théorie pure.",
    )
    focus: Literal["academic", "code", "web"] = Field(
        default="academic",
        description="Angle de recherche ('academic' pour arXiv, 'code' pour GitHub, 'web' pour le web technique).",
    )
    queries: list[str] = Field(
        default_factory=list,
        description="1 à 2 requêtes clés en anglais pour les moteurs de recherche académiques ou de code.",
    )
    direct_answer: str | None = Field(
        default=None,
        description="Réponse directe si is_search_needed est False.",
    )

    @field_validator("is_search_needed", mode="before")
    @classmethod
    def sanitize_is_search_needed(cls, value: Any) -> bool:
        """Coerce toute valeur ou fragment de schéma en booléen sûr."""
        if isinstance(value, bool):
            return value
        if isinstance(value, dict):
            if "default" in value:
                return bool(value["default"])
            return True
        if isinstance(value, str):
            return value.strip().lower() not in {"false", "0", "no", "null"}
        return bool(value)

    @field_validator("focus", mode="before")
    @classmethod
    def normalize_focus(cls, value: Any) -> str:
        """Tolère et normalise les variations lexicales générées par les modèles compacts."""
        if isinstance(value, dict) and "default" in value:
            value = value["default"]
        if not isinstance(value, str):
            return "web"
        val = value.lower().strip()
        if val in {"academic", "science", "arxiv", "paper", "papers", "bio", "research"}:
            return "academic"
        if val in {"code", "github", "git", "repo", "repository"}:
            return "code"
        return "web"

    @field_validator("queries", mode="before")
    @classmethod
    def normalize_queries(cls, value: Any) -> list[str]:
        """Assure que les requêtes sont toujours une liste de chaînes valides."""
        if isinstance(value, dict) and "default" in value:
            value = value["default"]
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        if isinstance(value, list):
            return [str(q).strip() for q in value if str(q).strip()]
        return []


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

    @field_validator("tool_arguments_json", mode="before")
    @classmethod
    def sanitize_arguments_json(cls, value: Any) -> str:
        """Normalise les arguments JSON qu'ils soient reçus sous forme de dict, null ou str."""
        if value is None:
            return "{}"
        if isinstance(value, dict):
            import json
            return json.dumps(value)
        if isinstance(value, str):
            clean = value.strip()
            return clean if clean else "{}"
        return "{}"

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


class ThoughtEvent(BaseModel):
    """Événement émis lors d'une étape de réflexion interne."""

    thought: str
    elapsed: float = 0.0


class PlanEvent(BaseModel):
    """Événement émis lors du cadrage de la recherche."""

    focus: str
    queries: list[str] = Field(default_factory=list)
    elapsed: float = 0.0


class RetrievalEvent(BaseModel):
    """Événement émis lors de la collecte et du dédoublonnage des sources."""

    source: str
    count: int
    elapsed: float = 0.0


class ToolCallEvent(BaseModel):
    """Événement émis lors du déclenchement d'un outil externe."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResultEvent(BaseModel):
    """Événement émis lors de la réception du résultat d'un outil."""

    tool_name: str
    result: str


class ValidationEvent(BaseModel):
    """Événement émis lors de la phase de validation critique."""

    content: str
    elapsed: float = 0.0


class StreamChunkEvent(BaseModel):
    """Événement émis lors du streaming continu d'un fragment de texte."""

    delta: str


class DoneEvent(BaseModel):
    """Événement terminal signalant l'achèvement de la tâche."""

    response: AgentResponse


AgentEvent = (
    ThoughtEvent
    | PlanEvent
    | RetrievalEvent
    | ToolCallEvent
    | ToolResultEvent
    | ValidationEvent
    | StreamChunkEvent
    | DoneEvent
)


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
