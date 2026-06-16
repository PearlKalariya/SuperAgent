# SuperAgent RAG Implementation Plan

## Objective

Build a modular agentic RAG platform with a Next.js 15 frontend and FastAPI backend. The system should accept natural-language queries, stream multi-step agent progress to the UI, retrieve context using Gemini embeddings and ChromaDB, and orchestrate external tool calls through Composio.

## Milestones

1. Project foundation
2. Backend API and streaming workflow
3. Embeddings, retrieval, and memory
4. Composio tool orchestration
5. Frontend query and streaming UI
6. File attachment and document ingestion
7. End-to-end integration and verification
8. Documentation and polish

## Phase 1: Project Foundation

### Tasks

- Create a monorepo-style structure:
  - `frontend/` for the Next.js 15 application.
  - `backend/` for the FastAPI application.
  - `docs/` for architecture and integration notes.
- Add environment variable templates for required secrets and URLs:
  - `GEMINI_API_KEY`
  - `COMPOSIO_API_KEY`
  - `CHROMA_HOST` or local Chroma path
  - `NEXT_PUBLIC_BACKEND_URL`
- Add basic development scripts for frontend, backend, formatting, and tests.
- Document local setup requirements for Node, Python 3.13+, and ChromaDB.

### Deliverables

- Working project folder structure.
- `.env.example` files for frontend and backend.
- Basic README setup instructions.

## Phase 2: Backend API and Streaming Workflow

### Tasks

- Scaffold a FastAPI app with routes for:
  - `GET /health`
  - `POST /api/query`
  - `GET /api/history/{session_id}`
  - `GET /api/stream/{run_id}` or a direct SSE query endpoint
- Define backend models for:
  - User query
  - Workflow step
  - Tool call trace
  - Retrieval citation
  - Streaming response event
- Implement SSE streaming for agent progress and final responses.
- Add a service layer with clear module boundaries:
  - query understanding
  - retrieval
  - memory
  - orchestration
  - response generation
- Add structured error handling for failed retrieval, embedding, and tool-call steps.

### Deliverables

- FastAPI server starts locally.
- Health check works.
- Query endpoint returns or streams placeholder workflow events.

## Phase 3: Embeddings, Retrieval, and Memory

### Tasks

- Integrate Gemini embeddings for text encoding.
- Configure ChromaDB client and collection management.
- Implement document ingestion helpers for future knowledge-base content.
- Implement file upload ingestion for user-provided text documents.
- Implement retrieval functions that return:
  - matched text chunks
  - source metadata
  - similarity scores
  - citation IDs
- Implement conversational memory:
  - store user queries and assistant responses
  - retrieve relevant previous context by session
  - include memory provenance in workflow traces
- Add tests or scripts to verify embeddings are generated and stored.

### Deliverables

- ChromaDB collection is created automatically.
- Backend can embed, store, and retrieve text.
- Uploaded files are chunked, embedded, and retrievable.
- Query workflow includes retrieved context and citation metadata.

## Phase 3.5: File Attachment and Document Ingestion

### Tasks

- Add a FastAPI multipart upload route for text-based files.
- Extract readable text from uploaded files.
- Chunk uploaded content with overlap for retrieval quality.
- Embed each chunk and store it in ChromaDB or the local vector fallback.
- Preserve filename, content type, document ID, and chunk index as citation metadata.
- Add frontend upload controls near the query input.
- Display indexed files and chunk counts in the UI.

### Deliverables

- Users can attach a file from the UI.
- The backend indexes uploaded file chunks.
- Later queries can retrieve uploaded content and cite the source file.

## Phase 4: Composio Tool Orchestration

### Tasks

- Add a Composio integration service.
- Define a tool adapter interface so tools can be swapped or extended.
- Implement initial tool categories:
  - knowledge-base retrieval
  - memory lookup
  - custom backend function calls
  - external API calls through Composio
- Capture trace data for every tool call:
  - tool name
  - input
  - output summary
  - status
  - timing
  - errors
- Ensure orchestration supports multi-step workflows with intermediate outputs.

### Deliverables

