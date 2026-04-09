from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def test_search_route_uses_search_service(monkeypatch) -> None:
    chunk_id = uuid4()
    document_id = uuid4()
    run_id = uuid4()

    def fake_search_chunks(session, request):
        return [
            {
                "chunk_id": str(chunk_id),
                "document_id": str(document_id),
                "run_id": str(run_id),
                "score": 0.9,
                "chunk_text": "hello",
                "heading": "Heading",
                "page_from": 1,
                "page_to": 1,
                "source_filename": "report.pdf",
                "scores": {
                    "keyword_score": 0.4,
                    "semantic_score": 0.8,
                    "hybrid_score": 0.9,
                },
            }
        ]

    monkeypatch.setattr("app.api.main.search_chunks", fake_search_chunks)

    client = TestClient(app)
    response = client.post("/search", json={"query": "hello", "mode": "hybrid", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body[0]["chunk_id"] == str(chunk_id)
    assert body[0]["scores"]["hybrid_score"] == 0.9
