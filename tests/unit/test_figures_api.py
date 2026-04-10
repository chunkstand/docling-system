from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def test_document_figures_route_uses_figure_service(monkeypatch) -> None:
    figure_id = uuid4()
    document_id = uuid4()
    run_id = uuid4()
    now = datetime.now(timezone.utc)

    def fake_get_active_figures(session, incoming_document_id):
        assert incoming_document_id == document_id
        return [
            {
                "figure_id": str(figure_id),
                "document_id": str(document_id),
                "run_id": str(run_id),
                "figure_index": 0,
                "source_figure_ref": "#/pictures/0",
                "caption": "Fixture Venting Diagram",
                "heading": "702.2 Intermittent Flow",
                "page_from": 10,
                "page_to": 10,
                "confidence": 0.7,
                "created_at": now.isoformat(),
            }
        ]

    monkeypatch.setattr("app.api.main.get_active_figures", fake_get_active_figures)

    client = TestClient(app)
    response = client.get(f"/documents/{document_id}/figures")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["figure_id"] == str(figure_id)
    assert body[0]["caption"] == "Fixture Venting Diagram"


def test_document_figure_detail_route_uses_figure_service(monkeypatch) -> None:
    figure_id = uuid4()
    document_id = uuid4()
    run_id = uuid4()
    now = datetime.now(timezone.utc)

    def fake_get_active_figure_detail(session, incoming_document_id, incoming_figure_id):
        assert incoming_document_id == document_id
        assert incoming_figure_id == figure_id
        return {
            "figure_id": str(figure_id),
            "document_id": str(document_id),
            "run_id": str(run_id),
            "figure_index": 0,
            "source_figure_ref": "#/pictures/0",
            "caption": "Fixture Venting Diagram",
            "heading": "702.2 Intermittent Flow",
            "page_from": 10,
            "page_to": 10,
            "confidence": 0.7,
            "created_at": now.isoformat(),
            "has_json_artifact": True,
            "has_yaml_artifact": True,
            "status": "validated",
            "metadata": {
                "caption_resolution_source": "nearby_text",
                "provenance": [{"page_no": 10}],
            },
        }

    monkeypatch.setattr("app.api.main.get_active_figure_detail", fake_get_active_figure_detail)

    client = TestClient(app)
    response = client.get(f"/documents/{document_id}/figures/{figure_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["figure_id"] == str(figure_id)
    assert body["has_json_artifact"] is True
    assert body["metadata"]["caption_resolution_source"] == "nearby_text"
