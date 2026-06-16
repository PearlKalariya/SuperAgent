from pydantic import BaseModel


class DocumentIngestResponse(BaseModel):
    document_id: str
    filename: str
    chunks_indexed: int
    characters_indexed: int
    source: str
