from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def test_search_request_evidence_package_route_uses_evidence_service(monkeypatch) -> None:
    request_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.get_search_evidence_package",
        lambda session, search_request_id: {
            "schema_name": "search_evidence_package",
            "schema_version": "1.0",
            "search_request": {"id": str(search_request_id), "query_text": "vent stack"},
            "operator_runs": [{"operator_kind": "retrieve"}],
            "results": [],
            "audit_checklist": {"has_retrieve_run": True},
        },
    )

    client = TestClient(app)
    response = client.get(f"/search/requests/{request_id}/evidence-package")

    assert response.status_code == 200
    assert response.json()["search_request"]["id"] == str(request_id)
    assert response.json()["operator_runs"][0]["operator_kind"] == "retrieve"


def test_search_request_evidence_package_route_returns_structured_404(monkeypatch) -> None:
    request_id = uuid4()

    def raise_not_found(session, search_request_id):
        raise ValueError(f"Search request '{search_request_id}' was not found.")

    monkeypatch.setattr("app.api.routers.search.get_search_evidence_package", raise_not_found)

    client = TestClient(app)
    response = client.get(f"/search/requests/{request_id}/evidence-package")

    assert response.status_code == 404
    assert response.json()["error_code"] == "search_request_not_found"
    assert response.json()["error_context"]["search_request_id"] == str(request_id)


def test_search_evidence_package_export_route_uses_evidence_service(monkeypatch) -> None:
    request_id = uuid4()
    export_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.export_search_evidence_package",
        lambda session, search_request_id: {
            "schema_name": "search_evidence_package_export",
            "schema_version": "1.0",
            "evidence_package_export_id": str(export_id),
            "search_request_id": str(search_request_id),
            "package_kind": "search_request",
            "package_sha256": "a" * 64,
            "trace_sha256": "b" * 64,
            "node_count": 3,
            "edge_count": 2,
            "trace_integrity": {"complete": True},
        },
    )

    client = TestClient(app)
    response = client.post(f"/search/requests/{request_id}/evidence-package/export")

    assert response.status_code == 200
    assert response.json()["evidence_package_export_id"] == str(export_id)
    assert response.json()["trace_integrity"]["complete"] is True


def test_search_evidence_package_export_route_returns_structured_404(monkeypatch) -> None:
    request_id = uuid4()

    def raise_not_found(session, search_request_id):
        raise ValueError(f"Search request '{search_request_id}' was not found.")

    monkeypatch.setattr("app.api.routers.search.export_search_evidence_package", raise_not_found)

    client = TestClient(app)
    response = client.post(f"/search/requests/{request_id}/evidence-package/export")

    assert response.status_code == 404
    assert response.json()["error_code"] == "search_request_not_found"
    assert response.json()["error_context"]["search_request_id"] == str(request_id)


def test_search_evidence_trace_route_uses_trace_service(monkeypatch) -> None:
    export_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.search.get_search_evidence_package_export_trace",
        lambda session, evidence_package_export_id: {
            "schema_name": "search_evidence_package_trace",
            "schema_version": "1.0",
            "evidence_package_export_id": str(evidence_package_export_id),
            "trace_sha256": "b" * 64,
            "node_count": 3,
            "edge_count": 2,
            "nodes": [],
            "edges": [],
            "trace_integrity": {"complete": True},
        },
    )

    client = TestClient(app)
    response = client.get(f"/search/evidence-package-exports/{export_id}/trace-graph")

    assert response.status_code == 200
    assert response.json()["evidence_package_export_id"] == str(export_id)
    assert response.json()["trace_integrity"]["complete"] is True


def test_search_evidence_trace_route_returns_structured_404(monkeypatch) -> None:
    export_id = uuid4()

    def raise_not_found(session, evidence_package_export_id):
        raise ValueError(
            f"Search evidence package export '{evidence_package_export_id}' was not found."
        )

    monkeypatch.setattr(
        "app.api.routers.search.get_search_evidence_package_export_trace",
        raise_not_found,
    )

    client = TestClient(app)
    response = client.get(f"/search/evidence-package-exports/{export_id}/trace-graph")

    assert response.status_code == 404
    assert response.json()["error_code"] == "search_evidence_package_export_not_found"
    assert response.json()["error_context"]["evidence_package_export_id"] == str(export_id)