- Composio can invoke at least one external or mocked tool.
- Tool-call traces appear in backend workflow events.
- Failed tool calls are reported without crashing the whole workflow.

## Phase 5: Frontend Query and Streaming UI

### Tasks

- Scaffold a Next.js 15 app with TypeScript and Tailwind CSS.
- Build the main single-page agent interface:
  - query input
  - submit and stop controls
  - streamed response area
  - agent status indicator
  - citations/provenance section
  - tool-call/result sections
- Implement a TypeScript API client for backend calls.
- Implement SSE event handling and progressive rendering.
- Add responsive layout behavior for desktop and mobile.
- Ensure keyboard-friendly controls:
  - submit with Enter
  - multiline input support
  - visible focus states

### Deliverables

- Frontend renders a usable query interface.
- Streaming backend events appear live in the UI.
- Citations and tool traces are displayed clearly.

## Phase 6: End-to-End Integration and Verification

### Tasks

- Connect frontend query submission to FastAPI workflow execution.
- Verify streamed event types across the TypeScript/Python boundary.
- Run an end-to-end sample workflow:
  - user enters a plain-English query
  - backend parses the query
  - memory and vector retrieval run
  - Composio or a mocked external tool is invoked
  - final answer streams to the UI
  - citations and traces are shown
- Add focused tests for:
  - backend route contracts
  - retrieval service
  - streaming event serialization
  - frontend API client/event parser
- Add a manual QA checklist.

### Deliverables

- End-to-end query flow works locally.
- Verification checklist from `TASK_REQUIREMENTS.md` is satisfied.
- Known limitations are documented.

## Phase 7: Documentation and Polish

### Tasks

- Update `README.md` with:
  - overview
  - local setup
  - environment variables
  - frontend/backend commands
  - verification steps
- Add architecture documentation covering:
  - frontend/backend data flow
  - SSE event contract
  - service boundaries
  - retrieval and memory design
  - Composio tool orchestration design
- Add example requests and expected response events.
- Add troubleshooting notes for Gemini, ChromaDB, Composio, and CORS issues.

### Deliverables

- Clear setup and architecture docs.
- Future contributors can extend agents, tools, and retrieval components.

## Suggested Repository Structure

```text
SuperAgent_RAG/
  frontend/
    app/
    components/
    lib/
    package.json
    .env.example
  backend/
    app/
      api/
      core/
      models/
      services/
      tests/
      main.py
    pyproject.toml
    .env.example
  docs/
    architecture.md
    streaming-events.md
  TASK_REQUIREMENTS.md
  IMPLEMENTATION_PLAN.md
  README.md
```

## Backend Module Plan

```text
backend/app/
  main.py
  api/
    health.py
    query.py
    history.py
  core/
    config.py
    logging.py
    errors.py
  models/
    query.py
    workflow.py
    streaming.py
    citations.py
  services/
    agent_service.py
    embedding_service.py
    vector_store.py
    memory_service.py
    composio_service.py
    retrieval_service.py
    response_service.py
```

## Streaming Event Contract

Initial event types should include:

- `run_started`
- `status`
- `retrieval_started`
- `retrieval_result`
- `tool_call_started`
- `tool_call_result`
- `token`
- `citation`
- `error`
- `run_completed`

Each event should include:

- `run_id`
- `session_id`
- `type`
- `timestamp`
- `payload`

## Verification Checklist

- Frontend renders a responsive query interface.
- Backend exposes FastAPI health and query routes.
- Query responses stream to the frontend.
- Gemini embeddings are generated for memory or retrieval content.
- ChromaDB stores and retrieves vectors.
- Composio handles at least one tool invocation path.
- Responses include source metadata or retrieval provenance when applicable.
- Architecture and setup are documented.

## Recommended Build Order

1. Scaffold backend and frontend.
2. Implement backend placeholder streaming.
3. Build frontend streaming UI against placeholder events.
4. Add Gemini embeddings and ChromaDB retrieval.
5. Add memory service.
6. Add Composio tool orchestration.
7. Replace placeholders with real workflow events.
8. Add tests, docs, and manual verification.
