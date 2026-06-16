from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class StructuredWorkflowInput(BaseModel):
    original_query: str
    normalized_query: str
    intent: str
    retrieval_query: str


class WorkflowStep(BaseModel):
    name: str
    status: Literal["pending", "running", "completed", "failed"]
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    detail: str | None = None


class ToolTrace(BaseModel):
    name: str
    status: Literal["started", "completed", "failed"]
    input: dict[str, Any] = Field(default_factory=dict)
    output_summary: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    error: str | None = None
