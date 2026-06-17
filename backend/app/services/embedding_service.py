import hashlib
import logging
import math

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        self._client = None
        if settings.gemini_api_key:
            try:
                from google import genai

                self._client = genai.Client(api_key=settings.gemini_api_key)
            except ImportError:
                self._client = None

    async def embed(self, text: str) -> list[float]:
        if self._client is not None:
            try:
                result = self._client.models.embed_content(
                    model=settings.gemini_embedding_model,
                    contents=text,
                )
                embedding = result.embeddings[0].values
                return list(embedding)
            except Exception:
                logger.exception("Gemini embedding failed; using deterministic local fallback.")
                self._client = None

        return self._deterministic_embedding(text)

    @staticmethod
    def _deterministic_embedding(text: str, dimensions: int = 64) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = []
        for index in range(dimensions):
            byte = digest[index % len(digest)]
            values.append((byte / 255.0) - 0.5)
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]
