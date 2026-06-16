from fastapi.testclient import TestClient

from app.api import query as query_api
from app.main import app


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
    response = client.post(
        "/api/documents",
        files={"file": ("notes.md", b"# Notes\nThis file explains uploaded RAG context.", "text/markdown")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "notes.md"
    assert payload["chunks_indexed"] >= 1
    assert payload["characters_indexed"] >= 1
