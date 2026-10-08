"""Package agent définissant le domaine cognitif d'Ekko."""

from .engine import EkkoEngine
from .memory import SQLiteMemory, load_user_profile
from .prompts import build_system_prompt, format_history_block, format_step_prompt
from .schemas import (
    AgentAction,
    AgentEvent,
    AgentRequest,
    AgentResponse,
    DoneEvent,
    ThoughtEvent,
    ToolCallEvent,
    ToolResultEvent,
    ValidationEvent,
    decide_action,
)
from .validator import validate_draft

__all__ = [
    "EkkoEngine",
    "SQLiteMemory",
    "load_user_profile",
    "AgentRequest",
    "AgentResponse",
    "AgentAction",
    "AgentEvent",
    "ThoughtEvent",
    "ToolCallEvent",
    "ToolResultEvent",
    "ValidationEvent",
    "DoneEvent",
    "decide_action",
    "validate_draft",
    "build_system_prompt",
    "format_history_block",
    "format_step_prompt",
]
