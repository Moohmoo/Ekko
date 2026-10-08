"""Interface abstraite de base pour les gestionnaires d'intention."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from agent.context import ExecutionContext
from agent.schemas import AgentEvent, AgentRequest


class BaseHandler(ABC):
    """Interface abstraite commune pour tous les gestionnaires d'intention."""

    @abstractmethod
    def handle_stream(
        self,
        req: AgentRequest,
        ctx: ExecutionContext,
    ) -> AsyncIterator[AgentEvent]:
        """Traite la requête et émet un flux asynchrone d'événements pour le présentateur."""
