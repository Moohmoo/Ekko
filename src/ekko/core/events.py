"""Typed domain events emitted by the orchestrator engine."""

from typing import Annotated, Any, Literal, Union
from pydantic import BaseModel, Field


class BaseEngineEvent(BaseModel):
    """Base class for all immutable domain engine events."""

    model_config = {"frozen": True}


class StepStarted(BaseEngineEvent):
    """Emitted at the beginning of each ReAct iteration loop."""

    type: Literal["step_started"] = "step_started"
    step_index: int = Field(..., description="Current iteration step (1-indexed)")
    max_steps: int = Field(..., description="Maximum allowed iteration steps")


class ToolCallStarted(BaseEngineEvent):
    """Emitted immediately before an external tool execution starts."""

    type: Literal["tool_call_started"] = "tool_call_started"
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallCompleted(BaseEngineEvent):
    """Emitted immediately after a tool execution finishes."""

    type: Literal["tool_call_completed"] = "tool_call_completed"
    tool_call_id: str
    tool_name: str
    success: bool
    summary: str = Field(..., description="Concise or human-readable outcome summary")
    duration_ms: float | None = Field(default=None, description="Execution duration in ms")


class TokenChunk(BaseEngineEvent):
    """Emitted when the engine streams text tokens or chunks incrementally."""

    type: Literal["token_chunk"] = "token_chunk"
    delta: str = Field(..., description="Incremental text fragment")


class TurnCompleted(BaseEngineEvent):
    """Emitted when the conversational turn terminates with a final answer."""

    type: Literal["turn_completed"] = "turn_completed"
    content: str = Field(..., description="Full final synthesized response")
    total_steps: int = Field(..., description="Total iteration steps executed in this turn")


class EngineError(BaseEngineEvent):
    """Emitted when an unrecoverable or infrastructure error occurs."""

    type: Literal["engine_error"] = "engine_error"
    error_type: str = Field(..., description="Machine-readable error classification")
    message: str = Field(..., description="Technical explanation for logs")
    actionable_hint: str | None = Field(
        default=None,
        description="Clear, human-friendly guidance to resolve the issue",
    )


EngineEvent = Annotated[
    Union[
        StepStarted,
        ToolCallStarted,
        ToolCallCompleted,
        TokenChunk,
        TurnCompleted,
        EngineError,
    ],
    Field(discriminator="type"),
]
