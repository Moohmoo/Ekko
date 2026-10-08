"""Module agent d'Ekko : orchestration, handlers et persistance."""

from .context import (
    EnvironmentContext,
    ExecutionContext,
    UserProfileContext,
    WorkingMemoryContext,
    build_execution_context,
)
from .engine import EkkoEngine
from .handlers import ActionHandler, BaseHandler, ChatHandler, ResearchHandler
from .router import classify_intent
from .schemas import (
    AgentAction,
    AgentEvent,
    AgentRequest,
    AgentResponse,
    DoneEvent,
    PlanEvent,
    RetrievalEvent,
    StreamChunkEvent,
    ThoughtEvent,
    ToolCallEvent,
    ToolResultEvent,
    ValidationEvent,
)
from .storage import DEFAULT_PROFILE_CONTENT, SessionStorage, load_user_profile

__all__ = [
    "EnvironmentContext",
    "ExecutionContext",
    "UserProfileContext",
    "WorkingMemoryContext",
    "build_execution_context",
    "EkkoEngine",
    "BaseHandler",
    "ChatHandler",
    "ResearchHandler",
    "ActionHandler",
    "SessionStorage",
    "load_user_profile",
    "DEFAULT_PROFILE_CONTENT",
    "classify_intent",
    "AgentRequest",
    "AgentResponse",
    "AgentAction",
    "AgentEvent",
    "PlanEvent",
    "RetrievalEvent",
    "ThoughtEvent",
    "ToolCallEvent",
    "ToolResultEvent",
    "ValidationEvent",
    "StreamChunkEvent",
    "DoneEvent",
]
