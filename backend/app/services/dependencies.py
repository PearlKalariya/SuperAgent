from app.services.agent_service import AgentService
from app.services.composio_service import ComposioService
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.memory_service import MemoryService
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.orchestration_service import OrchestrationService
from app.services.response_service import ResponseService
from app.services.retrieval_service import RetrievalService
from app.services.vector_store import VectorStore

embedding_service = EmbeddingService()
vector_store = VectorStore(embedding_service=embedding_service)
memory_service = MemoryService(vector_store=vector_store)
query_understanding_service = QueryUnderstandingService()
retrieval_service = RetrievalService(vector_store=vector_store)
document_service = DocumentService(vector_store=vector_store)
composio_service = ComposioService()
orchestration_service = OrchestrationService()
response_service = ResponseService()

agent_service = AgentService(
    query_understanding=query_understanding_service,
    retrieval=retrieval_service,
    memory=memory_service,
    composio=composio_service,
    orchestration=orchestration_service,
    response=response_service,
)
