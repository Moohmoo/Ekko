"""Unit tests for the ToolRegistry."""

import pytest
from pydantic import BaseModel

from ekko.core.models import ToolResult
from ekko.tools.base import BaseTool
from ekko.tools.registry import ToolRegistry


class DummyArgs(BaseModel):
    query: str


class EchoTool(BaseTool):
    name: str = "echo"
    description: str = "Echoes input"
    args_schema: type[BaseModel] = DummyArgs

    async def _run(self, query: str) -> ToolResult:
        return ToolResult(content=query, success=True)


class SearchTool(BaseTool):
    name: str = "search"
    description: str = "Searches web"
    args_schema: type[BaseModel] = DummyArgs

    async def _run(self, query: str) -> ToolResult:
        return ToolResult(content="Results", success=True)


def test_registry_register_and_get() -> None:
    """Ensure tools can be registered and retrieved by name."""
    registry = ToolRegistry()
    tool = EchoTool()

    registry.register(tool)

    assert registry.get("echo") is tool
    assert registry.get("unknown") is None
    assert registry.list_tools() == ["echo"]


def test_registry_duplicate_registration_raises_error() -> None:
    """Ensure duplicate tool names are rejected to avoid collisions."""
    registry = ToolRegistry()
    registry.register(EchoTool())

    with pytest.raises(ValueError) as exc_info:
        registry.register(EchoTool())

    assert "already registered" in str(exc_info.value)


def test_registry_get_schemas() -> None:
    """Ensure get_schemas aggregates JSON schemas of all registered tools."""
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(SearchTool())

    schemas = registry.get_schemas()
    names = [s["function"]["name"] for s in schemas]

    assert len(schemas) == 2
    assert "echo" in names
    assert "search" in names


def test_registry_get_schemas_with_filter() -> None:
    """Ensure get_schemas respects enabled tools filter."""
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(SearchTool())

    filtered_schemas = registry.get_schemas(enabled_names=["echo"])
    assert len(filtered_schemas) == 1
    assert filtered_schemas[0]["function"]["name"] == "echo"
