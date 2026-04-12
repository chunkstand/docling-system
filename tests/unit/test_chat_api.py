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


def test_chat_feedback_route_uses_chat_service(monkeypatch) -> None:
    answer_id = uuid4()
    feedback_id = uuid4()

    monkeypatch.setattr(
        "app.api.main.record_chat_answer_feedback",
        lambda session, chat_answer_id, payload: {
            "feedback_id": str(feedback_id),
            "chat_answer_id": str(chat_answer_id),
            "feedback_type": payload.feedback_type,
            "note": payload.note,
            "created_at": "2026-04-12T00:00:00Z",
        },
    )

    client = TestClient(app)
    response = client.post(
        f"/chat/answers/{answer_id}/feedback",
        json={"feedback_type": "helpful"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chat_answer_id"] == str(answer_id)
    assert body["feedback_type"] == "helpful"
