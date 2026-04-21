from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app
from app.db.session import get_db_session


def _case_payload(case_id=None) -> dict:
    now = datetime.now(UTC).isoformat()
    case_id = case_id or uuid4()
    return {
        "schema_name": "eval_failure_case",
        "schema_version": "1.0",
        "case_id": str(case_id),
        "case_key": "case-key",
        "status": "open",
        "severity": "high",
        "surface": "search_request",
        "failure_classification": "table_recall_gap",
        "problem_statement": "tabular search returned no table hits",
        "observed_behavior": "no table hits",
        "expected_behavior": "table evidence should rank",
        "diagnosis": None,
        "source_observation_id": None,
        "document_id": None,
        "run_id": None,
        "evaluation_id": None,
        "evaluation_query_id": None,
        "search_request_id": None,
        "replay_run_id": None,
        "harness_evaluation_id": None,
        "agent_task_id": None,
        "recommended_next_actions": ["inspect_eval_failure_case"],
        "allowed_repair_surfaces": ["retrieval_profile_overrides"],
        "blocked_repair_surfaces": ["evaluation_corpus_weakening"],
        "evidence_refs": [],
        "verification_requirements": {"max_total_regressed_count": 0},
        "agent_task_payloads": {
            "inspect": {
                "task_type": "inspect_eval_failure_case",
                "input": {"case_id": str(case_id)},
                "workflow_version": "eval_v1",
            }
        },
        "details": {},
        "created_at": now,
        "updated_at": now,
        "last_seen_at": now,
        "resolved_at": None,
    }


def test_eval_workbench_route_returns_agent_task_payloads(monkeypatch) -> None:
    case_id = uuid4()

    monkeypatch.setattr(
        "app.api.main.get_eval_workbench",
        lambda session, limit=25: {
            "schema_name": "eval_workbench",
            "schema_version": "1.0",
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": {
                "open_case_count": 1,
                "awaiting_approval_count": 0,
                "high_severity_count": 1,
                "refreshed_case_count": 0,
                "refreshed_observation_count": 0,
            },
            "cases": [_case_payload(case_id)],
            "approval_queue": [],
            "recommended_task_payloads": [
                {
                    "task_type": "inspect_eval_failure_case",
                    "input": {"case_id": str(case_id)},
                    "workflow_version": "eval_v1",
                }
            ],
            "freshness_warnings": [],
        },
    )

    client = TestClient(app)
    response = client.get("/eval/workbench")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["open_case_count"] == 1
    assert body["recommended_task_payloads"][0]["task_type"] == "inspect_eval_failure_case"


def test_eval_failure_case_yaml_is_derived_from_json_contract(monkeypatch) -> None:
    case_id = uuid4()
    monkeypatch.setattr(
        "app.api.main.get_eval_failure_case",
        lambda session, requested_case_id: _case_payload(requested_case_id),
    )

    client = TestClient(app)
    response = client.get(f"/eval/failure-cases/{case_id}?format=yaml")

    assert response.status_code == 200
    assert "schema_name: eval_failure_case" in response.text
    assert f"case_id: {case_id}" in response.text


def test_eval_failure_cases_route_accepts_repeated_status_query(monkeypatch) -> None:
    captured: dict = {}

    def fake_list_cases(session, *, status_filter=None, include_resolved=False, limit=50):
        captured["status_filter"] = status_filter
        captured["include_resolved"] = include_resolved
        captured["limit"] = limit
        return []

    monkeypatch.setattr("app.api.main.list_eval_failure_cases", fake_list_cases)

    client = TestClient(app)
    response = client.get(
        "/eval/failure-cases?status=triaged&status=verified&include_resolved=true&limit=7"
    )

    assert response.status_code == 200
    assert response.json() == []
    assert captured == {
        "status_filter": ["triaged", "verified"],
        "include_resolved": True,
        "limit": 7,
    }


def test_refresh_eval_failure_cases_route_commits(monkeypatch) -> None:
    committed = {"value": False}

    class SessionStub:
        def commit(self) -> None:
            committed["value"] = True

    def override_session():
        yield SessionStub()

    app.dependency_overrides[get_db_session] = override_session
    monkeypatch.setattr(
        "app.api.main.refresh_eval_failure_cases",
        lambda session, limit=50, include_resolved=False: {
            "schema_name": "eval_failure_case_refresh",
            "schema_version": "1.0",
            "refreshed_at": datetime.now(UTC).isoformat(),
            "observation_count": 1,
            "case_count": 1,
            "open_case_count": 1,
            "cases": [_case_payload()],
        },
    )

    client = TestClient(app)
    try:
        response = client.post("/eval/failure-cases/refresh")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["case_count"] == 1
    assert committed["value"] is True


def test_refresh_eval_failure_cases_route_requires_remote_write_capability(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_port=8000,
            api_key="operator-secret",
            remote_api_capabilities=None,
        ),
    )
    monkeypatch.setattr(
        "app.api.main.refresh_eval_failure_cases",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("capability gate should block before eval failure refresh runs")
        ),
    )

    client = TestClient(app)
    response = client.post(
        "/eval/failure-cases/refresh",
        headers={"X-API-Key": "operator-secret"},
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "capability_not_allowed"


def test_eval_workbench_route_requires_remote_read_capability(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.main.get_settings",
        lambda: SimpleNamespace(
            api_mode="remote",
            api_host="0.0.0.0",
            api_port=8000,
            api_key="operator-secret",
            remote_api_capabilities=None,
        ),
    )
    monkeypatch.setattr(
        "app.api.main.get_eval_workbench",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("capability gate should block before eval workbench reads")
        ),
    )

    client = TestClient(app)
    response = client.get("/eval/workbench", headers={"X-API-Key": "operator-secret"})

    assert response.status_code == 403
    assert response.json()["error_code"] == "capability_not_allowed"
