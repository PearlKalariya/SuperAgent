# SuperAgent RAG Architecture

## System Flow

1. The Next.js frontend sends a plain-English query to `POST /api/query/stream`.
2. FastAPI creates a workflow run and emits Server-Sent Events.
3. The agent service loads session memory, performs vector retrieval, invokes Composio tool actions, and streams answer tokens from Gemini.
4. The frontend progressively renders status, citations, tool traces, and the final response.
5. Conversation history is retained by session through the memory service.

Uploaded files enter through `POST /api/documents`, where text is extracted, chunked, embedded, and stored in the vector index. Later queries retrieve those chunks and cite the original filename.

## Backend Boundaries

- `api/`: FastAPI route definitions.
- `models/`: Shared response, streaming, citation, and workflow contracts.
- `services/agent_service.py`: Workflow coordinator.
- `services/embedding_service.py`: Gemini embedding boundary with deterministic local fallback.
- `services/vector_store.py`: ChromaDB-backed vector retrieval with deterministic local JSON fallback.
- `services/document_service.py`: Upload ingestion, text extraction, chunking, and indexing.
- `services/composio_service.py`: Composio SDK tool orchestration. Falls back to mock traces when `COMPOSIO_API_KEY` is not set.
- `services/memory_service.py`: Session-scoped chat memory.
- `services/response_service.py`: Gemini LLM generation with streaming. Falls back to deterministic scaffold answers when `GEMINI_API_KEY` is not set.

## Frontend Boundaries

- `app/page.tsx`: Main single-page console.
- `lib/api.ts`: Streaming API client and SSE parser.
- `lib/types.ts`: TypeScript mirror of backend event, citation, and trace contracts.

## Extension Points

- Register additional Composio actions in `ComposioService._live_actions`.
- Add persistent database-backed memory for multi-user sessions.
- Expand document extraction to PDF and DOCX formats.
- Add authentication and per-user session isolation.
