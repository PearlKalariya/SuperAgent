import logging
from datetime import UTC, datetime
from typing import Any

from app.models.workflow import ToolTrace
from app.services.tools.base import BaseTool

logger = logging.getLogger(__name__)


class OrchestrationService:
    """Manages the execution of agent tools."""

    async def execute_tools(
        self,
        tools: list[BaseTool],
        tool_inputs: dict[str, dict[str, Any]],
    ) -> list[ToolTrace]:
        """Execute a list of tools with given inputs and return traces.
        
        Args:
            tools: The list of tools available to execute.
            tool_inputs: A mapping of tool name to input arguments.
                         Only tools present in this mapping will be executed.
        """
        traces: list[ToolTrace] = []
        
        for tool in tools:
            if tool.name not in tool_inputs:
                continue

            inputs = tool_inputs[tool.name]
            started_at = datetime.now(UTC)
            try:
                result = await tool.execute(**inputs)
                traces.append(
                    ToolTrace(
                        name=tool.name,
                        status="completed" if not result.error else "failed",
                        input=inputs,
                        output_summary=result.summary,
                        started_at=started_at,
                        completed_at=datetime.now(UTC),
                        error=result.error,
                    )
                )
            except Exception as exc:
                logger.exception("Tool %s failed.", tool.name)
                traces.append(
                    ToolTrace(
                        name=tool.name,
                        status="failed",
                        input=inputs,
                        output_summary=None,
                        started_at=started_at,
                        completed_at=datetime.now(UTC),
                        error=str(exc)[:300],
                    )
                )

        return traces
