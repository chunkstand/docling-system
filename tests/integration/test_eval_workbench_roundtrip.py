from __future__ import annotations

import os
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.db.models import AgentTask, AgentTaskStatus, EvalFailureCase, EvalObservation
from app.schemas.agent_tasks import AgentTaskApprovalRequest, AgentTaskCreateRequest
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import approve_agent_task, create_agent_task
from tests.integration.test_agent_task_triage_roundtrip import _create_processed_document

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def _process_next_task(postgres_integration_harness) -> UUID:
    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "eval-workbench-agent-worker")
        assert task is not None
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)
        return task.id


def _create_task(postgres_integration_harness, payload: AgentTaskCreateRequest) -> UUID:
    with postgres_integration_harness.session_factory() as session:
        task = create_agent_task(session, payload)
        return task.task_id


def test_eval_workbench_agent_harness_repair_roundtrip(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.search_harness_optimization.get_settings",
        lambda: SimpleNamespace(
            storage_root=postgres_integration_harness.storage_service.storage_root
        ),
    )
    _document_id, _run_id = _create_processed_document(postgres_integration_harness)
    client = postgres_integration_harness.client

    gap_response = client.post(
        "/search",
        json={
            "query": "xqzv pleroma quasar nothing",
            "mode": "hybrid",
            "limit": 5,
        },
    )
    assert gap_response.status_code == 200
    assert gap_response.json() == []
    assert gap_response.headers["X-Search-Request-Id"]

    refresh_task_id = _create_task(
        postgres_integration_harness,
        AgentTaskCreateRequest(
            task_type="refresh_eval_failure_cases",
            input={"limit": 20},
            workflow_version="eval_workbench_integration",
        ),
    )
    assert _process_next_task(postgres_integration_harness) == refresh_task_id

    with postgres_integration_harness.session_factory() as session:
        refresh_task = session.get(AgentTask, refresh_task_id)
        assert refresh_task is not None
        assert refresh_task.status == AgentTaskStatus.COMPLETED.value
        refresh_payload = refresh_task.result_json["payload"]["refresh"]
        assert refresh_payload["case_count"] >= 1
        case_id = UUID(refresh_payload["cases"][0]["case_id"])
        case = session.get(EvalFailureCase, case_id)
        assert case is not None
        assert case.status == "open"
        assert case.failure_classification in {"search_recall_gap", "search_quality_gap"}
        observation = session.get(EvalObservation, case.source_observation_id)
        assert observation is not None
        assert observation.status == "active"
        assert case.agent_task_payloads_json["inspect"]["task_type"] == "inspect_eval_failure_case"

    workbench_response = client.get("/eval/workbench")
    assert workbench_response.status_code == 200
    assert workbench_response.json()["summary"]["open_case_count"] >= 1
    assert any(
        payload["task_type"] == "inspect_eval_failure_case"
        for payload in workbench_response.json()["recommended_task_payloads"]
    )
    case_yaml_response = client.get(f"/eval/failure-cases/{case_id}?format=yaml")
    assert case_yaml_response.status_code == 200
    assert "schema_name: eval_failure_case" in case_yaml_response.text
    inspect_response = client.get(f"/eval/failure-cases/{case_id}/inspect")
    assert inspect_response.status_code == 200
    assert inspect_response.json()["case"]["case_id"] == str(case_id)

    inspect_task_id = _create_task(
        postgres_integration_harness,
        AgentTaskCreateRequest(
            task_type="inspect_eval_failure_case",
            input={"case_id": str(case_id)},
            workflow_version="eval_workbench_integration",
        ),
    )
    assert _process_next_task(postgres_integration_harness) == inspect_task_id

    triage_task_id = _create_task(
        postgres_integration_harness,
        AgentTaskCreateRequest(
            task_type="triage_eval_failure_case",
            input={"case_id": str(case_id)},
            workflow_version="eval_workbench_integration",
        ),
    )
    assert _process_next_task(postgres_integration_harness) == triage_task_id

    with postgres_integration_harness.session_factory() as session:
        case = session.get(EvalFailureCase, case_id)
        assert case is not None
        assert case.status == "triaged"
        assert case.agent_task_id == triage_task_id
        triage_task = session.get(AgentTask, triage_task_id)
        assert triage_task is not None
        assert triage_task.result_json["payload"]["triage"]["repair_case"]["schema_name"] == (
            "eval_failure_repair_case"
        )

    optimize_task_id = _create_task(
        postgres_integration_harness,
        AgentTaskCreateRequest(
            task_type="optimize_search_harness_from_case",
            input={
                "case_id": str(case_id),
                "base_harness_name": "wide_v2",
                "baseline_harness_name": "wide_v2",
                "candidate_harness_name": f"case_candidate_{uuid4().hex[:8]}",
                "source_types": ["evaluation_queries", "live_search_gaps"],
                "limit": 10,
                "iterations": 1,
            },
            workflow_version="eval_workbench_integration",
        ),
    )
    assert _process_next_task(postgres_integration_harness) == optimize_task_id

    with postgres_integration_harness.session_factory() as session:
        optimize_task = session.get(AgentTask, optimize_task_id)
        assert optimize_task is not None
        assert optimize_task.status == AgentTaskStatus.COMPLETED.value
        optimization = optimize_task.result_json["payload"]["optimization"]
        assert optimization["best_override_spec"]["base_harness_name"] == "wide_v2"
        assert optimization["best_evaluation"]["total_shared_query_count"] >= 1
        best_override = optimization["best_override_spec"]
        assert (
            best_override.get("retrieval_profile_overrides")
            or best_override.get("reranker_overrides")
        ), {
            "best_score": optimization["best_score"],
            "best_gate": optimization["best_gate"],
            "attempts": optimization["attempts"],
        }

    draft_name = f"case_review_{uuid4().hex[:8]}"
    draft_task_id = _create_task(
        postgres_integration_harness,
        AgentTaskCreateRequest(
            task_type="draft_harness_config_update_from_optimization",
            input={
                "source_task_id": str(optimize_task_id),
                "draft_harness_name": draft_name,
                "rationale": "publish verified eval-workbench search repair",
            },
            workflow_version="eval_workbench_integration",
        ),
    )
    assert _process_next_task(postgres_integration_harness) == draft_task_id

    verify_task_id = _create_task(
        postgres_integration_harness,
        AgentTaskCreateRequest(
            task_type="verify_draft_harness_config",
            input={
                "target_task_id": str(draft_task_id),
                "baseline_harness_name": "wide_v2",
                "source_types": ["evaluation_queries", "live_search_gaps"],
                "limit": 10,
                "min_total_shared_query_count": 1,
            },
            workflow_version="eval_workbench_integration",
        ),
    )
    assert _process_next_task(postgres_integration_harness) == verify_task_id

    with postgres_integration_harness.session_factory() as session:
        verify_task = session.get(AgentTask, verify_task_id)
        assert verify_task is not None
        assert verify_task.status == AgentTaskStatus.COMPLETED.value
        verification_payload = verify_task.result_json["payload"]["verification"]
        assert verification_payload["outcome"] == "passed", {
            "reasons": verification_payload["reasons"],
            "metrics": verification_payload["metrics"],
            "comprehension_gate": verify_task.result_json["payload"]["comprehension_gate"],
        }

    apply_task_id = _create_task(
        postgres_integration_harness,
        AgentTaskCreateRequest(
            task_type="apply_harness_config_update",
            input={
                "draft_task_id": str(draft_task_id),
                "verification_task_id": str(verify_task_id),
                "reason": "approve agent-proposed eval repair",
            },
            workflow_version="eval_workbench_integration",
        ),
    )

    with postgres_integration_harness.session_factory() as session:
        apply_task = session.get(AgentTask, apply_task_id)
        assert apply_task is not None
        assert apply_task.status == AgentTaskStatus.AWAITING_APPROVAL.value
        assert claim_next_agent_task(session, "eval-workbench-agent-worker") is None
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="operator@example.com",
                approval_note="human approves verified eval-workbench harness repair",
            ),
        )

    assert _process_next_task(postgres_integration_harness) == apply_task_id

    with postgres_integration_harness.session_factory() as session:
        apply_task = session.get(AgentTask, apply_task_id)
        assert apply_task is not None
        assert apply_task.status == AgentTaskStatus.COMPLETED.value
        apply_payload = apply_task.result_json["payload"]
        assert apply_payload["draft_harness_name"] == draft_name
        assert apply_payload["follow_up_summary"]["schema_name"] == (
            "search_harness_follow_up_evidence"
        )
        harness_rows = (
            session.execute(
                select(AgentTask).where(
                    AgentTask.workflow_version == "eval_workbench_integration"
                )
            )
            .scalars()
            .all()
        )
        assert {row.task_type for row in harness_rows} >= {
            "refresh_eval_failure_cases",
            "inspect_eval_failure_case",
            "triage_eval_failure_case",
            "optimize_search_harness_from_case",
            "draft_harness_config_update_from_optimization",
            "verify_draft_harness_config",
            "apply_harness_config_update",
        }

    harnesses_response = client.get("/search/harnesses")
    assert harnesses_response.status_code == 200
    assert any(row["harness_name"] == draft_name for row in harnesses_response.json())
