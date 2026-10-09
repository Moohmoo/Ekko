"""ToolCatalog mapping configuration names to tool classes adhering to OCP."""

from ekko.tools.arxiv import ArxivTool
from ekko.tools.base import BaseTool
from ekko.tools.hacker_news import HackerNewsTool
from ekko.tools.note_writer import NoteWriterTool
from ekko.tools.registry import ToolRegistry
from ekko.tools.system_info import SystemInfoTool
from ekko.tools.url_reader import UrlReaderTool
from ekko.utils.logger import get_logger

logger = get_logger("tools.catalog")


class ToolCatalog:
    """Extensible factory registry storing tool classes without hardcoding instances."""

    def __init__(self, include_defaults: bool = True) -> None:
        self._classes: dict[str, type[BaseTool]] = {}
        if include_defaults:
            self.register(SystemInfoTool)
            self.register(HackerNewsTool)
            self.register(UrlReaderTool)
            self.register(ArxivTool)
            self.register(NoteWriterTool)

    def register(self, tool_cls: type[BaseTool]) -> None:
        """Register a tool class mapped to its canonical tool name."""
        name = getattr(tool_cls, "name", tool_cls.__name__)
        self._classes[name] = tool_cls
        logger.debug("Registered tool class in catalog: %s", name)

    def get_class(self, name: str) -> type[BaseTool] | None:
        """Retrieve tool class by registered name, or None."""
        return self._classes.get(name)

    def build_registry(self, enabled_names: list[str]) -> ToolRegistry:
        """Instantiate and register tools declared in enabled configuration."""
        registry = ToolRegistry()
        for name in enabled_names:
            cls = self.get_class(name)
            if cls is not None:
                instance = cls()
                registry.register(instance)
                logger.info("Instantiated and activated tool from catalog: %s", name)
            else:
                logger.warning("Configured tool '%s' not found in catalog, skipping.", name)

        return registry
