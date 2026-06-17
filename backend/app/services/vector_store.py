import json
import math
import re
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.models.citations import Citation
from app.services.embedding_service import EmbeddingService

MetadataValue = str | int | float | bool
MetadataFilterValue = MetadataValue | dict[str, MetadataValue]
Metadata = dict[str, MetadataValue]
MetadataFilter = dict[str, MetadataFilterValue]


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
                {
                    "title": "Requirements Overview",
                    "source": "TASK_REQUIREMENTS.md",
                    "kind": "system_seed",
                    "chunk_index": 0,
                },
            ),
            (
                "backend-architecture",
                "The backend orchestrates query understanding, retrieval, memory, tool calls, and response generation through FastAPI services.",
                {
                    "title": "Backend Architecture",
                    "source": "TASK_REQUIREMENTS.md",
                    "kind": "system_seed",
                    "chunk_index": 0,
                },
            ),
            (
                "frontend-experience",
                "The frontend provides a responsive single-page query interface with streaming status, citations, result sections, and keyboard-friendly controls.",
                {
                    "title": "Frontend Experience",
                    "source": "TASK_REQUIREMENTS.md",
                    "kind": "system_seed",
                    "chunk_index": 0,
                },
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
            self._upsert_chroma_records(records)
            self._seeded = True
            return

        if self.fallback_path.exists():
            self._upsert_fallback_records(records)
            self._seeded = True
            return

        self._upsert_fallback_records(records)
        self._seeded = True

    async def search(
        self,
        query: str,
        limit: int = 3,
        where: MetadataFilter | None = None,
    ) -> list[Citation]:
        await self.ensure_seed_data()
        query_embedding = await self.embedding_service.embed(query)
        if self._collection is not None:
            candidate_count = max(limit * 4, 20)
            result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=candidate_count,
                where=self._to_chroma_where(where),
            )
            ids = result.get("ids", [[]])[0]
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]
            citations = []
            for index, doc_id in enumerate(ids):
                metadata = metadatas[index] or {}
                distance = distances[index] if index < len(distances) else None
                vector_score = None if distance is None else 1 / (1 + distance)
                score = self._hybrid_score(query, documents[index], vector_score)
                citations.append(
                    Citation(
                        id=doc_id,
                        title=metadata.get("title", doc_id),
                        source=metadata.get("source", "unknown"),
                        snippet=documents[index],
                        score=round(score, 4),
                        metadata=metadata,
                    )
                )
            return sorted(citations, key=lambda citation: citation.score or 0, reverse=True)[:limit]

        records = json.loads(self.fallback_path.read_text(encoding="utf-8"))
        if where:
            records = [record for record in records if self._matches_where(record["metadata"], where)]
        scored = []
        for record in records:
            vector_score = self._cosine_similarity(query_embedding, record["embedding"])
            score = self._hybrid_score(query, record["text"], vector_score)
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
        metadata: Metadata,
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
            self._upsert_chroma_records(records)
            return

        self._upsert_fallback_records(records)

    async def count(self, where: MetadataFilter | None = None) -> int:
        await self.ensure_seed_data()
        if self._collection is not None:
            result = self._collection.get(where=self._to_chroma_where(where))
            return len(result.get("ids", []))

        if not self.fallback_path.exists():
            return 0
        records = json.loads(self.fallback_path.read_text(encoding="utf-8"))
        if where:
            records = [record for record in records if self._matches_where(record["metadata"], where)]
        return len(records)

    def _upsert_chroma_records(self, records: list[dict[str, Any]]) -> None:
        if not records or self._collection is None:
            return

        self._collection.upsert(
            ids=[record["id"] for record in records],
            documents=[record["text"] for record in records],
            metadatas=[record["metadata"] for record in records],
            embeddings=[record["embedding"] for record in records],
        )

    def _upsert_fallback_records(self, records: list[dict[str, Any]]) -> None:
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
    def _matches_where(metadata: Metadata, where: MetadataFilter) -> bool:
        for key, value in where.items():
            if isinstance(value, dict):
                if "$ne" in value and metadata.get(key) == value["$ne"]:
                    return False
                if "$eq" in value and metadata.get(key) != value["$eq"]:
                    return False
                continue
            if metadata.get(key) != value:
                return False
        return True

    @staticmethod
    def _to_chroma_where(where: MetadataFilter | None) -> dict[str, Any] | None:
        if not where:
            return None
        if len(where) == 1:
            key, value = next(iter(where.items()))
            return {key: value}
        return {"$and": [{key: value} for key, value in where.items()]}

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(value * value for value in left)) or 1.0
        right_norm = math.sqrt(sum(value * value for value in right)) or 1.0
        return numerator / (left_norm * right_norm)

    @classmethod
    def _hybrid_score(cls, query: str, text: str, vector_score: float | None) -> float:
        base_score = vector_score or 0.0
        lexical_score = cls._lexical_score(query, text)
        return (0.7 * base_score) + (0.3 * lexical_score)

    @staticmethod
    def _lexical_score(query: str, text: str) -> float:
        query_terms = set(re.findall(r"[a-zA-Z0-9_-]+", query.lower()))
        text_terms = set(re.findall(r"[a-zA-Z0-9_-]+", text.lower()))
        if not query_terms:
            return 0.0
        return len(query_terms & text_terms) / len(query_terms)

    def _create_chroma_collection(self):
        try:
            import chromadb
        except ImportError:
            return None

        client = chromadb.PersistentClient(path=str(self.persist_dir))
        return client.get_or_create_collection(name=settings.chroma_collection)
