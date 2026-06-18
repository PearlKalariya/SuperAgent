# Architecture

SuperAgent RAG is built as a modular application split between a Next.js 15 frontend and a FastAPI Python backend.

## Frontend-Backend Data Flow

1. **User Input:** The user submits a query via the Next.js UI.
2. **API Request:** The Next.js API client sends a POST request with the query and a unique `session_id` to the FastAPI backend.
3. **Agent Orchestration:** 
   - The FastAPI backend receives the request and initializes the agent workflow.
   - The backend uses Server-Sent Events (SSE) to stream updates (e.g., status changes, tool execution traces, retrieved citations, and generated tokens) back to the frontend.
4. **Progressive Rendering:** The frontend parses the SSE events and progressively renders the response, citations, and agent state.

## Service Boundaries

The backend is composed of several decoupled services:

- **Agent Service:** Orchestrates the multi-step workflow, combining retrieval, memory, tool use, and response generation.
- **Embedding Service:** Integrates with Gemini (or falls back to a deterministic method) to encode text into vector representations.
- **Vector Store:** Manages communication with ChromaDB for storing and searching vector embeddings.
- **Document Service:** Handles file uploads, text extraction, chunking, and indexing.
- **Memory Service:** Stores conversation history into the vector store, scoped by `session_id`, allowing the agent to recall past context semantically.
- **Retrieval Service:** Queries the vector store for context relevant to the user's input, returning ranked citations.
- **Orchestration Service:** Integrates with Composio to execute external tools and track their traces.

## Retrieval and Memory Design

Documents and conversational history are treated uniformly as semantic knowledge:
- **Documents:** Text extracted from uploaded files is chunked, embedded, and indexed.
- **Memory:** Exchanges (user query + assistant response) are embedded and indexed with a `session_id` and a `kind="conversation_memory"` metadata tag.
- **Search:** The retrieval service can pull from both documents and past conversation turns to ground the LLM's answers.