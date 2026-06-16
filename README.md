# SuperAgent RAG

SuperAgent RAG is a scaffold for an agentic retrieval workflow with a Next.js 15 frontend and FastAPI backend. It streams workflow status, vector retrieval provenance, tool traces, and response tokens from Python to TypeScript.

## What Is Included

- Next.js 15, TypeScript, and Tailwind CSS frontend in `frontend/`.
- FastAPI backend in `backend/`.
- SSE streaming endpoint at `POST /api/query/stream`.
- Document upload endpoint at `POST /api/documents`.
- Session history endpoint at `GET /api/history/{session_id}`.
- File attachment flow for text-based documents that are chunked, embedded, and indexed for RAG answers.
- Gemini embedding integration boundary with a deterministic local fallback.
- Chroma-ready vector store boundary with local persisted fallback records.
- Composio orchestration boundary with mock traces until credentials and actions are configured.
- Architecture and streaming docs in `docs/`.

## Local Setup

This project targets Python 3.13+. If `python3.13 --version` fails, install Python 3.13 from the official Python macOS installer, then open a new terminal and try again.

Backend:

```bash
cd /Users/pearl/Desktop/projects/SuperAgent_RAG/backend
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
python -m uvicorn app.main:app --reload
```

Frontend:

```bash
cd /Users/pearl/Desktop/projects/SuperAgent_RAG/frontend
npm install
cp .env.example .env.local
npm run dev
```

If `npm` is not available, install Node.js first, then open a new terminal and rerun the frontend commands.

The frontend expects the backend at `http://localhost:8000` by default.

## Environment Variables

Backend:

- `GEMINI_API_KEY`: Enables live Gemini embeddings and LLM generation.
- `GEMINI_MODEL`: Text generation model. Defaults to `gemini-2.5-flash`.
- `GEMINI_EMBEDDING_MODEL`: Defaults to `models/text-embedding-004`.
- `COMPOSIO_API_KEY`: Enables live Composio integration work.
- `CHROMA_PERSIST_DIR`: Local vector persistence directory.
- `CHROMA_COLLECTION`: Target vector collection name.
- `FRONTEND_ORIGIN`: CORS origin for the frontend.

Frontend:

- `NEXT_PUBLIC_BACKEND_URL`: FastAPI server URL.

## Verification

Run backend tests after installing dependencies:

```bash
cd /Users/pearl/Desktop/projects/SuperAgent_RAG/backend
source .venv/bin/activate
python -m pytest app/tests
```

If you accidentally created a virtual environment in `/Users/pearl/Desktop/projects/.venv`, it is separate from this project and can be removed once you are sure you do not need it.

Manual check:

1. Start the backend.
2. Start the frontend.
3. Submit a query from the console.
4. Confirm status events, citations, tool traces, and answer tokens appear in real time.
5. Attach a text or markdown file and ask the system to summarize or answer questions from it.

## Next Build Steps

1. ~~Replace the response scaffold with a live LLM generation service.~~ ✅ Done — uses Gemini when `GEMINI_API_KEY` is set.
2. ~~Connect `VectorStore` to ChromaDB directly.~~ ✅ Done — ChromaDB used when installed.
3. ~~Add real Composio tool actions.~~ ✅ Done — uses Composio SDK when `COMPOSIO_API_KEY` is set.
4. Expand document extraction beyond text-like files, such as PDF and DOCX.
5. Persist memory beyond the current process.
