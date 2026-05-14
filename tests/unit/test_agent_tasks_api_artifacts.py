from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app
from app.db.session import get_db_session
from app.services.storage import StorageService


def test_agent_task_context_route_supports_json_and_yaml(monkeypatch) -> None:
    task_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.get_agent_task_context",
        lambda session, incoming_task_id: {
            "task_id": str(incoming_task_id),
            "task_type": "draft_harness_config_update",
            "task_status": "completed",
            "workflow_version": "v1",
            "generated_at": "2026-04-15T00:00:00Z",
            "task_updated_at": "2026-04-15T00:00:00Z",
            "schema_name": "agent_task_context",
            "schema_version": "1.0",
            "output_schema_name": "draft_harness_config_update_output",
            "output_schema_version": "1.0",
            "freshness_status": "fresh",
            "summary": {"headline": "Draft ready"},
            "refs": [
                {
                    "ref_key": "draft_task_output",
                    "ref_kind": "task_output",
                    "task_id": str(incoming_task_id),
                    "freshness_status": "fresh",
                }
            ],
            "output": {"artifact_kind": "harness_config_draft"},
        },
    )

    client = TestClient(app)

    json_response = client.get(f"/agent-tasks/{task_id}/context")
    assert json_response.status_code == 200
    assert json_response.json()["task_type"] == "draft_harness_config_update"
    assert json_response.json()["freshness_status"] == "fresh"
    assert json_response.json()["refs"][0]["freshness_status"] == "fresh"

    yaml_response = client.get(f"/agent-tasks/{task_id}/context?format=yaml")
    assert yaml_response.status_code == 200
    assert "agent_task_context" in yaml_response.text


def test_agent_task_audit_bundle_route_uses_audit_service(monkeypatch) -> None:
    task_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.get_agent_task_audit_bundle",
        lambda session, incoming_task_id: {
            "schema_name": "technical_report_audit_bundle",
            "task": {"task_id": str(incoming_task_id)},
            "evidence_package_exports": [{"package_sha256": "abc"}],
            "claim_derivations": [{"claim_id": "claim:1"}],
            "audit_checklist": {"has_frozen_evidence_package": True},
        },
    )

    client = TestClient(app)
    response = client.get(f"/agent-tasks/{task_id}/audit-bundle")

    assert response.status_code == 200
    assert response.json()["schema_name"] == "technical_report_audit_bundle"
    assert response.json()["task"]["task_id"] == str(task_id)
    assert response.json()["audit_checklist"]["has_frozen_evidence_package"] is True


def test_agent_task_audit_bundle_route_returns_structured_404(monkeypatch) -> None:
    task_id = uuid4()

    def raise_not_found(session, incoming_task_id):
        raise ValueError(f"Agent task '{incoming_task_id}' was not found.")

    monkeypatch.setattr("app.api.routers.agent_tasks.get_agent_task_audit_bundle", raise_not_found)

    client = TestClient(app)
    response = client.get(f"/agent-tasks/{task_id}/audit-bundle")

    assert response.status_code == 404
    assert response.json()["error_code"] == "agent_task_audit_bundle_not_found"
    assert response.json()["error_context"]["task_id"] == str(task_id)


def test_agent_task_evidence_manifest_route_uses_manifest_service(monkeypatch) -> None:
    task_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.get_agent_task_evidence_manifest",
        lambda session, incoming_task_id: {
            "schema_name": "technical_report_evidence_manifest",
            "task": {"task_id": str(incoming_task_id)},
            "manifest_sha256": "abc",
            "audit_checklist": {"complete": True},
        },
    )

    client = TestClient(app)
    response = client.get(f"/agent-tasks/{task_id}/evidence-manifest")

    assert response.status_code == 200
    assert response.json()["schema_name"] == "technical_report_evidence_manifest"
    assert response.json()["task"]["task_id"] == str(task_id)
    assert response.json()["audit_checklist"]["complete"] is True


def test_agent_task_evidence_manifest_route_returns_structured_404(monkeypatch) -> None:
    task_id = uuid4()

    def raise_not_found(session, incoming_task_id):
        raise ValueError(f"Agent task '{incoming_task_id}' was not found.")

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.get_agent_task_evidence_manifest",
        raise_not_found,
    )

    client = TestClient(app)
    response = client.get(f"/agent-tasks/{task_id}/evidence-manifest")

    assert response.status_code == 404
    assert response.json()["error_code"] == "agent_task_evidence_manifest_not_found"
    assert response.json()["error_context"]["task_id"] == str(task_id)


