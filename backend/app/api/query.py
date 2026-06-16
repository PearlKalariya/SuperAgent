from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.errors import WorkflowError
from app.models.query import QueryRequest, QueryResponse
from app.services.dependencies import agent_service

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def run_query(request: QueryRequest) -> QueryResponse:
    try:
        return await agent_service.run_query(request)
    except WorkflowError as error:
        raise HTTPException(
            status_code=500,
            detail={"message": error.message, "step": error.step},
        ) from error


@router.post("/query/stream")
async def stream_query(request: QueryRequest) -> StreamingResponse:
    return StreamingResponse(
        agent_service.stream_query(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
