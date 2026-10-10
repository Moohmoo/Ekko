"""ToolCatalog mapping configuration names to tool classes adhering to OCP."""

from pathlib import Path
from typing import Any

from ekko.core.ports import HybridMemoryPort
from ekko.tools.base import BaseTool
from ekko.tools.note_writer import NoteWriterTool
from ekko.tools.query_knowledge import QueryKnowledgeTool
from ekko.tools.read_resource import ReadResourceTool
from ekko.tools.registry import ToolRegistry
from ekko.tools.scan_inbox import ScanInboxTool
from ekko.tools.system_info import SystemInfoTool
from ekko.logger import get_logger

logger = get_logger("tools.catalog")


def _instantiate_tool(
    cls: type[BaseTool],
    db_manager: HybridMemoryPort | None = None,
    notes_dir: Path | str = "data/notes",
    embedder: Any | None = None,
) -> BaseTool:
    """Instantiate a tool class injecting optional dependencies."""
    name = getattr(cls, "name", "")
    if name == "save_note":
        return NoteWriterTool(notes_dir=notes_dir, db_manager=db_manager, embedder=embedder)
    if name in {"query_knowledge", "scan_inbox"}:
        return cls(db_manager=db_manager)  # type: ignore[call-arg]
    return cls()


class ToolCatalog:
    """Extensible factory registry storing tool classes without hardcoding instances."""

    def __init__(self, include_defaults: bool = True) -> None:
        self._classes: dict[str, type[BaseTool]] = {}
        if include_defaults:
            self.register(SystemInfoTool)
            self.register(ReadResourceTool)
            self.register(NoteWriterTool)
            self.register(QueryKnowledgeTool)
            self.register(ScanInboxTool)

    def register(self, tool_cls: type[BaseTool]) -> None:
        """Register a tool class mapped to its canonical tool name."""
        name = getattr(tool_cls, "name", tool_cls.__name__)
        self._classes[name] = tool_cls
        logger.debug("Registered tool class in catalog: %s", name)

    def get_class(self, name: str) -> type[BaseTool] | None:
        """Retrieve tool class by registered name, or None."""
        return self._classes.get(name)

    def build_registry(
        self,
        enabled_names: list[str],
        db_manager: HybridMemoryPort | None = None,
        notes_dir: Path | str = "data/notes",
        embedder: Any | None = None,
    ) -> ToolRegistry:
        """Instantiate and register tools declared in enabled configuration."""
        registry = ToolRegistry()
        for name in enabled_names:
            cls = self.get_class(name)
            if cls is not None:
                instance = _instantiate_tool(cls, db_manager, notes_dir, embedder)
                registry.register(instance)
                logger.info("Instantiated and activated tool from catalog: %s", name)
            else:
                logger.warning("Configured tool '%s' not found in catalog, skipping.", name)

        return registry
