"""Package des outils d'action pour l'agent Ekko."""

from .base import BaseTool, EmptyParams
from .registry import ToolRegistry, default_registry
from .system_tool import SystemInfoTool
from .watch_tool import WatchTool

# Enregistrement des outils natifs par défaut
default_registry.register(WatchTool())
default_registry.register(SystemInfoTool())

__all__ = [
    "BaseTool",
    "EmptyParams",
    "ToolRegistry",
    "default_registry",
    "WatchTool",
    "SystemInfoTool",
]
