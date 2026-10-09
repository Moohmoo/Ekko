"""Unit tests for ToolCatalog and declarative plugin instantiation."""

from pydantic import BaseModel
import pytest

from ekko.core.models import ToolResult
from ekko.tools.base import BaseTool
from ekko.tools.catalog import ToolCatalog
from ekko.tools.hacker_news import HackerNewsTool
from ekko.tools.system_info import SystemInfoTool
from ekko.tools.url_reader import UrlReaderTool


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


def test_catalog_default_includes_hacker_news() -> None:
    """Ensure default catalog contains HackerNewsTool."""
    catalog = ToolCatalog(include_defaults=True)
    assert catalog.get_class("hacker_news") is HackerNewsTool


def test_catalog_default_includes_url_reader() -> None:
    """Ensure default catalog contains UrlReaderTool."""
    catalog = ToolCatalog(include_defaults=True)
    assert catalog.get_class("url_reader") is UrlReaderTool



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
