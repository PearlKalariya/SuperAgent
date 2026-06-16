# Streaming Event Contract

The query stream endpoint is:

```http
POST /api/query/stream
Content-Type: application/json
Accept: text/event-stream
```

Request body:

```json
{
  "query": "Show me how this workflow runs",
  "session_id": "session-123"
}
```

Every SSE message includes a JSON payload with:

- `run_id`
- `session_id`
- `type`
- `timestamp`
- `payload`

## Event Types

- `run_started`: A new workflow run has begun.
- `status`: Human-readable progress update.
- `retrieval_started`: Vector retrieval is starting.
- `retrieval_result`: Retrieval finished with citation metadata.
- `tool_call_started`: Tool orchestration is starting.
- `tool_call_result`: Tool orchestration finished with trace details.
- `token`: A streamed response token.
- `citation`: A single citation/provenance object.
- `error`: A recoverable workflow error.
- `run_completed`: Final answer and complete metadata.
