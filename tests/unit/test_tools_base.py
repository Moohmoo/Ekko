"""Unit tests for BaseTool and dynamic Pydantic schema introspection."""

from typing import Any
import pytest
from pydantic import BaseModel, Field

from ekko.core.models import ToolResult
from ekko.core.ports import ToolPort
from ekko.tools.base import BaseTool


class CalculatorArgs(BaseModel):
    """Schema for test calculator tool."""

    a: int = Field(..., description="First integer")
    b: int = Field(..., description="Second integer")


class CalculatorTool(BaseTool):
    """Test implementation of BaseTool."""

    name: str = "calculator"
    description: str = "Adds two numbers together"
    args_schema: type[BaseModel] = CalculatorArgs

    async def _run(self, a: int, b: int) -> ToolResult:
        return ToolResult(content=str(a + b), success=True)


class CrashingTool(BaseTool):
    """Test tool that raises unexpected runtime exception."""

    name: str = "crashing"
    description: str = "Fails at runtime"
    args_schema: type[BaseModel] = CalculatorArgs

    async def _run(self, a: int, b: int) -> ToolResult:
        raise RuntimeError("Disk failure")


def test_base_tool_implements_tool_port() -> None:
    """Ensure BaseTool instances comply with ToolPort protocol."""
    tool = CalculatorTool()
    assert isinstance(tool, ToolPort)


def test_base_tool_schema_generation() -> None:
    """Ensure get_schema derives OpenAI/LiteLLM standard tool schema via Pydantic."""
    tool = CalculatorTool()
    schema = tool.get_schema()

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "calculator"
    assert schema["function"]["description"] == "Adds two numbers together"

    parameters = schema["function"]["parameters"]
    assert parameters["type"] == "object"
    assert "a" in parameters["properties"]
    assert "b" in parameters["properties"]
    assert parameters["required"] == ["a", "b"]


@pytest.mark.asyncio
async def test_base_tool_execute_success() -> None:
    """Ensure valid parameters are validated and passed to _run."""
    tool = CalculatorTool()
    result = await tool.execute(a=10, b=32)

    assert result.success is True
    assert result.content == "42"
    assert result.error is None


@pytest.mark.asyncio
async def test_base_tool_execute_validation_error() -> None:
    """Ensure missing or malformed parameters return structured failure."""
    tool = CalculatorTool()
    result = await tool.execute(a="not_an_int")

    assert result.success is False
    assert "Validation error" in result.content
    assert result.error is not None


@pytest.mark.asyncio
async def test_base_tool_execute_runtime_exception_handled() -> None:
    """Ensure runtime tool crashes are captured as ToolResult errors."""
    tool = CrashingTool()
    result = await tool.execute(a=1, b=2)

    assert result.success is False
    assert "Execution error" in result.content
    assert "Disk failure" in str(result.error)
