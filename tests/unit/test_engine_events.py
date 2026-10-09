"""Unit tests for asynchronous event streaming in EkkoEngine."""

import pytest
from typing import Any
from unittest.mock import AsyncMock

from ekko.core.engine import EkkoEngine
from ekko.core.errors import ProviderError
from ekko.core.events import (
    EngineError,
    StepStarted,
    TokenChunk,
    ToolCallCompleted,
    ToolCallStarted,
    TurnCompleted,
)
from ekko.core.models import Message, ModelResponse, ToolCall, ToolResult
from ekko.memory.in_memory import InMemoryMemory


class MockProvider:
    """Mock provider returning predefined responses."""

    def __init__(self, responses: list[ModelResponse]) -> None:
        self.responses = list(responses)
        self.call_history: list[list[Message]] = []

    async def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        self.call_history.append(messages)
        if not self.responses:
            raise RuntimeError("No more mocked responses available")
        return self.responses.pop(0)


class MockFailingProvider:
    """Mock provider that raises a specific exception."""

    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        raise self.exc


class MockToolRegistry:
    """Mock registry exposing mock tools."""

    def __init__(self, tools: dict[str, Any]) -> None:
        self.tools = tools

    def get(self, name: str) -> Any:
        return self.tools.get(name)

    def get_schemas(self) -> list[dict[str, Any]]:
        return [{"type": "function", "function": {"name": name}} for name in self.tools]


class MockTool:
    """Mock tool executing with predefined outcome."""

    def __init__(self, result: ToolResult) -> None:
        self.result = result
        self.executed_with: list[dict[str, Any]] = []

    async def execute(self, **kwargs: Any) -> ToolResult:
        self.executed_with.append(kwargs)
        return self.result


@pytest.mark.asyncio
async def test_run_stream_direct_answer() -> None:
    """Ensure run_stream yields StepStarted, TokenChunk, and TurnCompleted for direct replies."""
    provider = MockProvider(
        [
            ModelResponse(
                content="Bonjour ! Je suis Ekko.",
                model_name="mock-model",
            )
        ]
    )
    memory = InMemoryMemory()
    engine = EkkoEngine(provider=provider, memory=memory)

    events = [event async for event in engine.run_stream("Bonjour", session_id="test_stream")]

    assert len(events) == 3

    assert isinstance(events[0], StepStarted)
    assert events[0].step_index == 1
    assert events[0].max_steps == 5

    assert isinstance(events[1], TokenChunk)
    assert events[1].delta == "Bonjour ! Je suis Ekko."

    assert isinstance(events[2], TurnCompleted)
    assert events[2].content == "Bonjour ! Je suis Ekko."
    assert events[2].total_steps == 1


@pytest.mark.asyncio
async def test_process_message_backward_compatibility() -> None:
    """Verify process_message behaves identically as a façade over run_stream."""
    provider = MockProvider(
        [
            ModelResponse(
                content="Réponse rétrocompatible.",
                model_name="mock-model",
            )
        ]
    )
    memory = InMemoryMemory()
    engine = EkkoEngine(provider=provider, memory=memory)

    result = await engine.process_message("Test", session_id="test_compat")
    assert result == "Réponse rétrocompatible."


@pytest.mark.asyncio
async def test_run_stream_tool_calls_lifecycle() -> None:
    """Verify lifecycle events: StepStarted -> ToolCallStarted -> ToolCallCompleted -> StepStarted -> TurnCompleted."""
    call = ToolCall(id="call_arxiv_1", name="arxiv", arguments={"query": "diffusion"})
    provider = MockProvider(
        [
            ModelResponse(
                content="",
                tool_calls=[call],
                model_name="mock-model",
            ),
            ModelResponse(
                content="Synthèse finale de la recherche.",
                model_name="mock-model",
            ),
        ]
    )
    tool = MockTool(ToolResult(content="Found 1 paper on diffusion models", success=True))
    registry = MockToolRegistry({"arxiv": tool})
    memory = InMemoryMemory()
    engine = EkkoEngine(provider=provider, memory=memory, tools=registry)

    events = [event async for event in engine.run_stream("Cherche sur arxiv", session_id="test_tools")]

    assert len(events) == 6
    assert isinstance(events[0], StepStarted)
    assert events[0].step_index == 1

    assert isinstance(events[1], ToolCallStarted)
    assert events[1].tool_call_id == "call_arxiv_1"
    assert events[1].tool_name == "arxiv"
    assert events[1].arguments == {"query": "diffusion"}

    assert isinstance(events[2], ToolCallCompleted)
    assert events[2].tool_call_id == "call_arxiv_1"
    assert events[2].tool_name == "arxiv"
    assert events[2].success is True
    assert events[2].summary == "Found 1 paper on diffusion models"
    assert events[2].duration_ms is not None
    assert events[2].duration_ms >= 0.0

    assert isinstance(events[3], StepStarted)
    assert events[3].step_index == 2

    assert isinstance(events[4], TokenChunk)
    assert events[4].delta == "Synthèse finale de la recherche."

    assert isinstance(events[5], TurnCompleted)
    assert events[5].content == "Synthèse finale de la recherche."
    assert events[5].total_steps == 2


