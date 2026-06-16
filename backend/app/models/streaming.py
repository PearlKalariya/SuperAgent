from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

StreamEventType = Literal[
    "run_started",
    "status",
    "retrieval_started",
    "retrieval_result",
    "tool_call_started",
    "tool_call_result",
    "token",
    "citation",
    "error",
    "run_completed",
]


class StreamEvent(BaseModel):
    run_id: str
    session_id: str
    type: StreamEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)
