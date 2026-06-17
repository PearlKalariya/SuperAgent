from typing import Any

from pydantic import BaseModel, Field

from app.services.memory_service import MemoryService
from app.services.tools.base import BaseTool, ToolResult


class MemoryToolSchema(BaseModel):
    query: str = Field(..., description="The search query to find previous conversation context.")


class MemoryTool(BaseTool):
    def __init__(self, memory_service: MemoryService, session_id: str):
        self.memory_service = memory_service
        self.session_id = session_id

    @property
    def name(self) -> str:
        return "search_memory"

    @property
    def description(self) -> str:
        return "Search the current conversation memory for previous messages and context."

    @property
    def parameters(self) -> type[BaseModel]:
        return MemoryToolSchema

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query")
        if not query:
            return ToolResult(summary="Failed: query is required.", error="query is required")
        
        try:
            citations = await self.memory_service.search(self.session_id, query)
            if not citations:
                return ToolResult(summary="No results found in conversation memory.", data={"citations": []})
            
            summary = "\n\n".join([f"Source: {c.source}\n{c.text}" for c in citations])
            return ToolResult(
                summary=f"Found {len(citations)} results:\n{summary}",
                data={"citations": [c.model_dump() for c in citations]}
            )
        except Exception as e:
            return ToolResult(summary=f"Error searching memory: {e}", error=str(e))
