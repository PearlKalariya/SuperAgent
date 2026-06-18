# Deployment Guide

## Architecture Components

A typical production deployment of SuperAgent RAG requires:
- **Frontend App (Next.js):** Hosted on Vercel, AWS Amplify, or a Node.js server.
- **Backend API (FastAPI):** Hosted on a container platform (e.g., AWS ECS, Google Cloud Run, Fly.io, or Heroku).
- **Vector Database (ChromaDB):** For production, consider using ChromaDB deployed in client-server mode or a managed vector database (e.g., Pinecone, Weaviate) rather than local persistence.

## Environment Variables Configuration

Ensure the following secrets and variables are securely configured in your production environment:

**Backend:**
- `GEMINI_API_KEY`: Required for live embeddings and generation.
- `GEMINI_MODEL`: e.g., `gemini-2.5-flash`.
- `GEMINI_EMBEDDING_MODEL`: e.g., `models/text-embedding-004`.
- `COMPOSIO_API_KEY`: Required for external tool orchestration.
- `CHROMA_PERSIST_DIR`: Path to a persistent volume (if using local Chroma).
- `FRONTEND_ORIGIN`: Set to the exact URL of your production frontend (e.g., `https://app.superagent.com`) for CORS.

**Frontend:**
- `NEXT_PUBLIC_BACKEND_URL`: Set to the public URL of your FastAPI backend (e.g., `https://api.superagent.com`).

## Deployment Steps

### 1. Build and Deploy Backend (Docker approach)
Create a `Dockerfile` in the `backend/` directory:
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Deploy the container to your platform of choice, ensuring `FRONTEND_ORIGIN` is correctly set.

### 2. Build and Deploy Frontend
From the `frontend/` directory, run:
```bash
npm run build
npm start
```
Or connect the GitHub repository directly to Vercel for automated deployments. Ensure `NEXT_PUBLIC_BACKEND_URL` is set in the build settings.

## Performance & Security Notes

- **CORS:** Strictly configure `FRONTEND_ORIGIN` to prevent unauthorized domains from calling your API.
- **Rate Limiting:** Implement rate limiting (e.g., via a reverse proxy like Nginx or a cloud WAF) to protect the expensive LLM endpoints.
- **Streaming:** Ensure your hosting provider supports long-lived HTTP connections and SSE (e.g., some serverless environments have strict timeout limits).
- **Persistent Storage:** If using local ChromaDB (`CHROMA_PERSIST_DIR`), ensure the backend container has a persistent mounted volume; otherwise, your vector data will be lost on container restart.

## CI & Monitoring Recommendations
- Integrate the provided `.github/workflows/ci.yml` for automated backend testing on pull requests.
- Use an application performance monitoring (APM) tool like Datadog or Sentry to track workflow failures and tool orchestration latency.

## QA Release Checklist
- [ ] Confirm valid API keys are securely set in production environment variables.
- [ ] Verify `FRONTEND_ORIGIN` successfully blocks requests from unauthorized domains.
- [ ] Execute an end-to-end test query from the live frontend and confirm the answer streams without connection timeouts.
- [ ] Verify file upload limits and chunking performance on the live server.
- [ ] Test the fallback mechanisms by temporarily setting an invalid Composio API key and ensuring the workflow doesn't crash.