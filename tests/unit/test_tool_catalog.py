"""Unit tests for ToolCatalog and declarative plugin instantiation."""

from pydantic import BaseModel
import pytest

from ekko.core.models import ToolResult
from ekko.tools.base import BaseTool
from ekko.tools.catalog import ToolCatalog
from ekko.tools.note_writer import NoteWriterTool
from ekko.tools.read_resource import ReadResourceTool
from ekko.tools.system_info import SystemInfoTool


class MockArgs(BaseModel):
    x: int


class MockCustomTool(BaseTool):
    name: str = "custom_tool"
    description: str = "Mock tool"
    args_schema: type[BaseModel] = MockArgs

    async def _run(self, x: int) -> ToolResult:
        return ToolResult(content=str(x), success=True)


def test_catalog_register_and_get() -> None:
    """Ensure custom tool classes can be registered and retrieved by name."""
    catalog = ToolCatalog(include_defaults=False)
    catalog.register(MockCustomTool)

    assert catalog.get_class("custom_tool") is MockCustomTool
    assert catalog.get_class("missing") is None


def test_catalog_default_includes_system_info() -> None:
    """Ensure default catalog contains SystemInfoTool."""
    catalog = ToolCatalog(include_defaults=True)
    assert catalog.get_class("system_info") is SystemInfoTool


def test_catalog_default_includes_read_resource() -> None:
    """Ensure default catalog contains ReadResourceTool."""
    catalog = ToolCatalog(include_defaults=True)
    assert catalog.get_class("read_resource") is ReadResourceTool


def test_catalog_default_includes_save_note() -> None:
    """Ensure default catalog contains NoteWriterTool."""
    catalog = ToolCatalog(include_defaults=True)
    assert catalog.get_class("save_note") is NoteWriterTool


def test_catalog_default_includes_query_knowledge() -> None:
    """Ensure default catalog contains QueryKnowledgeTool."""
    from ekko.tools.query_knowledge import QueryKnowledgeTool

    catalog = ToolCatalog(include_defaults=True)
    assert catalog.get_class("query_knowledge") is QueryKnowledgeTool



def test_catalog_build_registry_filters_enabled_tools() -> None:
    """Ensure build_registry only instantiates and registers enabled tools."""
    catalog = ToolCatalog(include_defaults=True)
    catalog.register(MockCustomTool)

    registry = catalog.build_registry(enabled_names=["custom_tool"])

    assert registry.get("custom_tool") is not None
    assert registry.get("system_info") is None


def test_catalog_build_registry_skips_unknown_tool_without_crashing() -> None:
    """Ensure unknown tool names in configuration do not trigger exceptions."""
    catalog = ToolCatalog(include_defaults=True)
    registry = catalog.build_registry(enabled_names=["nonexistent_plugin"])

    assert registry.list_tools() == []
 
 
def test_catalog_build_registry_injects_dependencies() -> None:
    """Ensure build_registry propagates db_manager and notes_dir to tools."""
    from unittest.mock import MagicMock

    catalog = ToolCatalog(include_defaults=True)
    mock_db = MagicMock()
    registry = catalog.build_registry(
        enabled_names=["save_note", "query_knowledge", "scan_inbox", "read_resource"],
        db_manager=mock_db,
    )

    save_note = registry.get("save_note")
    assert isinstance(save_note, NoteWriterTool)
    assert save_note.db_manager is mock_db

    query_tool = registry.get("query_knowledge")
    assert query_tool is not None
    assert getattr(query_tool, "db_manager") is mock_db
