# Troubleshooting

Common issues and resolutions.

## Composio API Key (HTTP 410)
- Symptom: Backend logs `Composio initialisation failed — falling back to mocks.` and `ApiKeyError: Unexpected error: HTTP 410`.
- Cause: Invalid or expired `COMPOSIO_API_KEY` or the account lacks the expected resources.
- Fix: Set a valid `COMPOSIO_API_KEY` in backend `.env`, restart the backend. If you don't have an account, the project will run with mock tool traces.

## Gemini Embeddings / Model Errors
- Symptom: `google.genai.errors.ClientError: 404 NOT_FOUND` referencing `text-embedding-004`.
- Cause: The selected embedding model isn't available for the configured API version or the key lacks access.
- Fix: Update `GEMINI_EMBEDDING_MODEL` to a supported model, or remove `GEMINI_API_KEY` to use the deterministic fallback. Check the `google-genai` SDK docs for supported models.

## ChromaDB Issues
- Symptom: Failures connecting to ChromaDB, or missing collections.
- Fix: Ensure `chromadb` is installed in the backend venv, and set `CHROMA_PERSIST_DIR` to a writable path. For production, run a dedicated Chroma server or cloud vector DB.

## File Upload Failures
- Symptom: `Unsupported file extension` or `Uploaded file exceeds` errors.
- Fix: Check `settings.allowed_upload_extensions`, `MAX_UPLOAD_BYTES`, and ensure the upload `Content-Type` is allowed.

## Tests Failing Locally
- Fix: Activate virtualenv, run `pip install -e .[dev]`, then `python -m pytest app/tests`.

## Useful Commands

```bash
# Start backend
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload

# Run tests
python -m pytest -q
```
