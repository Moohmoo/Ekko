"""Package des outils d'action pour l'agent Ekko."""

from .base import BaseTool, EmptyParams
from .reader import FetchPageParams, FetchPageTool, ReaderParams, ReaderTool
from .registry import ToolRegistry, default_registry
from .search import SearchParams, SearchTool, WebSearchParams, WebSearchTool
from .system import SystemInfoTool

# Enregistrement des outils universels par défaut
default_registry.register(SearchTool())
default_registry.register(ReaderTool())
default_registry.register(SystemInfoTool())

__all__ = [
    "BaseTool",
    "EmptyParams",
    "ToolRegistry",
    "default_registry",
    "SearchTool",
    "SearchParams",
    "WebSearchTool",
    "WebSearchParams",
    "ReaderTool",
    "ReaderParams",
    "FetchPageTool",
    "FetchPageParams",
    "SystemInfoTool",
]
