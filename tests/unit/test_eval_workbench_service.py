from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.db.models import EvalFailureCase
from app.services.eval_workbench import triage_eval_failure_case


class FakeSession:
    def __init__(self, row: EvalFailureCase) -> None:
        self.row = row

    def get(self, model, key):
        if model.__name__ == "EvalFailureCase" and key == self.row.id:
            return self.row
        return None


def _case(*, classification: str = "table_recall_gap") -> EvalFailureCase:
    now = datetime.now(UTC)
    case_id = uuid4()
    return EvalFailureCase(
        id=case_id,
        case_key="case-key",
        status="open",
        severity="high",
        surface="search_request",
        failure_classification=classification,
        problem_statement="tabular search returned no table hits",
        observed_behavior="no table hits",
        expected_behavior="table evidence should rank in the top results",
        diagnosis=None,
        recommended_next_actions_json=[
            "inspect_eval_failure_case",
            "triage_eval_failure_case",
            "optimize_search_harness_from_case",
        ],
        allowed_repair_surfaces_json=["retrieval_profile_overrides", "reranker_overrides"],
        blocked_repair_surfaces_json=["evaluation_corpus_weakening"],
        evidence_refs_json=[],
        verification_requirements_json={"max_total_regressed_count": 0},
        agent_task_payloads_json={
            "optimize_harness": {
                "task_type": "optimize_search_harness_from_case",
                "input": {"case_id": str(case_id)},
                "workflow_version": "eval_v1",
            }
        },
        details_json={"search_related": True},
        created_at=now,
        updated_at=now,
        last_seen_at=now,
    )


def test_triage_eval_failure_case_updates_case_and_returns_next_task_payload() -> None:
    row = _case()
    task_id = uuid4()

    response = triage_eval_failure_case(FakeSession(row), row.id, agent_task_id=task_id)

    assert row.status == "triaged"
    assert row.agent_task_id == task_id
    assert row.diagnosis
    assert response.recommendation["next_action"] == "optimize_search_harness_from_case"
    assert response.repair_case["blocked_repair_surfaces"] == ["evaluation_corpus_weakening"]
    assert response.next_task_payloads[0]["task_type"] == "optimize_search_harness_from_case"

