import abc
from typing import Any

from pydantic import BaseModel



class ToolResult(BaseModel):
    summary: str
    data: dict[str, Any] | None = None
    error: str | None = None


class BaseTool(abc.ABC):
    """Base interface for all agent tools."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """The tool name as exposed to the LLM."""
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """The description of the tool for the LLM."""
        pass

    @property
    def parameters(self) -> type[BaseModel]:
        """Pydantic model representing the input schema."""
        class EmptySchema(BaseModel):
            pass
        return EmptySchema

    @abc.abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool and return the result."""
        pass
