# Server-Sent Events (SSE) API Contract

The primary communication channel for query responses is the `POST /api/query/stream` endpoint, which streams workflow events.

## Request Format

```json
{
  "query": "What is the capital of France?",
  "session_id": "optional-session-uuid"
}
```

## Event Types

- `run_started`: Emitted when the workflow initializes.
- `status`: Provides human-readable progress updates (e.g., "Searching knowledge base...").
- `retrieval_started`: Emitted before vector search begins.
- `retrieval_result`: Emitted after search, containing citations and similarity scores.
- `tool_call_started`: Emitted when an external tool or action is invoked.
- `tool_call_result`: Emitted when the tool finishes, containing the tool's output and execution trace.
- `token`: Streamed chunk of the LLM's generated response.
- `citation`: Emitted for individual sources used to inform the final answer.
- `error`: Emitted if a non-fatal workflow error occurs (e.g., retrieval failure).
- `run_completed`: Signals the end of the SSE stream.

## Example Event Stream

```text
event: run_started
data: {"session_id": "123", "timestamp": "2026-06-18T06:16:00Z"}

event: status
data: {"message": "Thinking..."}

event: retrieval_result
data: {"citations": [{"source": "notes.txt", "score": 0.95}]}

event: token
data: {"text": "The"}

event: token
data: {"text": " capital"}

event: run_completed
data: {"status": "success"}
```