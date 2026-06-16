from collections import defaultdict

from app.models.query import ChatMessage


class MemoryService:
    def __init__(self) -> None:
        self._messages: dict[str, list[ChatMessage]] = defaultdict(list)

    def add_exchange(self, session_id: str, user_query: str, assistant_response: str) -> None:
        self._messages[session_id].append(ChatMessage(role="user", content=user_query))
        self._messages[session_id].append(ChatMessage(role="assistant", content=assistant_response))

    def get_history(self, session_id: str) -> list[ChatMessage]:
        return list(self._messages[session_id])
