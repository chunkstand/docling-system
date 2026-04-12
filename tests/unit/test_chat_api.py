from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def test_chat_route_uses_answer_service(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()

    monkeypatch.setattr(
        "app.api.main.answer_question",
        lambda session, request: {
            "answer": "Vent sizing is covered in the retrieved chapter text [1].",
            "citations": [
                {
                    "citation_index": 1,
                    "result_type": "chunk",
                    "document_id": str(document_id),
                    "run_id": str(run_id),
                    "source_filename": "UPC_CH_5.pdf",
                    "page_from": 12,
                    "page_to": 12,
                    "label": "Venting",
                    "excerpt": "Plastic vent joints shall be installed...",
                    "score": 0.91,
                }
            ],
            "mode": "hybrid",
            "model": "gpt-4.1-mini",
            "used_fallback": False,
            "warning": None,
        },
    )

    client = TestClient(app)
    response = client.post("/chat", json={"question": "How are plastic vent joints handled?"})

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "hybrid"
    assert body["used_fallback"] is False
    assert body["citations"][0]["source_filename"] == "UPC_CH_5.pdf"
