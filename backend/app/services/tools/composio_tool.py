from typing import Any

from pydantic import BaseModel

from app.services.composio_service import ComposioService
from app.services.tools.base import BaseTool, ToolResult


class ComposioActionTool(BaseTool):
    """Adapts a Composio action to the BaseTool interface."""

    def __init__(
        self,
        composio_service: ComposioService,
        action_name: str,
        description: str,
        schema: type[BaseModel],
    ):
        self.composio_service = composio_service
        self._action_name = action_name
        self._description = description
        self._schema = schema

    @property
    def name(self) -> str:
        return self._action_name.lower()

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> type[BaseModel]:
        return self._schema

    async def execute(self, **kwargs: Any) -> ToolResult:
        if not self.composio_service.is_live:
            return ToolResult(
                summary="Mock Composio action successful.",
                data={"mocked": True, "action": self._action_name, "input": kwargs}
            )

        try:
            # Delegate to composio_service public API for execution
            result = self.composio_service.execute_action(
                action=self._action_name,
                params=kwargs,
            )
            return ToolResult(
                summary=str(result)[:1000],
                data={"result": result}
            )
        except Exception as e:
            return ToolResult(summary=f"Error executing Composio action: {e}", error=str(e))
