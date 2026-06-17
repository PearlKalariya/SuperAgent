import hashlib
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.models.documents import DocumentIngestResponse
from app.services.vector_store import VectorStore

ALLOWED_TEXT_CONTENT_TYPES = {
    "application/json",
    "application/octet-stream",
    "application/x-ndjson",
    "application/xml",
    "text/css",
    "text/csv",
    "text/html",
    "text/javascript",
    "text/markdown",
    "text/plain",
    "text/xml",
}

ALLOWED_BINARY_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

BINARY_EXTENSIONS = {".pdf", ".docx"}


class DocumentService:
    def __init__(self, vector_store: VectorStore) -> None:
        self.vector_store = vector_store

    async def ingest_upload(self, file: UploadFile) -> DocumentIngestResponse:
        filename = Path(file.filename or "uploaded-document").name
        self._validate_filename(filename)
        self._validate_content_type(file.content_type)

        raw = await file.read(settings.max_upload_bytes + 1)
        if len(raw) > settings.max_upload_bytes:
            raise ValueError(f"Uploaded file exceeds {settings.max_upload_bytes} bytes.")
        self._reject_binary_content(raw, filename)

        text = self._extract_text(raw, Path(filename).suffix.lower())
        if not text.strip():
            raise ValueError("The uploaded file did not contain readable text.")

        document_id = self._document_id(filename, raw)
        chunks = self._chunk_text(text)
        if len(chunks) > settings.max_upload_chunks:
            raise ValueError(f"Uploaded file produced more than {settings.max_upload_chunks} chunks.")
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
    def _extract_text(raw: bytes, extension: str) -> str:
        if extension == ".pdf":
            return DocumentService._extract_text_from_pdf(raw)
        if extension == ".docx":
            return DocumentService._extract_text_from_docx(raw)
        return DocumentService._decode_text(raw)

    @staticmethod
    def _extract_text_from_pdf(raw: bytes) -> str:
        try:
            from pdfminer.high_level import extract_text
        except ImportError as error:
            raise ValueError("PDF support requires the pdfminer.six package.") from error

        try:
            return extract_text(BytesIO(raw)) or ""
        except Exception as error:
            raise ValueError(f"Unable to parse PDF document: {error}") from error

    @staticmethod
    def _extract_text_from_docx(raw: bytes) -> str:
        try:
            from docx import Document
        except ImportError as error:
            raise ValueError("DOCX support requires the python-docx package.") from error

        try:
            document = Document(BytesIO(raw))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
        except Exception as error:
            raise ValueError(f"Unable to parse DOCX document: {error}") from error

    @staticmethod
    def _decode_text(raw: bytes) -> str:
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="ignore")

    @staticmethod
    def _validate_filename(filename: str) -> None:
        extension = Path(filename).suffix.lower()
        allowed_extensions = {
            item.strip().lower()
            for item in settings.allowed_upload_extensions.split(",")
            if item.strip()
        }
        if extension not in allowed_extensions:
            raise ValueError(f"Unsupported file extension: {extension or 'none'}.")

    @staticmethod
    def _validate_content_type(content_type: str | None) -> None:
        if not content_type:
            return
        normalized = content_type.split(";")[0].strip().lower()
        if normalized.startswith("text/") or normalized in ALLOWED_TEXT_CONTENT_TYPES or normalized in ALLOWED_BINARY_CONTENT_TYPES:
            return
        raise ValueError(f"Unsupported content type: {content_type}.")

    @staticmethod
    def _reject_binary_content(raw: bytes, filename: str) -> None:
        extension = Path(filename).suffix.lower()
        if extension in BINARY_EXTENSIONS:
            return

        if b"\x00" in raw:
            raise ValueError("Binary files are not supported.")
        if not raw:
            raise ValueError("Uploaded file is empty.")

        sample = raw[:4096]
        control_bytes = sum(
            1
            for byte in sample
            if byte < 32 and byte not in (9, 10, 13)
        )
        if sample and control_bytes / len(sample) > 0.08:
            raise ValueError("Uploaded file appears to be binary content.")

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
