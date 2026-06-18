"""Unit tests for core backend services."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.services.memory_service import MemoryService
from app.services.retrieval_service import RetrievalService
from app.services.document_service import DocumentService
from app.core.config import settings


class TestEmbeddingService:
    """Test embedding service with deterministic fallback."""

    @pytest.mark.asyncio
    async def test_embed_text_returns_embedding(self):
        """Test that embed returns a valid embedding."""
        svc = EmbeddingService()
        text = "This is a test sentence"
        embedding = await svc.embed(text)

        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        # Embeddings are floats
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_embed_text_deterministic_fallback(self):
        """Test that fallback embeddings are deterministic."""
        svc = EmbeddingService()
        # Force fallback by setting client to None
        svc._client = None
        text = "Same test text"
        
        # Embed twice and compare
        emb1 = await svc.embed(text)
        emb2 = await svc.embed(text)
        
        # Should be identical if using fallback
        assert emb1 == emb2

    def test_deterministic_embedding_dimensions(self):
        """Test that deterministic embeddings have correct dimensions."""
        text = "Test content"
        embedding = EmbeddingService._deterministic_embedding(text, dimensions=64)
        
        assert len(embedding) == 64
        assert all(isinstance(x, float) for x in embedding)

    def test_deterministic_embedding_normalized(self):
        """Test that deterministic embeddings are normalized."""
        text = "Test content"
        embedding = EmbeddingService._deterministic_embedding(text, dimensions=64)
        
        # Check approximate normalization
        magnitude = sum(x * x for x in embedding) ** 0.5
        assert abs(magnitude - 1.0) < 0.01  # Allow small floating point error


class TestDocumentService:
    """Test document parsing and extraction."""

    @pytest.fixture
    def doc_service(self):
        """Provide a DocumentService instance with mock VectorStore."""
        mock_vector_store = Mock(spec=VectorStore)
        return DocumentService(mock_vector_store)

    def test_decode_text_utf8(self):
        """Test UTF-8 text decoding."""
        text = "Hello, World! 🚀"
        encoded = text.encode("utf-8")
        result = DocumentService._decode_text(encoded)
        assert result == text

    def test_decode_text_invalid_fallback_ignore(self):
        """Test fallback to ignore errors."""
        # Binary data that's not valid UTF-8
        binary_data = b'\xff\xfe\x00\x00Some text'
        result = DocumentService._decode_text(binary_data)
        # Should return something without raising an error
        assert isinstance(result, str)

    def test_validate_filename_allowed_extension(self):
        """Test that allowed extensions pass validation."""
        try:
            DocumentService._validate_filename("document.txt")
            DocumentService._validate_filename("data.csv")
            DocumentService._validate_filename("script.py")
        except ValueError:
            pytest.fail("Validation should pass for allowed extensions")

    def test_validate_filename_unsupported_extension(self):
        """Test that unsupported extensions raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported file extension"):
            DocumentService._validate_filename("file.exe")

    def test_validate_content_type_text(self):
        """Test text content type validation."""
        try:
            DocumentService._validate_content_type("text/plain")
            DocumentService._validate_content_type("text/markdown")
            DocumentService._validate_content_type("text/csv")
        except ValueError:
            pytest.fail("Should accept text/* types")

    def test_validate_content_type_invalid(self):
        """Test that invalid content types raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported content type"):
            DocumentService._validate_content_type("application/executable")

    def test_validate_content_type_with_charset(self):
        """Test content type with charset parameter."""
        try:
            DocumentService._validate_content_type("text/plain; charset=utf-8")
            DocumentService._validate_content_type("application/pdf")
        except ValueError:
            pytest.fail("Should handle content types with charset")


class TestMemoryService:
    """Test conversational memory service."""

    @pytest.fixture
    def memory_service(self):
        """Provide a MemoryService instance with mock VectorStore."""
        mock_vector_store = Mock(spec=VectorStore)
        return MemoryService(mock_vector_store)

    @pytest.mark.asyncio
    async def test_add_exchange_stores_message(self, memory_service):
        """Test that add_exchange stores user and assistant messages."""
        session_id = "test-session-123"
        user_query = "What is AI?"
        assistant_response = "AI is artificial intelligence."

        # Mock the vector store's upsert method
        memory_service.vector_store.upsert_text_chunks = AsyncMock()

        await memory_service.add_exchange(
            session_id=session_id,
            user_query=user_query,
            assistant_response=assistant_response,
        )

        # Verify the upsert was called
        assert memory_service.vector_store.upsert_text_chunks.called

    @pytest.mark.asyncio
    async def test_get_history_returns_messages(self, memory_service):
        """Test retrieving session history."""
        session_id = "test-session-456"
        
        # Mock the upsert
        memory_service.vector_store.upsert_text_chunks = AsyncMock()
        
        await memory_service.add_exchange(
            session_id=session_id,
            user_query="Hello?",
            assistant_response="Hi there!",
        )

        history = memory_service.get_history(session_id)
        
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[0].content == "Hello?"
        assert history[1].role == "assistant"
        assert history[1].content == "Hi there!"


class TestRetrievalService:
    """Test document retrieval service."""

    @pytest.fixture
    def retrieval_service(self):
        """Provide a RetrievalService instance."""
        mock_vector_store = Mock(spec=VectorStore)
        return RetrievalService(vector_store=mock_vector_store)

    @pytest.mark.asyncio
    async def test_retrieve_documents_returns_citations(self, retrieval_service):
        """Test that search returns proper citation format."""
        # Mock vector store search result
        retrieval_service.vector_store.ensure_seed_data = AsyncMock()
        retrieval_service.vector_store.search = AsyncMock(
            return_value=[
                {
                    "id": "doc-1",
                    "text": "Sample retrieved text",
                    "source": "uploaded-file.txt",
                    "score": 0.92,
                }
            ]
        )

        results = await retrieval_service.search(
            query="test query",
            limit=10,
        )

        assert len(results) > 0
        assert "text" in results[0]


class TestVectorStoreIntegration:
    """Test vector store integration."""

    @pytest.mark.asyncio
    async def test_vector_store_ensure_seed_data(self):
        """Test that seed data can be ensured."""
        embedding_service = EmbeddingService()
        store = VectorStore(embedding_service=embedding_service)
        
        # Should not raise any errors
        await store.ensure_seed_data()
        
        # Verify internal collection was created
        assert store._collection is not None

    @pytest.mark.asyncio
    async def test_vector_store_search(self):
        """Test basic search functionality."""
        embedding_service = EmbeddingService()
        store = VectorStore(embedding_service=embedding_service)
        
        await store.ensure_seed_data()

        # Search should return results
        results = await store.search(
            query="AI agent",
            limit=5,
        )

        assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

