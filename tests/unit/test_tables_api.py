from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def test_document_tables_route_uses_table_service(monkeypatch) -> None:
    table_id = uuid4()
    document_id = uuid4()
    run_id = uuid4()
    now = datetime.now(UTC)

    def fake_get_active_tables(session, incoming_document_id):
        assert incoming_document_id == document_id
        return [
            {
                "table_id": str(table_id),
                "document_id": str(document_id),
                "run_id": str(run_id),
                "table_index": 0,
                "title": "TABLE 1 DATA GRID",
                "heading": "701.2 Drainage Piping",
                "page_from": 1,
                "page_to": 2,
                "row_count": 10,
                "col_count": 2,
                "preview_text": "Name | Value",
                "created_at": now.isoformat(),
            }
        ]

    monkeypatch.setattr("app.api.main.get_active_tables", fake_get_active_tables)

    client = TestClient(app)
    response = client.get(f"/documents/{document_id}/tables")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["table_id"] == str(table_id)
    assert body[0]["title"] == "TABLE 1 DATA GRID"


def test_document_table_detail_route_uses_table_service(monkeypatch) -> None:
    table_id = uuid4()
    document_id = uuid4()
    run_id = uuid4()
    now = datetime.now(UTC)

    def fake_get_active_table_detail(session, incoming_document_id, incoming_table_id):
        assert incoming_document_id == document_id
        assert incoming_table_id == table_id
        return {
            "table_id": str(table_id),
            "document_id": str(document_id),
            "run_id": str(run_id),
            "table_index": 0,
            "title": "TABLE 1 DATA GRID",
            "heading": "701.2 Drainage Piping",
            "page_from": 1,
            "page_to": 2,
            "row_count": 10,
            "col_count": 2,
            "preview_text": "Name | Value",
            "created_at": now.isoformat(),
            "has_json_artifact": True,
            "has_yaml_artifact": True,
            "metadata": {"segment_count": 2},
            "segments": [
                {
                    "segment_index": 0,
                    "source_table_ref": "#/tables/0",
                    "page_from": 1,
                    "page_to": 1,
                    "segment_order": 3,
                    "metadata": {"caption": "TABLE 1"},
                }
            ],
        }

    monkeypatch.setattr("app.api.main.get_active_table_detail", fake_get_active_table_detail)

    client = TestClient(app)
    response = client.get(f"/documents/{document_id}/tables/{table_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["table_id"] == str(table_id)
    assert body["has_json_artifact"] is True
    assert body["segments"][0]["source_table_ref"] == "#/tables/0"
