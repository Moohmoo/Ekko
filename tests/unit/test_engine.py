"""Unit tests for the core conversation engine."""

from unittest.mock import AsyncMock
import pytest

from ekko.core.engine import EkkoEngine
from ekko.core.models import Message, ModelResponse
from ekko.memory.in_memory import InMemoryMemory


@pytest.mark.asyncio
async def test_engine_process_single_turn() -> None:
    """Ensure engine persists turn, sends prompt + history to provider, and returns reply."""
    mock_provider = AsyncMock()
    mock_provider.generate.return_value = ModelResponse(
        content="I am Ekko.",
        model_name="mock-model",
    )
    memory = InMemoryMemory()
    engine = EkkoEngine(
        provider=mock_provider,
        memory=memory,
        system_prompt="Custom system guardrail.",
    )

    reply = await engine.process_message("Who are you?", session_id="s1")

    assert reply == "I am Ekko."

    # Check that provider was called with system prompt followed by user turn
    call_args = mock_provider.generate.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0] == Message(role="system", content="Custom system guardrail.")
    assert call_args[1] == Message(role="user", content="Who are you?")

    # Check memory persistence
    messages = await memory.get_messages("s1")
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Who are you?"
    assert messages[1].role == "assistant"
    assert messages[1].content == "I am Ekko."


@pytest.mark.asyncio
async def test_engine_maintains_multi_turn_context() -> None:
    """Ensure subsequent turns include previous conversation history."""
    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(content="First reply", model_name="mock"),
        ModelResponse(content="Second reply", model_name="mock"),
    ]
    memory = InMemoryMemory()
    engine = EkkoEngine(provider=mock_provider, memory=memory)

    await engine.process_message("Turn 1", session_id="session-x")
    await engine.process_message("Turn 2", session_id="session-x")

    second_call_messages = mock_provider.generate.call_args_list[1][0][0]
    # system + user1 + asst1 + user2
    assert len(second_call_messages) == 4
    assert second_call_messages[1].content == "Turn 1"
    assert second_call_messages[2].content == "First reply"
    assert second_call_messages[3].content == "Turn 2"


@pytest.mark.asyncio
async def test_engine_rejects_empty_input() -> None:
    """Ensure blank inputs are rejected before hitting memory or provider."""
    mock_provider = AsyncMock()
    engine = EkkoEngine(provider=mock_provider, memory=InMemoryMemory())

    with pytest.raises(ValueError):
        await engine.process_message("   ")

    mock_provider.generate.assert_not_called()


@pytest.mark.asyncio
async def test_engine_executes_tool_call_and_returns_final_response() -> None:
    """Ensure engine executes tool, stores role='tool' message, and gets final reply."""
    from pydantic import BaseModel
    from ekko.core.models import ToolCall, ToolResult
    from ekko.tools.base import BaseTool
    from ekko.tools.registry import ToolRegistry

    class CalcArgs(BaseModel):
        a: int
        b: int

    class MockCalc(BaseTool):
        name: str = "calculator"
        description: str = "Adds numbers"
        args_schema: type[BaseModel] = CalcArgs

        async def _run(self, a: int, b: int) -> ToolResult:
            return ToolResult(content=str(a + b), success=True)

    registry = ToolRegistry()
    registry.register(MockCalc())

    tool_call = ToolCall(id="call_1", name="calculator", arguments={"a": 10, "b": 20})
    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(content="", model_name="mock", tool_calls=[tool_call]),
        ModelResponse(content="The answer is 30.", model_name="mock"),
    ]

    memory = InMemoryMemory()
    engine = EkkoEngine(provider=mock_provider, memory=memory, tools=registry)

    reply = await engine.process_message("Compute 10 + 20", session_id="s_tool")

    assert reply == "The answer is 30."

    messages = await memory.get_messages("s_tool")
    assert len(messages) == 4
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert len(messages[1].tool_calls) == 1
    assert messages[2].role == "tool"
    assert messages[2].content == "30"
    assert messages[2].tool_call_id == "call_1"
    assert messages[3].role == "assistant"
    assert messages[3].content == "The answer is 30."


