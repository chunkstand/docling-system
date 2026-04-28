from __future__ import annotations

import os
from copy import deepcopy
from uuid import UUID

import pytest
from sqlalchemy import select

from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    ClaimSupportEvaluation,
    ClaimSupportEvaluationCase,
    KnowledgeOperatorRun,
)
from app.schemas.agent_tasks import AgentTaskCreateRequest
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import create_agent_task
from app.services.claim_support_evaluations import default_claim_support_evaluation_fixtures
from app.services.evidence import payload_sha256

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def _process_next_task(postgres_integration_harness) -> UUID:
    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "claim-support-eval-worker")
        assert task is not None
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)
        return task.id


def test_claim_support_judge_evaluation_task_persists_replay_rows(
    postgres_integration_harness,
):
    with postgres_integration_harness.session_factory() as session:
        task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_claim_support_judge",
                input={
                    "evaluation_name": "claim_support_judge_calibration",
                    "fixture_set_name": "default_claim_support_v1",
                    "min_support_score": 0.34,
                    "min_overall_accuracy": 1.0,
                    "min_verdict_precision": 1.0,
                    "min_verdict_recall": 1.0,
                },
                workflow_version="claim_support_judge_eval_integration",
            ),
        )
        task_id = task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        task_row = session.get(AgentTask, task_id)
        assert task_row is not None
        payload = task_row.result_json["payload"]
        evaluation_id = UUID(payload["evaluation_id"])
        assert payload["summary"]["gate_outcome"] == "passed"
        assert payload["summary"]["overall_accuracy"] == 1.0
        assert payload["fixture_set_sha256"]
        assert payload["operator_run_id"]

        evaluation_row = session.get(ClaimSupportEvaluation, evaluation_id)
        assert evaluation_row is not None
        assert evaluation_row.agent_task_id == task_id
        assert str(evaluation_row.operator_run_id) == payload["operator_run_id"]
        assert evaluation_row.gate_outcome == "passed"
        assert evaluation_row.fixture_set_sha256 == payload["fixture_set_sha256"]
        assert evaluation_row.evaluation_payload_sha256 == payload_sha256(
            evaluation_row.evaluation_payload_json
        )

        case_rows = list(
            session.scalars(
                select(ClaimSupportEvaluationCase)
                .where(ClaimSupportEvaluationCase.evaluation_id == evaluation_id)
                .order_by(ClaimSupportEvaluationCase.case_index.asc())
            )
        )
        assert len(case_rows) == payload["summary"]["case_count"]
        assert all(row.passed for row in case_rows)
        assert {row.expected_verdict for row in case_rows} == {
            "supported",
            "unsupported",
            "insufficient_evidence",
        }
        assert any(row.hard_case_kind == "lexical_overlap_wrong_evidence" for row in case_rows)
        assert all(row.support_judgment_json for row in case_rows)

        operator_run = session.get(KnowledgeOperatorRun, UUID(payload["operator_run_id"]))
        assert operator_run is not None
        assert operator_run.operator_kind == "judge"
        assert operator_run.operator_name == "technical_report_claim_support_judge_evaluation"
        assert operator_run.output_sha256

        artifacts = list(
            session.scalars(
                select(AgentTaskArtifact).where(
                    AgentTaskArtifact.task_id == task_id,
                    AgentTaskArtifact.artifact_kind == "claim_support_judge_evaluation",
                )
            )
        )
        assert len(artifacts) == 1
        assert artifacts[0].payload_json["evaluation_id"] == str(evaluation_id)


def test_claim_support_judge_evaluation_task_persists_failed_gate(
    postgres_integration_harness,
):
    fixture = deepcopy(default_claim_support_evaluation_fixtures()[0])
    fixture["case_id"] = "forced_claim_support_regression"
    fixture["description"] = "Intentional mismatch proves failed gates persist audit evidence."
    fixture["hard_case_kind"] = "forced_gate_failure"
    fixture["expected_verdict"] = "unsupported"

    with postgres_integration_harness.session_factory() as session:
        task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_claim_support_judge",
                input={
                    "evaluation_name": "claim_support_judge_forced_failure",
                    "fixture_set_name": "forced_failure_fixture_set",
                    "fixtures": [fixture],
                    "min_support_score": 0.34,
                    "min_overall_accuracy": 1.0,
                    "min_verdict_precision": 1.0,
                    "min_verdict_recall": 1.0,
                },
                workflow_version="claim_support_judge_eval_failure_integration",
            ),
        )
        task_id = task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        task_row = session.get(AgentTask, task_id)
        assert task_row is not None
        assert task_row.status == "completed"
        payload = task_row.result_json["payload"]
        evaluation_id = UUID(payload["evaluation_id"])
        assert payload["summary"]["gate_outcome"] == "failed"
        assert payload["summary"]["failed_case_count"] == 1
        assert payload["reasons"]

        evaluation_row = session.get(ClaimSupportEvaluation, evaluation_id)
        assert evaluation_row is not None
        assert evaluation_row.agent_task_id == task_id
        assert evaluation_row.status == "completed"
        assert evaluation_row.gate_outcome == "failed"
        assert evaluation_row.reasons_json == payload["reasons"]
        assert evaluation_row.evaluation_payload_sha256 == payload_sha256(
            evaluation_row.evaluation_payload_json
        )

        case_rows = list(
            session.scalars(
                select(ClaimSupportEvaluationCase)
                .where(ClaimSupportEvaluationCase.evaluation_id == evaluation_id)
                .order_by(ClaimSupportEvaluationCase.case_index.asc())
            )
        )
        assert len(case_rows) == 1
        assert case_rows[0].case_id == "forced_claim_support_regression"
        assert case_rows[0].hard_case_kind == "forced_gate_failure"
        assert case_rows[0].passed is False
        assert case_rows[0].expected_verdict == "unsupported"
        assert case_rows[0].predicted_verdict == "supported"
        assert case_rows[0].failure_reasons_json == ["expected_unsupported_got_supported"]

        operator_run = session.get(KnowledgeOperatorRun, UUID(payload["operator_run_id"]))
        assert operator_run is not None
        assert operator_run.metrics_json["gate_outcome"] == "failed"

        artifacts = list(
            session.scalars(
                select(AgentTaskArtifact).where(
                    AgentTaskArtifact.task_id == task_id,
                    AgentTaskArtifact.artifact_kind == "claim_support_judge_evaluation",
                )
            )
        )
        assert len(artifacts) == 1
        assert artifacts[0].payload_json["summary"]["gate_outcome"] == "failed"
