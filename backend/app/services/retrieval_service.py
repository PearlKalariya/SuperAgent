from app.models.citations import Citation
from app.services.vector_store import VectorStore


class RetrievalService:
    def __init__(self, vector_store: VectorStore) -> None:
        self.vector_store = vector_store

    async def search(self, query: str, limit: int = 5) -> list[Citation]:
        await self.vector_store.ensure_seed_data()
        return await self.vector_store.search(
            query,
            limit=limit,
            where={"kind": {"$ne": "conversation_memory"}},
        )
