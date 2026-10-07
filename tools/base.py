"""Contrat abstrait commun pour tous les outils de l'agent Ekko (Plugin System).

Permet d'ajouter de nouvelles capacités selon l'Open-Closed Principle (OCP)
sans jamais modifier la boucle centrale de l'agent.
"""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel


class EmptyParams(BaseModel):
    """Schéma vide pour les outils ne nécessitant aucun argument."""
    pass


class BaseTool(ABC):
    """Classe de base dont tout outil d'Ekko doit hériter."""

    name: str
    description: str
    parameters_schema: type[BaseModel] = EmptyParams

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """Exécute l'action de l'outil et renvoie un résumé textuel du résultat."""
        pass

    def get_declaration(self) -> dict[str, Any]:
        """Retourne la signature formelle de l'outil pour les modèles LLM."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema.model_json_schema(),
        }
