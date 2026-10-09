"""Base class for tools providing automated Pydantic schema generation and argument validation."""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, ValidationError

from ekko.core.models import ToolResult
from ekko.utils.logger import get_logger

logger = get_logger("tools")


class BaseTool(ABC):
    """Abstract base tool introspecting its args_schema to expose compliant schemas."""

    name: str
    description: str
    args_schema: type[BaseModel]

    def get_schema(self) -> dict[str, Any]:
        """Derive standard OpenAI/LiteLLM tool declaration from Pydantic schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_schema.model_json_schema(),
            },
        }

    @abstractmethod
    async def _run(self, **kwargs: Any) -> ToolResult:
        """Concrete tool logic executed with validated keyword arguments."""
        ...

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Validate input arguments against args_schema before delegating to _run."""
        logger.debug("Executing tool '%s' with arguments: %s", self.name, kwargs)
        try:
            validated = self.args_schema.model_validate(kwargs)
            result = await self._run(**validated.model_dump())
            logger.info("Tool '%s' executed successfully (success=%s)", self.name, result.success)
            return result
        except ValidationError as err:
            logger.error("Validation failed for tool '%s': %s", self.name, err)
            return ToolResult(
                content=f"Validation error: {err}",
                success=False,
                error=str(err),
            )
        except Exception as err:
            logger.error("Runtime exception in tool '%s': %s", self.name, err)
            return ToolResult(
                content=f"Execution error: {err}",
                success=False,
                error=str(err),
            )

