"""ToolRegistry managing explicit registration and schema aggregation for tools."""

from typing import Any
from ekko.core.ports import ToolPort
from ekko.logger import get_logger

logger = get_logger("tools.registry")


class ToolRegistry:
    """Registry maintaining active tool instances and providing schema introspection."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolPort] = {}

    def register(self, tool: ToolPort) -> None:
        """Register a tool instance, preventing accidental name collisions."""
        if tool.name in self._tools:
            logger.error("Attempted duplicate registration for tool: %s", tool.name)
            raise ValueError(f"Tool with name '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        logger.info("Registered tool: %s", tool.name)

    def get(self, name: str) -> ToolPort | None:
        """Retrieve registered tool by name, or None if not found."""
        tool = self._tools.get(name)
        logger.debug("Tool lookup for '%s': %s", name, "found" if tool else "not found")
        return tool


    def list_tools(self) -> list[str]:
        """Return list of all registered tool names."""
        return list(self._tools.keys())

    def get_schemas(
        self,
        enabled_names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return OpenAI/LiteLLM tool definitions, optionally filtered."""
        if enabled_names is not None:
            active_tools = [t for name, t in self._tools.items() if name in enabled_names]
        else:
            active_tools = list(self._tools.values())

        return [tool.get_schema() for tool in active_tools]