def test_agent_task_evidence_trace_route_uses_trace_service(monkeypatch) -> None:
    task_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.get_agent_task_evidence_trace",
        lambda session, incoming_task_id: {
            "schema_name": "technical_report_evidence_trace",
            "evidence_manifest_id": str(uuid4()),
            "manifest_sha256": "abc",
            "trace_sha256": "def",
            "node_count": 1,
            "edge_count": 1,
            "trace_integrity": {"complete": True},
        },
    )

    client = TestClient(app)
    response = client.get(f"/agent-tasks/{task_id}/evidence-trace")

    assert response.status_code == 200
    assert response.json()["schema_name"] == "technical_report_evidence_trace"
    assert response.json()["trace_integrity"]["complete"] is True


def test_agent_task_evidence_trace_route_returns_structured_404(monkeypatch) -> None:
    task_id = uuid4()

    def raise_not_found(session, incoming_task_id):
        raise ValueError(f"Agent task '{incoming_task_id}' was not found.")

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.get_agent_task_evidence_trace",
        raise_not_found,
    )

    client = TestClient(app)
    response = client.get(f"/agent-tasks/{task_id}/evidence-trace")

    assert response.status_code == 404
    assert response.json()["error_code"] == "agent_task_evidence_trace_not_found"
    assert response.json()["error_context"]["task_id"] == str(task_id)


def test_agent_task_provenance_route_uses_provenance_service(monkeypatch) -> None:
    task_id = uuid4()

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.get_agent_task_provenance_export",
        lambda session, incoming_task_id, *, storage_service: {
            "schema_name": "technical_report_prov_export",
            "task_id": str(incoming_task_id),
            "entity": {"docling:documents/1": {"prov:type": "docling:SourceDocument"}},
            "activity": {"docling:agent-tasks/1": {"prov:type": "docling:AgentTask"}},
            "frozen_export": {"storage_path": str(storage_service.storage_root)},
            "prov_integrity": {"complete": True},
        },
    )

    client = TestClient(app)
    response = client.get(f"/agent-tasks/{task_id}/provenance")

    assert response.status_code == 200
    assert response.json()["schema_name"] == "technical_report_prov_export"
    assert response.json()["task_id"] == str(task_id)
    assert response.json()["prov_integrity"]["complete"] is True


def test_agent_task_provenance_route_returns_structured_404(monkeypatch) -> None:
    task_id = uuid4()

    def raise_not_found(session, incoming_task_id, *, storage_service):
        raise ValueError(f"Agent task '{incoming_task_id}' was not found.")

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.get_agent_task_provenance_export",
        raise_not_found,
    )

    client = TestClient(app)
    response = client.get(f"/agent-tasks/{task_id}/provenance")

    assert response.status_code == 404
    assert response.json()["error_code"] == "agent_task_provenance_not_found"
    assert response.json()["error_context"]["task_id"] == str(task_id)


def test_agent_task_failure_artifact_route_returns_404_when_missing(monkeypatch) -> None:
    task_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.agent_tasks.get_agent_task_detail",
        lambda session, incoming_task_id: {
            "task_id": str(incoming_task_id),
            "task_type": "triage_replay_regression",
            "status": "failed",
            "priority": 100,
            "side_effect_level": "read_only",
            "requires_approval": False,
            "parent_task_id": None,
            "workflow_version": "v1",
            "tool_version": None,
            "prompt_version": None,
            "model": None,
            "created_at": "2026-04-12T00:00:00Z",
            "updated_at": "2026-04-12T00:00:00Z",
            "started_at": None,
            "completed_at": None,
            "dependency_task_ids": [],
            "input": {},
            "result": {},
            "model_settings": {},
            "error_message": "failed",
            "failure_artifact_path": None,
            "attempts": 1,
            "locked_at": None,
            "locked_by": None,
            "last_heartbeat_at": None,
            "next_attempt_at": None,
            "approved_at": None,
            "approved_by": None,
            "approval_note": None,
            "artifact_count": 0,
            "attempt_count": 1,
            "verification_count": 0,
            "artifacts": [],
            "verifications": [],
        },
    )

    client = TestClient(app)
    response = client.get(f"/agent-tasks/{task_id}/failure-artifact")

    assert response.status_code == 404
    assert response.json()["error_code"] == "agent_task_failure_artifact_not_found"


def test_agent_task_context_route_returns_machine_readable_error_when_task_missing() -> None:
    task_id = uuid4()

    class FakeSession:
        def get(self, _model, _key):
            return None

        def close(self) -> None:
            return None

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/agent-tasks/{task_id}/context")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "agent_task_not_found"


