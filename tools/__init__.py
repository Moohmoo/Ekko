"""Package des outils d'action pour l'agent Ekko."""

from .base import BaseTool, EmptyParams
from .registry import ToolRegistry, default_registry
from .search import WebSearchTool
from .system import SystemInfoTool
from .web import FetchPageTool

# Enregistrement des outils natifs par défaut
default_registry.register(WebSearchTool())
default_registry.register(FetchPageTool())
default_registry.register(SystemInfoTool())

__all__ = [
    "BaseTool",
    "EmptyParams",
    "ToolRegistry",
    "default_registry",
    "WebSearchTool",
    "FetchPageTool",
    "SystemInfoTool",
]
