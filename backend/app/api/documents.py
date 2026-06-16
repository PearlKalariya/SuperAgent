from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.documents import DocumentIngestResponse
from app.services.dependencies import document_service

router = APIRouter()


@router.post("/documents", response_model=DocumentIngestResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentIngestResponse:
    try:
        return await document_service.ingest_upload(file)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
