"""Moteur d'orchestration central pour Ekko (Pattern Dispatcher).

Reçoit la requête, instancie l'ExecutionContext immuable,
classifie l'intention via le Routeur et délègue au Handler spécialisé.
"""

from collections.abc import AsyncIterator
from config import Settings
from core import Logger
from providers import LLMProvider
from tools.registry import ToolRegistry
from .context import ExecutionContext, build_execution_context
from .handlers import ActionHandler, BaseHandler, ChatHandler, ResearchHandler
from .router import classify_intent
from .schemas import AgentEvent, AgentRequest, AgentResponse
from .storage import SessionStorage

logger = Logger("ekko.agent.engine")


def normalize_request(request: AgentRequest | str, session_id: str = "default") -> AgentRequest:
    """Normalise l'entrée en contrat AgentRequest immuable."""
    if isinstance(request, AgentRequest):
        return request
    return AgentRequest(query=request.strip(), session_id=session_id)


class EkkoEngine:
    """Orchestrateur central sobre déléguant l'exécution aux Handlers d'intention."""

    def __init__(
        self,
        settings: Settings,
        provider: LLMProvider,
        registry: ToolRegistry,
        storage: SessionStorage,
        user_profile: str = "",
        max_steps: int = 5,
        use_pipeline: bool = False,
        handlers: dict[str, BaseHandler] | None = None,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.registry = registry
        self.storage = storage
        self.user_profile = user_profile
        self.max_steps = max_steps
        self.use_pipeline = use_pipeline
        self.handlers = handlers or self._default_handlers()

    def _default_handlers(self) -> dict[str, BaseHandler]:
        """Instancie les gestionnaires par défaut pour chaque intention."""
        search_tool = self.registry.get_tool("search")
        return {
            "chat": ChatHandler(self.provider, self.storage),
            "research": ResearchHandler(self.provider, self.storage, search_tool),
            "action": ActionHandler(self.provider, self.storage, self.registry, max_steps=self.max_steps),
        }

    async def run_stream(
        self,
        request: AgentRequest | str,
        session_id: str = "default",
    ) -> AsyncIterator[AgentEvent]:
        """Point d'entrée unique : résout le contexte et dispatche vers le handler approprié."""
        req = normalize_request(request, session_id)
        ctx = build_execution_context(self.storage, req.session_id, self.user_profile)
        if not self.handlers:
            raise RuntimeError("Aucun gestionnaire d'intention disponible dans le moteur.")
        if not self.use_pipeline:
            handler = self.handlers.get("action") or next(iter(self.handlers.values()))
        else:
            intent = await classify_intent(self.provider, req.query, ctx=ctx)
            handler = self.handlers.get(intent) or self.handlers.get("chat") or next(iter(self.handlers.values()))
        async for event in handler.handle_stream(req, ctx):
            yield event
