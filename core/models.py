"""Modèles de données et contrats d'échange pour l'agent Ekko.

Définit les DTOs découplant l'entrée utilisateur (AgentRequest)
et la sortie métier (AgentResponse) de l'interface graphique.
"""

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Contrat d'entrée représentant la requête utilisateur normalisée."""

    query: str = Field(description="Demande textuelle de l'utilisateur.")
    session_id: str = Field(default="default", description="Identifiant unique de la session.")


class AgentResponse(BaseModel):
    """Contrat de sortie représentant le résultat d'exécution de l'agent."""

    content: str = Field(description="Contenu textuel final formulé par l'agent ou ses outils.")
    tools_used: list[str] = Field(default_factory=list, description="Liste des noms des outils exécutés.")
    thought: str = Field(default="", description="Dernière réflexion ayant conduit à la conclusion.")
