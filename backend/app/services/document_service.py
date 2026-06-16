import hashlib
from pathlib import Path

from fastapi import UploadFile

from app.models.documents import DocumentIngestResponse
from app.services.vector_store import VectorStore


class DocumentService:
    def __init__(self, vector_store: VectorStore) -> None:
        self.vector_store = vector_store

    async def ingest_upload(self, file: UploadFile) -> DocumentIngestResponse:
        raw = await file.read()
        text = self._decode_text(raw)
        if not text.strip():
            raise ValueError("The uploaded file did not contain readable text.")

        filename = Path(file.filename or "uploaded-document").name
        document_id = self._document_id(filename, raw)
        chunks = self._chunk_text(text)
        await self.vector_store.upsert_text_chunks(
            document_id=document_id,
            source=filename,
            chunks=chunks,
            metadata={
                "title": filename,
                "source": filename,
                "kind": "uploaded_file",
                "content_type": file.content_type or "application/octet-stream",
            },
        )
        return DocumentIngestResponse(
            document_id=document_id,
            filename=filename,
            chunks_indexed=len(chunks),
            characters_indexed=len(text),
            source=filename,
        )

    @staticmethod
    def _decode_text(raw: bytes) -> str:
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="ignore")

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
        normalized = " ".join(text.split())
        if not normalized:
            return []

        chunks = []
        start = 0
        while start < len(normalized):
            end = min(start + chunk_size, len(normalized))
            chunks.append(normalized[start:end])
            if end == len(normalized):
                break
            start = max(0, end - overlap)
        return chunks

    @staticmethod
    def _document_id(filename: str, raw: bytes) -> str:
        digest = hashlib.sha256(filename.encode("utf-8") + raw).hexdigest()[:16]
        return f"doc_{digest}"
