import asyncio
import uuid

from fastapi.testclient import TestClient

from app.api import query as query_api
from app.main import app
from app.services.dependencies import embedding_service, vector_store


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_query_response() -> None:
    response = client.post("/api/query", json={"query": "How does retrieval work?", "session_id": "test"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"]
    assert payload["citations"]
    assert payload["tool_traces"]


def test_query_validation_rejects_empty_query() -> None:
    response = client.post("/api/query", json={"query": "", "session_id": "test"})
    assert response.status_code == 422


def test_history_response_tracks_query_exchange() -> None:
    session_id = "history-test"
    response = client.post(
        "/api/query",
        json={"query": "Remember this retrieval question", "session_id": session_id},
    )
    assert response.status_code == 200

    history_response = client.get(f"/api/history/{session_id}")
    assert history_response.status_code == 200
    payload = history_response.json()
    assert payload["session_id"] == session_id
    assert [message["role"] for message in payload["messages"][-2:]] == ["user", "assistant"]


def test_stream_query_response() -> None:
    with client.stream(
        "POST",
        "/api/query/stream",
        json={"query": "Stream a workflow update", "session_id": "stream-test"},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert "event: run_started" in body
    assert "Structured query for retrieval" in body
    assert "event: retrieval_result" in body
    assert "event: tool_call_result" in body
    assert "event: token" in body
    assert "event: run_completed" in body


def test_stream_query_returns_error_event_on_workflow_failure(monkeypatch) -> None:
    async def fail_search(query: str):
        raise RuntimeError("retrieval failed")

    monkeypatch.setattr(query_api.agent_service.retrieval, "search", fail_search)

    with client.stream(
        "POST",
        "/api/query/stream",
        json={"query": "Trigger retrieval failure", "session_id": "error-test"},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert "event: run_started" in body
    assert "event: error" in body
    assert "retrieval failed" in body


def test_document_upload_indexes_file() -> None:
    source_name = "notes.md"
    response = client.post(
        "/api/documents",
        files={
            "file": (
                source_name,
                b"# Notes\nThis file explains uploaded RAG context with phase three retrieval.",
                "text/markdown",
            )
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == source_name
    assert payload["chunks_indexed"] >= 1
    assert payload["characters_indexed"] >= 1

    indexed_chunks = asyncio.run(vector_store.count({"document_id": payload["document_id"]}))
    assert indexed_chunks == payload["chunks_indexed"]


def test_embedding_service_returns_vector() -> None:
    embedding = asyncio.run(embedding_service.embed("semantic retrieval smoke test"))
    assert embedding
    assert all(isinstance(value, float) for value in embedding)


def test_uploaded_document_is_retrieved_as_citation() -> None:
    filename = "retrieval-notes.md"
    session_id = f"uploaded-doc-test-{uuid.uuid4().hex}"
    client.post(
        "/api/documents",
        files={
            "file": (
                filename,
                b"orchid-vector-memory is the special phrase for uploaded document retrieval.",
                "text/markdown",
            )
        },
    )

    response = client.post(
        "/api/query",
        json={"query": "What mentions orchid-vector-memory?", "session_id": session_id},
    )
    assert response.status_code == 200
    citations = response.json()["citations"]
    assert any(citation["source"] == filename for citation in citations)
    assert all(citation["metadata"].get("kind") != "conversation_memory" for citation in citations)


def test_conversation_memory_is_retrieved_as_citation() -> None:
    session_id = "semantic-memory-test"
    first_response = client.post(
        "/api/query",
        json={
            "query": "Remember that sapphire-memory-token belongs to the deployment notes.",
            "session_id": session_id,
        },
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/api/query",
        json={"query": "What did I say about sapphire-memory-token?", "session_id": session_id},
    )
    assert second_response.status_code == 200
    citations = second_response.json()["citations"]
    assert any(citation["metadata"].get("kind") == "conversation_memory" for citation in citations)


def test_conversation_memory_is_scoped_to_session() -> None:
    secret_session = "secret-memory-session"
    public_session = "public-memory-session"
    secret_phrase = "private-session-only-token"

    first_response = client.post(
        "/api/query",
        json={
            "query": f"Remember {secret_phrase} for only this chat.",
            "session_id": secret_session,
        },
    )
    assert first_response.status_code == 200

    same_session_response = client.post(
        "/api/query",
        json={"query": f"What did I say about {secret_phrase}?", "session_id": secret_session},
    )
    assert same_session_response.status_code == 200
    same_session_citations = same_session_response.json()["citations"]
    assert any(
        citation["metadata"].get("kind") == "conversation_memory"
        and citation["metadata"].get("session_id") == secret_session
        for citation in same_session_citations
    )

    other_session_response = client.post(
        "/api/query",
        json={"query": f"What did I say about {secret_phrase}?", "session_id": public_session},
    )
    assert other_session_response.status_code == 200
    other_session_citations = other_session_response.json()["citations"]
    assert all(
        citation["metadata"].get("session_id") != secret_session
        for citation in other_session_citations
    )


def test_document_upload_rejects_unsupported_extension() -> None:
    response = client.post(
        "/api/documents",
        files={"file": ("payload.exe", b"not really executable", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.text


def test_document_upload_rejects_binary_content() -> None:
    response = client.post(
        "/api/documents",
        files={"file": ("payload.txt", b"hello\x00world", "text/plain")},
    )
    assert response.status_code == 400
    assert "Binary files" in response.text