@pytest.mark.asyncio
async def test_run_stream_circuit_breaker_emits_failure_event() -> None:
    """Verify duplicate tool calls emit ToolCallCompleted with success=False."""
    call1 = ToolCall(id="call_1", name="arxiv", arguments={"query": "diffusion"})
    call2 = ToolCall(id="call_2", name="arxiv", arguments={"query": "diffusion"})

    provider = MockProvider(
        [
            ModelResponse(
                content="",
                tool_calls=[call1, call2],
                model_name="mock-model",
            ),
            ModelResponse(
                content="Terminé après déduplication.",
                model_name="mock-model",
            ),
        ]
    )
    tool = MockTool(ToolResult(content="Résultat 1", success=True))
    registry = MockToolRegistry({"arxiv": tool})
    memory = InMemoryMemory()
    engine = EkkoEngine(provider=provider, memory=memory, tools=registry)

    events = [event async for event in engine.run_stream("Recherche", session_id="test_breaker")]

    completed_events = [e for e in events if isinstance(e, ToolCallCompleted)]
    assert len(completed_events) == 2
    assert completed_events[0].success is True
    assert completed_events[1].success is False
    assert "déjà été exécuté" in completed_events[1].summary


@pytest.mark.asyncio
async def test_run_stream_emits_engine_error_on_provider_unavailable() -> None:
    """Verify ProviderError emits EngineError with ProviderUnavailable and actionable hint."""
    provider = MockFailingProvider(ProviderError("Connection refused by LLM backend"))
    memory = InMemoryMemory()
    engine = EkkoEngine(provider=provider, memory=memory)

    events = [event async for event in engine.run_stream("Bonjour", session_id="test_err_provider")]

    assert len(events) == 2
    assert isinstance(events[0], StepStarted)
    assert isinstance(events[1], EngineError)
    assert events[1].error_type == "ProviderUnavailable"
    assert "Connection refused" in events[1].message
    assert events[1].actionable_hint is not None
    assert "Ollama" in events[1].actionable_hint


@pytest.mark.asyncio
async def test_run_stream_emits_engine_error_on_timeout() -> None:
    """Verify TimeoutError emits EngineError with InfrastructureTimeout."""
    provider = MockFailingProvider(TimeoutError("Read timed out"))
    memory = InMemoryMemory()
    engine = EkkoEngine(provider=provider, memory=memory)

    events = [event async for event in engine.run_stream("Bonjour", session_id="test_err_timeout")]

    assert len(events) == 2
    assert isinstance(events[0], StepStarted)
    assert isinstance(events[1], EngineError)
    assert events[1].error_type == "InfrastructureTimeout"
    assert events[1].actionable_hint is not None


@pytest.mark.asyncio
async def test_run_stream_emits_engine_error_on_invalid_input() -> None:
    """Verify empty user input emits EngineError with InvalidInput."""
    provider = MockProvider([])
    memory = InMemoryMemory()
    engine = EkkoEngine(provider=provider, memory=memory)

    events = [event async for event in engine.run_stream("   ", session_id="test_err_input")]

    assert len(events) == 1
    assert isinstance(events[0], EngineError)
    assert events[0].error_type == "InvalidInput"
    assert events[0].actionable_hint is not None