@pytest.mark.asyncio
async def test_engine_handles_unknown_tool_gracefully() -> None:
    """Ensure engine reports error when LLM invokes an unregistered tool."""
    from ekko.core.models import ToolCall
    from ekko.tools.registry import ToolRegistry

    registry = ToolRegistry()
    tool_call = ToolCall(id="c_err", name="ghost_tool", arguments={})
    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(content="", model_name="mock", tool_calls=[tool_call]),
        ModelResponse(content="Sorry, tool not found.", model_name="mock"),
    ]

    memory = InMemoryMemory()
    engine = EkkoEngine(provider=mock_provider, memory=memory, tools=registry)

    reply = await engine.process_message("Call ghost", session_id="s_ghost")

    assert reply == "Sorry, tool not found."
    messages = await memory.get_messages("s_ghost")
    assert messages[2].role == "tool"
    assert "not found" in messages[2].content


@pytest.mark.asyncio
async def test_engine_stops_at_max_iterations() -> None:
    """Ensure ReAct loop terminates when max_iterations ceiling is hit."""
    from ekko.core.models import ToolCall
    from ekko.tools.registry import ToolRegistry

    registry = ToolRegistry()
    loop_call = ToolCall(id="loop", name="dummy", arguments={})
    mock_provider = AsyncMock()
    mock_provider.generate.return_value = ModelResponse(
        content="",
        model_name="mock",
        tool_calls=[loop_call],
    )

    memory = InMemoryMemory()
    engine = EkkoEngine(
        provider=mock_provider,
        memory=memory,
        tools=registry,
        max_iterations=2,
    )

    reply = await engine.process_message("Loop forever", session_id="s_loop")

    assert "Max iterations" in reply
    assert mock_provider.generate.await_count == 2


@pytest.mark.asyncio
async def test_engine_executes_multiple_tool_calls_sequentially() -> None:
    """Ensure multiple tool calls in a single turn are executed sequentially."""
    from pydantic import BaseModel
    from ekko.core.models import ToolCall, ToolResult
    from ekko.tools.base import BaseTool
    from ekko.tools.registry import ToolRegistry

    order: list[str] = []

    class DummyArgs(BaseModel):
        tag: str

    class StepTool(BaseTool):
        name: str = "step_tool"
        description: str = "Records step"
        args_schema: type[BaseModel] = DummyArgs

        async def _run(self, tag: str) -> ToolResult:
            order.append(tag)
            return ToolResult(content=f"Step {tag} done", success=True)

    registry = ToolRegistry()
    registry.register(StepTool())

    calls = [
        ToolCall(id="tc_1", name="step_tool", arguments={"tag": "first"}),
        ToolCall(id="tc_2", name="step_tool", arguments={"tag": "second"}),
    ]
    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(content="", model_name="mock", tool_calls=calls),
        ModelResponse(content="All steps executed.", model_name="mock"),
    ]

    memory = InMemoryMemory()
    engine = EkkoEngine(provider=mock_provider, memory=memory, tools=registry)

    reply = await engine.process_message("Execute steps", session_id="s_multi")

    assert reply == "All steps executed."
    assert order == ["first", "second"]
    messages = await memory.get_messages("s_multi")
    assert len(messages) == 5  # user, asst(2 calls), tool1, tool2, asst(final)
    assert messages[2].tool_call_id == "tc_1"
    assert messages[3].tool_call_id == "tc_2"


