from fastapi import APIRouter

from app.models.query import HistoryResponse
from app.services.dependencies import memory_service

router = APIRouter()


@router.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str) -> HistoryResponse:
    return HistoryResponse(session_id=session_id, messages=memory_service.get_history(session_id))
