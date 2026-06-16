from pydantic import BaseModel, Field


class Citation(BaseModel):
    id: str
    title: str
    source: str
    snippet: str
    score: float | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)