@pytest.mark.asyncio
async def test_engine_circuit_breaker_intercepts_duplicate_tool_call() -> None:
    """Ensure engine circuit-breaker catches identical tool calls in the same turn."""
    from pydantic import BaseModel
    from ekko.core.models import ToolCall, ToolResult
    from ekko.tools.base import BaseTool
    from ekko.tools.registry import ToolRegistry

    call_count = 0

    class ProbeArgs(BaseModel):
        target: str

    class ProbeTool(BaseTool):
        name: str = "probe_tool"
        description: str = "Probes a target"
        args_schema: type[BaseModel] = ProbeArgs

        async def _run(self, target: str) -> ToolResult:
            nonlocal call_count
            call_count += 1
            return ToolResult(content=f"Probe result for {target}", success=True)

    registry = ToolRegistry()
    registry.register(ProbeTool())

    duplicate_call = ToolCall(id="c_dup", name="probe_tool", arguments={"target": "same_url"})

    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        # Turn 1: LLM calls probe_tool
        ModelResponse(content="", model_name="mock", tool_calls=[ToolCall(id="c_1", name="probe_tool", arguments={"target": "same_url"})]),
        # Turn 2: LLM erroneously calls probe_tool with identical arguments again
        ModelResponse(content="", model_name="mock", tool_calls=[duplicate_call]),
        # Turn 3: LLM provides final answer
        ModelResponse(content="Final synthesized output.", model_name="mock"),
    ]

    memory = InMemoryMemory()
    engine = EkkoEngine(provider=mock_provider, memory=memory, tools=registry)

    reply = await engine.process_message("Investigate same_url", session_id="circuit_breaker_test")

    assert reply == "Final synthesized output."
    # Physical tool execution must happen ONLY once
    assert call_count == 1

    messages = await memory.get_messages("circuit_breaker_test")
    # user, asst(call1), tool(obs1), asst(call2), tool(circuit_breaker), asst(final)
    assert len(messages) == 6
    assert messages[4].tool_call_id == "c_dup"


@pytest.mark.asyncio
async def test_engine_handles_empty_tool_result_content() -> None:
    """Ensure engine does not raise Pydantic validation error when tool content is empty or whitespace."""
    from pydantic import BaseModel
    from ekko.core.models import ToolCall, ToolResult
    from ekko.tools.base import BaseTool
    from ekko.tools.registry import ToolRegistry

    class EmptyArgs(BaseModel):
        pass

    class EmptyTool(BaseTool):
        name: str = "empty_tool"
        description: str = "Returns empty content"
        args_schema: type[BaseModel] = EmptyArgs

        async def _run(self) -> ToolResult:
            return ToolResult(content="", success=True)

    registry = ToolRegistry()
    registry.register(EmptyTool())

    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(content="", model_name="mock", tool_calls=[ToolCall(id="c_empty", name="empty_tool", arguments={})]),
        ModelResponse(content="Handled empty gracefully.", model_name="mock"),
    ]

    memory = InMemoryMemory()
    engine = EkkoEngine(provider=mock_provider, memory=memory, tools=registry)

    reply = await engine.process_message("Run empty tool", session_id="empty_test")
    assert reply == "Handled empty gracefully."

    messages = await memory.get_messages("empty_test")
    assert len(messages) == 4
    tool_msg = messages[2]
    assert tool_msg.role == "tool"
    assert tool_msg.content == "(Aucun contenu retourné par l'outil)"


@pytest.mark.asyncio
async def test_engine_prefixes_tool_failure_in_message() -> None:
    """Ensure tool execution failure prefixes the injected tool message with [ÉCHEC OUTIL - ErrorType]."""
    from pydantic import BaseModel
    from ekko.core.models import ToolCall, ToolResult
    from ekko.tools.base import BaseTool
    from ekko.tools.registry import ToolRegistry

    class FailingArgs(BaseModel):
        path: str

    class FailingTool(BaseTool):
        name: str = "failing_tool"
        description: str = "Simulates failure"
        args_schema: type[BaseModel] = FailingArgs

        async def _run(self, path: str) -> ToolResult:
            return ToolResult(
                content="Accès interdit",
                success=False,
                error="SecurityViolation",
            )

    registry = ToolRegistry()
    registry.register(FailingTool())

    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(
            content="",
            model_name="mock",
            tool_calls=[ToolCall(id="c_fail", name="failing_tool", arguments={"path": "/etc/shadow"})],
        ),
        ModelResponse(content="L'accès a été refusé.", model_name="mock"),
    ]

    memory = InMemoryMemory()
    engine = EkkoEngine(provider=mock_provider, memory=memory, tools=registry)

    reply = await engine.process_message("Read /etc/shadow", session_id="fail_test")
    assert reply == "L'accès a été refusé."

    messages = await memory.get_messages("fail_test")
    tool_msg = messages[2]
    assert tool_msg.role == "tool"
    assert tool_msg.content == "[ÉCHEC OUTIL - SecurityViolation] : Accès interdit"