def test_agent_task_context_route_returns_machine_readable_error_when_context_missing() -> None:
    task_id = uuid4()

    class FakeScalarResult:
        def first(self):
            return None

    class FakeExecuteResult:
        def scalars(self):
            return FakeScalarResult()

    class FakeSession:
        def get(self, _model, _key):
            return object()

        def execute(self, _statement):
            return FakeExecuteResult()

        def close(self) -> None:
            return None

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/agent-tasks/{task_id}/context")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "agent_task_context_not_found"


def test_agent_task_artifacts_route_returns_machine_readable_error_when_task_missing() -> None:
    task_id = uuid4()

    class FakeSession:
        def get(self, _model, _key):
            return None

        def close(self) -> None:
            return None

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/agent-tasks/{task_id}/artifacts")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "agent_task_not_found"


def test_agent_task_verifications_route_returns_machine_readable_error_when_task_missing() -> None:
    task_id = uuid4()

    class FakeSession:
        def get(self, _model, _key):
            return None

        def close(self) -> None:
            return None

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/agent-tasks/{task_id}/verifications")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "agent_task_not_found"


def test_agent_task_artifact_route_does_not_serve_paths_outside_storage_root(
    monkeypatch, tmp_path: Path
) -> None:
    task_id = uuid4()
    artifact_id = uuid4()
    storage_service = StorageService(storage_root=tmp_path / "storage")
    outside_path = tmp_path / "outside.json"
    outside_path.write_text('{"should":"not-serve"}')

    monkeypatch.setattr("app.api.deps.get_storage_service", lambda: storage_service)
    monkeypatch.setattr("app.api.routers.agent_tasks.get_storage_service", lambda: storage_service)
    monkeypatch.setattr(
        "app.api.routers.agent_tasks.get_agent_task_artifact",
        lambda session, incoming_task_id, incoming_artifact_id: type(
            "ArtifactRow",
            (),
            {
                "id": incoming_artifact_id,
                "task_id": incoming_task_id,
                "storage_path": str(outside_path),
                "payload_json": {"fallback": True},
            },
        )(),
    )

    client = TestClient(app)
    response = client.get(f"/agent-tasks/{task_id}/artifacts/{artifact_id}")

    assert response.status_code == 200
    assert response.json() == {"fallback": True}


def test_agent_task_prov_artifact_route_rejects_tampered_storage_file(
    monkeypatch, tmp_path: Path
) -> None:
    task_id = uuid4()
    artifact_id = uuid4()
    storage_service = StorageService(storage_root=tmp_path / "storage")
    artifact_path = (
        storage_service.get_agent_task_dir(task_id) / "technical_report_prov_export.json"
    )
    frozen_payload = {
        "schema_name": "technical_report_prov_export",
        "frozen_export": {
            "artifact_id": str(artifact_id),
            "artifact_kind": "technical_report_prov_export",
            "task_id": str(task_id),
            "export_payload_sha256": "expected",
        },
        "prov_integrity": {"complete": True},
    }
    artifact_path.write_text(json.dumps({**frozen_payload, "tampered": True}))

    def fake_get_artifact(_session, incoming_task_id, incoming_artifact_id):
        return type(
            "ArtifactRow",
            (),
            {
                "id": incoming_artifact_id,
                "task_id": incoming_task_id,
                "artifact_kind": "technical_report_prov_export",
                "storage_path": str(artifact_path),
                "payload_json": frozen_payload,
            },
        )()

    try:
        monkeypatch.setattr(
            "app.api.routers.agent_tasks.get_storage_service",
            lambda: storage_service,
        )
        monkeypatch.setattr(
            "app.api.routers.agent_tasks.get_agent_task_artifact",
            fake_get_artifact,
        )
        client = TestClient(app)
        response = client.get(f"/agent-tasks/{task_id}/artifacts/{artifact_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["error_code"] == "agent_task_artifact_integrity_mismatch"
    assert response.json()["error_context"]["artifact_id"] == str(artifact_id)


def test_agent_task_context_route_returns_machine_readable_error_code_for_bad_format(
    monkeypatch,
) -> None:
    task_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.agent_tasks.get_agent_task_context",
        lambda session, requested_task_id: {"summary": {}, "refs": []},
    )

    client = TestClient(app)
    response = client.get(f"/agent-tasks/{task_id}/context?format=xml")

    assert response.status_code == 400
    assert response.json()["error_code"] == "invalid_context_format"
