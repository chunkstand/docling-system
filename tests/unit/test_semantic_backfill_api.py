from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.main import app
from app.db.session import get_db_session
from app.schemas.semantic_backfill import (
    SemanticBackfillGraphStatus,
    SemanticBackfillReadiness,
    SemanticBackfillRegistryStatus,
    SemanticBackfillStatusResponse,
)


def _local_semantic_settings(*, enabled: bool) -> SimpleNamespace:
    return SimpleNamespace(
        api_mode="local",
        api_host="127.0.0.1",
        api_port=8000,
        api_key=None,
        api_credentials_json=None,
        remote_api_capabilities=None,
        semantics_enabled=enabled,
    )


def _override_db_session():
    yield object()


def test_semantic_backfill_status_route_returns_machine_readable_payload(monkeypatch) -> None:
    now = datetime.now(UTC)
    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: _local_semantic_settings(enabled=False),
    )
    monkeypatch.setattr(
        "app.api.main.get_semantic_backfill_status",
        lambda session: SemanticBackfillStatusResponse(
            semantics_enabled=False,
            active_document_count=2,
            active_run_count=2,
            current_registry=SemanticBackfillRegistryStatus(
                registry_name="portable_upper_ontology",
                registry_version="portable-upper-ontology-v1",
                concept_count=0,
                relation_count=4,
            ),
            graph=SemanticBackfillGraphStatus(),
            readiness=SemanticBackfillReadiness(
                ready=False,
                blocked_reasons=["Semantic execution is disabled."],
                next_actions=["Enable semantic execution."],
            ),
            updated_at=now,
        ),
    )
    app.dependency_overrides[get_db_session] = _override_db_session
    try:
        client = TestClient(app)
        response = client.get("/semantics/backfill/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["schema_name"] == "semantic_backfill_status"
    assert response.json()["active_document_count"] == 2
    assert response.json()["readiness"]["ready"] is False


def test_semantic_backfill_run_route_blocks_when_semantics_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: _local_semantic_settings(enabled=False),
    )
    app.dependency_overrides[get_db_session] = _override_db_session
    try:
        client = TestClient(app)
        response = client.post("/semantics/backfill", json={"limit": 1})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["error_code"] == "semantics_disabled"
