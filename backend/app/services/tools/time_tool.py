from datetime import datetime, UTC
from typing import Any

from pydantic import BaseModel

from app.services.tools.base import BaseTool, ToolResult


class TimeTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_current_time"

    @property
    def description(self) -> str:
        return "Get the current system time."

    @property
    def parameters(self) -> type[BaseModel]:
        class EmptySchema(BaseModel):
            pass
        return EmptySchema

    async def execute(self, **kwargs: Any) -> ToolResult:
        now = datetime.now(UTC)
        return ToolResult(
            summary=f"The current system time is {now.isoformat()}",
            data={"time": now.isoformat()}
        )
