"""Interface abstraite commune pour les fournisseurs de modèles LLM.

Permet d'interchanger les implémentations (Gemini officiel vs modèles locaux)
selon le principe de responsabilité unique et l'inversion de dépendance (SOLID).
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Contrat commun pour l'interrogation d'un modèle de langage."""

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_instruction: str = "",
    ) -> T:
        """Génère une réponse garantie conforme au schéma Pydantic fourni."""
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> str:
        """Génère une réponse textuelle brute (par exemple du Markdown)."""
        pass

    @abstractmethod
    async def stream_text(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> AsyncIterator[str]:
        """Génère une réponse textuelle en flux continu (streaming de tokens)."""
        pass
