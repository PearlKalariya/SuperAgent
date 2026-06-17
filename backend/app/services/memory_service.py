from collections import defaultdict
import uuid

from app.models.citations import Citation
from app.models.query import ChatMessage
from app.services.vector_store import VectorStore


class MemoryService:
    def __init__(self, vector_store: VectorStore) -> None:
        self.vector_store = vector_store
        self._messages: dict[str, list[ChatMessage]] = defaultdict(list)

    async def add_exchange(self, session_id: str, user_query: str, assistant_response: str) -> None:
        self._messages[session_id].append(ChatMessage(role="user", content=user_query))
        self._messages[session_id].append(ChatMessage(role="assistant", content=assistant_response))

        memory_id = f"memory_{session_id}_{uuid.uuid4().hex}"
        await self.vector_store.upsert_text_chunks(
            document_id=memory_id,
            source=f"conversation:{session_id}",
            chunks=[
                f"User asked: {user_query}\nAssistant answered: {assistant_response}",
            ],
            metadata={
                "title": f"Conversation Memory {session_id}",
                "source": f"conversation:{session_id}",
                "kind": "conversation_memory",
                "session_id": session_id,
            },
        )

    def get_history(self, session_id: str) -> list[ChatMessage]:
        return list(self._messages[session_id])

    async def search(self, session_id: str, query: str, limit: int = 2) -> list[Citation]:
        return await self.vector_store.search(
            query,
            limit=limit,
            where={"kind": "conversation_memory", "session_id": session_id},
        )
