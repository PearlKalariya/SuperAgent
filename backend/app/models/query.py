from pydantic import BaseModel, Field

from app.models.citations import Citation
from app.models.workflow import ToolTrace


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    session_id: str = "default"


class ChatMessage(BaseModel):
    role: str
    content: str


class QueryResponse(BaseModel):
    run_id: str
    session_id: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    tool_traces: list[ToolTrace] = Field(default_factory=list)


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
