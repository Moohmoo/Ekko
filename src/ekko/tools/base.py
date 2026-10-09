"""Base class for tools providing automated Pydantic schema generation and argument validation."""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, ValidationError

from ekko.core.models import ToolResult


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
        try:
            validated = self.args_schema.model_validate(kwargs)
            return await self._run(**validated.model_dump())
        except ValidationError as err:
            return ToolResult(
                content=f"Validation error: {err}",
                success=False,
                error=str(err),
            )
        except Exception as err:
            return ToolResult(
                content=f"Execution error: {err}",
                success=False,
                error=str(err),
            )
