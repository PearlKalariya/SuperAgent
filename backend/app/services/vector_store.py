import json
import math
from pathlib import Path

from app.core.config import settings
from app.models.citations import Citation
from app.services.embedding_service import EmbeddingService


class VectorStore:
    def __init__(self, embedding_service: EmbeddingService) -> None:
        self.embedding_service = embedding_service
        self.persist_dir = Path(settings.chroma_persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.fallback_path = self.persist_dir / "fallback_vectors.json"
        self._seeded = False
        self._collection = self._create_chroma_collection()

    async def ensure_seed_data(self) -> None:
        if self._seeded:
            return

        documents = [
            (
                "requirements-overview",
                "SuperAgent is a modular RAG workflow with Next.js, FastAPI, Gemini embeddings, ChromaDB, Composio, and streaming responses.",
                {"title": "Requirements Overview", "source": "TASK_REQUIREMENTS.md"},
            ),
            (
                "backend-architecture",
                "The backend orchestrates query understanding, retrieval, memory, tool calls, and response generation through FastAPI services.",
                {"title": "Backend Architecture", "source": "TASK_REQUIREMENTS.md"},
            ),
            (
                "frontend-experience",
                "The frontend provides a responsive single-page query interface with streaming status, citations, result sections, and keyboard-friendly controls.",
                {"title": "Frontend Experience", "source": "TASK_REQUIREMENTS.md"},
            ),
        ]
        records = []
        for doc_id, text, metadata in documents:
            records.append(
                {
                    "id": doc_id,
                    "text": text,
                    "metadata": metadata,
                    "embedding": await self.embedding_service.embed(text),
                }
            )

        if self._collection is not None:
            existing = self._collection.get(ids=[record["id"] for record in records])
            existing_ids = set(existing.get("ids", []))
            new_records = [record for record in records if record["id"] not in existing_ids]
            if new_records:
                self._collection.add(
                    ids=[record["id"] for record in new_records],
                    documents=[record["text"] for record in new_records],
                    metadatas=[record["metadata"] for record in new_records],
                    embeddings=[record["embedding"] for record in new_records],
                )
            self._seeded = True
            return

        if self.fallback_path.exists():
            self._seeded = True
            return

        self.fallback_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        self._seeded = True

    async def search(self, query: str, limit: int = 3) -> list[Citation]:
        await self.ensure_seed_data()
        query_embedding = await self.embedding_service.embed(query)
        if self._collection is not None:
            result = self._collection.query(query_embeddings=[query_embedding], n_results=limit)
            ids = result.get("ids", [[]])[0]
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]
            citations = []
            for index, doc_id in enumerate(ids):
                metadata = metadatas[index] or {}
                distance = distances[index] if index < len(distances) else None
                score = None if distance is None else round(1 / (1 + distance), 4)
                citations.append(
                    Citation(
                        id=doc_id,
                        title=metadata.get("title", doc_id),
                        source=metadata.get("source", "unknown"),
                        snippet=documents[index],
                        score=score,
                        metadata=metadata,
                    )
                )
            return citations

        records = json.loads(self.fallback_path.read_text(encoding="utf-8"))
        scored = []
        for record in records:
            score = self._cosine_similarity(query_embedding, record["embedding"])
            scored.append((score, record))

        citations = []
        for score, record in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]:
            metadata = record["metadata"]
            citations.append(
                Citation(
                    id=record["id"],
                    title=metadata.get("title", record["id"]),
                    source=metadata.get("source", "unknown"),
                    snippet=record["text"],
                    score=round(score, 4),
                    metadata=metadata,
                )
            )
        return citations

    async def upsert_text_chunks(
        self,
        document_id: str,
        source: str,
        chunks: list[str],
        metadata: dict[str, str],
    ) -> None:
        if not chunks:
            return

        records = []
        for index, chunk in enumerate(chunks):
            chunk_metadata = {
                **metadata,
                "source": source,
                "chunk_index": index,
                "document_id": document_id,
            }
            records.append(
                {
                    "id": f"{document_id}_chunk_{index}",
                    "text": chunk,
                    "metadata": chunk_metadata,
                    "embedding": await self.embedding_service.embed(chunk),
                }
            )

        if self._collection is not None:
            self._collection.upsert(
                ids=[record["id"] for record in records],
                documents=[record["text"] for record in records],
                metadatas=[record["metadata"] for record in records],
                embeddings=[record["embedding"] for record in records],
            )
            return

        existing_records = []
        if self.fallback_path.exists():
            existing_records = json.loads(self.fallback_path.read_text(encoding="utf-8"))
        existing_by_id = {record["id"]: record for record in existing_records}
        for record in records:
            existing_by_id[record["id"]] = record
        self.fallback_path.write_text(
            json.dumps(list(existing_by_id.values()), indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(value * value for value in left)) or 1.0
        right_norm = math.sqrt(sum(value * value for value in right)) or 1.0
        return numerator / (left_norm * right_norm)

    def _create_chroma_collection(self):
        try:
            import chromadb
        except ImportError:
            return None

        client = chromadb.PersistentClient(path=str(self.persist_dir))
        return client.get_or_create_collection(name=settings.chroma_collection)
