"""Integration test verifying end-to-end flow with SystemInfoTool and EkkoEngine."""

from unittest.mock import AsyncMock
import pytest

from ekko.core.engine import EkkoEngine
from ekko.core.models import ModelResponse, ToolCall
from ekko.memory.in_memory import InMemoryMemory
from ekko.tools.registry import ToolRegistry
from ekko.tools.system_info import SystemInfoTool


@pytest.mark.asyncio
async def test_system_info_tool_integration_in_engine() -> None:
    """Ensure engine receives tool call, executes SystemInfoTool, and produces response."""
    registry = ToolRegistry()
    registry.register(SystemInfoTool())

    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(
            content="",
            model_name="mock-llm",
            tool_calls=[ToolCall(id="call_sys", name="system_info", arguments={})],
        ),
        ModelResponse(
            content="Voici les ressources de la machine : 8 Go VRAM et 16 Go RAM.",
            model_name="mock-llm",
        ),
    ]

    memory = InMemoryMemory()
    engine = EkkoEngine(provider=mock_provider, memory=memory, tools=registry)

    response = await engine.process_message("Quelles sont les ressources de la machine ?")

    assert "Voici les ressources" in response
    messages = await memory.get_messages("default")
    assert len(messages) == 4
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[2].role == "tool"
    assert messages[2].tool_call_id == "call_sys"
    assert "System Hardware & Resource Status:" in messages[2].content
    assert messages[3].role == "assistant"
