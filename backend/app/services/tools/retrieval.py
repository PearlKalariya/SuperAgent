from typing import Any

from pydantic import BaseModel, Field

from app.services.retrieval_service import RetrievalService
from app.services.tools.base import BaseTool, ToolResult


class RetrievalToolSchema(BaseModel):
    query: str = Field(..., description="The search query to find information in the knowledge base.")


class RetrievalTool(BaseTool):
    def __init__(self, retrieval_service: RetrievalService):
        self.retrieval_service = retrieval_service

    @property
    def name(self) -> str:
        return "search_knowledge_base"

    @property
    def description(self) -> str:
        return "Search the user's uploaded documents and knowledge base for context."

    @property
    def parameters(self) -> type[BaseModel]:
        return RetrievalToolSchema

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query")
        if not query:
            return ToolResult(summary="Failed: query is required.", error="query is required")
        
        try:
            citations = await self.retrieval_service.search(query)
            if not citations:
                return ToolResult(summary="No results found in knowledge base.", data={"citations": []})
            
            summary = "\n\n".join([f"Source: {c.source}\n{c.text}" for c in citations])
            return ToolResult(
                summary=f"Found {len(citations)} results:\n{summary}",
                data={"citations": [c.model_dump() for c in citations]}
            )
        except Exception as e:
            return ToolResult(summary=f"Error searching knowledge base: {e}", error=str(e))
