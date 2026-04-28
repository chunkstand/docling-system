from __future__ import annotations

import os
from copy import deepcopy
from uuid import UUID

import pytest
from sqlalchemy import select

from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskStatus,
    ClaimSupportCalibrationPolicy,
    ClaimSupportEvaluation,
    ClaimSupportEvaluationCase,
    ClaimSupportFixtureSet,
    KnowledgeOperatorOutput,
    KnowledgeOperatorRun,
)
from app.schemas.agent_tasks import AgentTaskApprovalRequest, AgentTaskCreateRequest
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import approve_agent_task, create_agent_task
from app.services.claim_support_evaluations import (
    build_claim_support_calibration_policy_payload,
    default_claim_support_evaluation_fixtures,
    draft_claim_support_calibration_policy,
    ensure_claim_support_calibration_policy,
    resolve_claim_support_calibration_policy,
)
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
        assert payload["fixture_set_id"]
        assert payload["fixture_set_version"] == "v1"
        assert payload["policy_id"]
        assert payload["policy_name"] == "claim_support_judge_calibration_policy"
        assert payload["policy_version"] == "v1"
        assert payload["policy_sha256"]
        assert payload["operator_run_id"]

        evaluation_row = session.get(ClaimSupportEvaluation, evaluation_id)
        assert evaluation_row is not None
        assert evaluation_row.agent_task_id == task_id
        assert str(evaluation_row.operator_run_id) == payload["operator_run_id"]
        assert str(evaluation_row.fixture_set_id) == payload["fixture_set_id"]
        assert str(evaluation_row.policy_id) == payload["policy_id"]
        assert evaluation_row.gate_outcome == "passed"
        assert evaluation_row.fixture_set_version == "v1"
        assert evaluation_row.fixture_set_sha256 == payload["fixture_set_sha256"]
        assert evaluation_row.policy_sha256 == payload["policy_sha256"]
        assert evaluation_row.evaluation_payload_sha256 == payload_sha256(
            evaluation_row.evaluation_payload_json
        )
        fixture_set_row = session.get(ClaimSupportFixtureSet, UUID(payload["fixture_set_id"]))
        policy_row = session.get(ClaimSupportCalibrationPolicy, UUID(payload["policy_id"]))
        assert fixture_set_row is not None
        assert fixture_set_row.fixture_set_sha256 == payload["fixture_set_sha256"]
        assert policy_row is not None
        assert policy_row.policy_sha256 == payload["policy_sha256"]

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
        assert operator_run.metrics_json["policy_sha256"] == payload["policy_sha256"]
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


def test_claim_support_judge_evaluation_task_fails_single_fixture_coverage_gate(
    postgres_integration_harness,
):
    fixture = deepcopy(default_claim_support_evaluation_fixtures()[0])
    fixture["case_id"] = "single_fixture_coverage_gap"

    with postgres_integration_harness.session_factory() as session:
        task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_claim_support_judge",
                input={
                    "evaluation_name": "claim_support_judge_coverage_gap",
                    "fixture_set_name": "single_fixture_coverage_gap",
                    "fixtures": [fixture],
                    "min_support_score": 0.34,
                    "min_overall_accuracy": 1.0,
                    "min_verdict_precision": 1.0,
                    "min_verdict_recall": 1.0,
                },
                workflow_version="claim_support_judge_eval_coverage_gap_integration",
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
        assert payload["summary"]["overall_accuracy"] == 1.0
        assert payload["summary"]["failed_case_count"] == 0
        assert payload["summary"]["hard_case_kind_count"] == 1
        assert "Support-judge quality satisfies the governed hard-case policy." in payload[
            "reasons"
        ]
        assert payload["fixture_set_id"]
        assert payload["policy_id"]
        assert payload["policy_sha256"]

        evaluation_row = session.get(ClaimSupportEvaluation, evaluation_id)
        assert evaluation_row is not None
        assert evaluation_row.gate_outcome == "failed"
        assert str(evaluation_row.fixture_set_id) == payload["fixture_set_id"]
        assert str(evaluation_row.policy_id) == payload["policy_id"]
        assert evaluation_row.metrics_json["gate_outcome"] == "failed"
        assert evaluation_row.metrics_json["policy_sha256"] == payload["policy_sha256"]
        assert evaluation_row.reasons_json == payload["reasons"]

        operator_run = session.get(KnowledgeOperatorRun, UUID(payload["operator_run_id"]))
        assert operator_run is not None
        assert operator_run.metrics_json["gate_outcome"] == "failed"

        operator_output = session.scalar(
            select(KnowledgeOperatorOutput).where(
                KnowledgeOperatorOutput.operator_run_id == operator_run.id,
                KnowledgeOperatorOutput.output_kind == "claim_support_judge_evaluation",
            )
        )
        assert operator_output is not None
        assert operator_output.payload_json["gate_outcome"] == "failed"
        assert operator_output.payload_json["policy_sha256"] == payload["policy_sha256"]


def test_claim_support_judge_evaluation_task_uses_persisted_custom_policy(
    postgres_integration_harness,
):
    fixture = deepcopy(default_claim_support_evaluation_fixtures()[0])
    fixture["case_id"] = "custom_policy_missing_kind"
    policy_payload = build_claim_support_calibration_policy_payload(
        policy_name="strict_claim_support_policy",
        policy_version="v1",
        min_hard_case_kind_count=1,
        required_hard_case_kinds=["required_kind_not_in_fixture"],
        required_verdicts=["supported"],
        source="integration_test",
    )

    with postgres_integration_harness.session_factory() as session:
        policy_row = ensure_claim_support_calibration_policy(
            session,
            policy_payload=policy_payload,
        )
        task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_claim_support_judge",
                input={
                    "evaluation_name": "claim_support_judge_custom_policy",
                    "fixture_set_name": "custom_policy_fixture_set",
                    "fixture_set_version": "v1",
                    "policy_name": "strict_claim_support_policy",
                    "policy_version": "v1",
                    "fixtures": [fixture],
                    "min_support_score": 0.34,
                    "min_overall_accuracy": 1.0,
                    "min_verdict_precision": 1.0,
                    "min_verdict_recall": 1.0,
                },
                workflow_version="claim_support_judge_eval_custom_policy_integration",
            ),
        )
        policy_id = policy_row.id
        task_id = task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        task_row = session.get(AgentTask, task_id)
        assert task_row is not None
        payload = task_row.result_json["payload"]
        evaluation_id = UUID(payload["evaluation_id"])
        assert payload["summary"]["gate_outcome"] == "failed"
        assert payload["summary"]["overall_accuracy"] == 1.0
        assert payload["summary"]["missing_hard_case_kinds"] == [
            "required_kind_not_in_fixture"
        ]
        assert payload["policy_id"] == str(policy_id)
        assert payload["policy_sha256"] == policy_payload["policy_sha256"]

        evaluation_row = session.get(ClaimSupportEvaluation, evaluation_id)
        assert evaluation_row is not None
        assert evaluation_row.gate_outcome == "failed"
        assert evaluation_row.policy_id == policy_id
        assert evaluation_row.policy_name == "strict_claim_support_policy"
        assert evaluation_row.policy_sha256 == policy_payload["policy_sha256"]


def test_claim_support_policy_promotion_workflow_activates_verified_policy(
    postgres_integration_harness,
):
    with postgres_integration_harness.session_factory() as session:
        initial_policy = ensure_claim_support_calibration_policy(
            session,
            policy_payload=build_claim_support_calibration_policy_payload(),
        )
        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_claim_support_calibration_policy",
                input={
                    "policy_name": "claim_support_judge_calibration_policy",
                    "policy_version": "v2",
                    "rationale": "promote a focused one-kind calibration policy for integration",
                    "min_hard_case_kind_count": 1,
                    "required_hard_case_kinds": ["exact_source_support"],
                    "required_verdicts": ["supported"],
                },
                workflow_version="claim_support_policy_promotion_integration",
            ),
        )
        initial_policy_id = initial_policy.id
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_row = session.get(AgentTask, draft_task_id)
        assert draft_row is not None
        draft_payload = draft_row.result_json["payload"]
        draft_policy_id = UUID(draft_payload["policy_id"])
        draft_policy = session.get(ClaimSupportCalibrationPolicy, draft_policy_id)
        assert draft_policy is not None
        assert draft_policy.status == "draft"
        assert session.get(ClaimSupportCalibrationPolicy, initial_policy_id).status == "active"

        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixtures": [default_claim_support_evaluation_fixtures()[0]],
                },
                workflow_version="claim_support_policy_promotion_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_row = session.get(AgentTask, verify_task_id)
        assert verify_row is not None
        verify_payload = verify_row.result_json["payload"]
        assert verify_payload["verification"]["outcome"] == "passed"
        assert verify_payload["evaluation"]["policy_id"] == str(draft_policy_id)
        assert verify_payload["mined_failure_summary"]["mined_failure_case_count"] == 0
        verification_id = verify_payload["verification"]["verification_id"]
        verification_fixture_set_id = verify_payload["evaluation"]["fixture_set_id"]
        verification_fixture_set_sha256 = verify_payload["evaluation"]["fixture_set_sha256"]
        verification_policy_sha256 = verify_payload["evaluation"]["policy_sha256"]

        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_claim_support_calibration_policy",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "activate the verified focused calibration policy",
                },
                workflow_version="claim_support_policy_promotion_integration",
            ),
        )
        apply_task_id = apply_task.task_id
        apply_row = session.get(AgentTask, apply_task_id)
        assert apply_row is not None
        assert apply_row.status == AgentTaskStatus.AWAITING_APPROVAL.value
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="claim-support-operator@example.com",
                approval_note="verified policy may become active",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_row = session.get(AgentTask, apply_task_id)
        assert apply_row is not None
        apply_payload = apply_row.result_json["payload"]
        assert apply_payload["activated_policy_id"] == str(draft_policy_id)
        assert apply_payload["previous_active_policy_id"] == str(initial_policy_id)
        assert apply_payload["approved_by"] == "claim-support-operator@example.com"
        assert apply_payload["approved_at"]
        assert apply_payload["approval_note"] == "verified policy may become active"
        assert apply_payload["verification_id"] == verification_id
        assert apply_payload["verification_outcome"] == "passed"
        assert apply_payload["verification_reasons"] == []
        assert apply_payload["verification_fixture_set_id"] == verification_fixture_set_id
        assert apply_payload["verification_fixture_set_sha256"] == verification_fixture_set_sha256
        assert apply_payload["verification_policy_sha256"] == verification_policy_sha256
        assert apply_payload["draft_policy_sha256"] == verification_policy_sha256
        assert apply_payload["verification_mined_failure_summary"][
            "mined_failure_case_count"
        ] == 0
        assert apply_payload["operator_run_id"]

        initial_policy = session.get(ClaimSupportCalibrationPolicy, initial_policy_id)
        activated_policy = session.get(ClaimSupportCalibrationPolicy, draft_policy_id)
        assert initial_policy is not None
        assert initial_policy.status == "retired"
        assert activated_policy is not None
        assert activated_policy.status == "active"

        active_policies = list(
            session.scalars(
                select(ClaimSupportCalibrationPolicy).where(
                    ClaimSupportCalibrationPolicy.policy_name
                    == "claim_support_judge_calibration_policy",
                    ClaimSupportCalibrationPolicy.status == "active",
                )
            )
        )
        assert [row.id for row in active_policies] == [draft_policy_id]

        eval_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_claim_support_judge",
                input={
                    "evaluation_name": "claim_support_judge_active_policy_check",
                    "fixture_set_name": "active_policy_fixture_set",
                    "fixtures": [default_claim_support_evaluation_fixtures()[0]],
                },
                workflow_version="claim_support_policy_promotion_integration",
            ),
        )
        eval_task_id = eval_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        eval_row = session.get(AgentTask, eval_task_id)
        assert eval_row is not None
        eval_payload = eval_row.result_json["payload"]
        assert eval_payload["summary"]["gate_outcome"] == "passed"
        assert eval_payload["policy_id"] == str(draft_policy_id)
        assert eval_payload["policy_version"] == "v2"


def test_claim_support_policy_verification_replays_mined_failed_cases(
    postgres_integration_harness,
):
    failure_fixture = deepcopy(default_claim_support_evaluation_fixtures()[0])
    failure_fixture["case_id"] = "mined_claim_support_failure"
    failure_fixture["description"] = "Persisted failure should become future policy evidence."
    failure_fixture["hard_case_kind"] = "mined_failed_claim_support_case"
    failure_fixture["expected_verdict"] = "unsupported"

    with postgres_integration_harness.session_factory() as session:
        source_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_claim_support_judge",
                input={
                    "evaluation_name": "claim_support_judge_mined_failure_source",
                    "fixture_set_name": "mined_failure_source_fixture_set",
                    "fixtures": [failure_fixture],
                    "min_hard_case_kind_count": 1,
                    "required_hard_case_kinds": ["mined_failed_claim_support_case"],
                    "required_verdicts": ["unsupported"],
                },
                workflow_version="claim_support_policy_mined_failure_integration",
            ),
        )
        source_task_id = source_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        source_row = session.get(AgentTask, source_task_id)
        assert source_row is not None
        source_payload = source_row.result_json["payload"]
        source_evaluation_id = source_payload["evaluation_id"]
        source_fixture_set_id = source_payload["fixture_set_id"]
        source_fixture_set_sha256 = source_payload["fixture_set_sha256"]
        assert source_payload["summary"]["gate_outcome"] == "failed"
        assert source_payload["summary"]["failed_case_count"] == 1

        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_claim_support_calibration_policy",
                input={
                    "policy_name": "claim_support_judge_calibration_policy",
                    "policy_version": "v_mined_failures",
                    "rationale": "prove mined support-judge failures join verification evidence",
                    "min_hard_case_kind_count": 1,
                    "required_hard_case_kinds": ["exact_source_support"],
                    "required_verdicts": ["supported"],
                },
                workflow_version="claim_support_policy_mined_failure_integration",
            ),
        )
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixture_set_name": "mined_failure_policy_verification",
                    "fixture_set_version": "v1",
                    "include_mined_failures": True,
                    "mined_failure_limit": 5,
                },
                workflow_version="claim_support_policy_mined_failure_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_row = session.get(AgentTask, verify_task_id)
        assert verify_row is not None
        verify_payload = verify_row.result_json["payload"]
        mined_summary = verify_payload["mined_failure_summary"]
        mined_source = mined_summary["sources"][0]

        assert verify_payload["verification"]["outcome"] == "failed"
        assert verify_payload["evaluation"]["summary"]["failed_case_count"] == 1
        assert verify_payload["evaluation"]["summary"]["case_count"] == (
            len(default_claim_support_evaluation_fixtures()) + 1
        )
        assert mined_summary["enabled"] is True
        assert mined_summary["default_fixture_count"] == len(
            default_claim_support_evaluation_fixtures()
        )
        assert mined_summary["explicit_fixture_count"] == 0
        assert mined_summary["mined_failure_case_count"] == 1
        assert mined_summary["combined_fixture_count"] == (
            len(default_claim_support_evaluation_fixtures()) + 1
        )
        assert mined_summary["manifest_sha256"]
        assert mined_summary["summary_sha256"]
        assert mined_source["source_evaluation_id"] == source_evaluation_id
        assert (
            mined_source["source_evaluation_name"]
            == "claim_support_judge_mined_failure_source"
        )
        assert mined_source["source_gate_outcome"] == "failed"
        assert mined_source["source_agent_task_id"] == str(source_task_id)
        assert mined_source["source_operator_run_id"] == source_payload["operator_run_id"]
        assert mined_source["source_case_id"] == "mined_claim_support_failure"
        assert mined_source["case_index"] == 0
        assert mined_source["source_fixture_set_id"] == source_fixture_set_id
        assert mined_source["source_fixture_set_name"] == "mined_failure_source_fixture_set"
        assert mined_source["source_fixture_set_version"] == "v1"
        assert mined_source["source_fixture_set_sha256"] == source_fixture_set_sha256
        assert mined_source["source_policy_name"] == "claim_support_judge_calibration_policy"
        assert mined_source["source_policy_version"]
        assert mined_source["source_fixture_sha256"]


def test_claim_support_policy_activation_carries_remediated_mined_failures(
    postgres_integration_harness,
):
    failure_fixture = deepcopy(default_claim_support_evaluation_fixtures()[1])
    failure_fixture["case_id"] = "mined_remediated_claim_support_failure"
    failure_fixture["description"] = (
        "A prior high-threshold support failure should replay and pass after remediation."
    )
    failure_fixture["hard_case_kind"] = "mined_remediated_claim_support_case"

    with postgres_integration_harness.session_factory() as session:
        source_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_claim_support_judge",
                input={
                    "evaluation_name": "claim_support_judge_mined_remediation_source",
                    "fixture_set_name": "mined_remediation_source_fixture_set",
                    "fixtures": [failure_fixture],
                    "min_support_score": 0.99,
                },
                workflow_version="claim_support_policy_mined_remediation_integration",
            ),
        )
        source_task_id = source_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        source_row = session.get(AgentTask, source_task_id)
        assert source_row is not None
        source_payload = source_row.result_json["payload"]
        assert source_payload["summary"]["gate_outcome"] == "failed"
        assert source_payload["summary"]["failed_case_count"] == 1
        assert source_payload["case_results"][0]["expected_verdict"] == "supported"
        assert source_payload["case_results"][0]["predicted_verdict"] == "unsupported"
        initial_policy_id = UUID(source_payload["policy_id"])

        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_claim_support_calibration_policy",
                input={
                    "policy_name": "claim_support_judge_calibration_policy",
                    "policy_version": "v_mined_remediated",
                    "rationale": "prove remediated mined failures gate activation auditably",
                    "min_support_score": 0.34,
                },
                workflow_version="claim_support_policy_mined_remediation_integration",
            ),
        )
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_row = session.get(AgentTask, draft_task_id)
        assert draft_row is not None
        draft_policy_id = UUID(draft_row.result_json["payload"]["policy_id"])
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixture_set_name": "mined_remediated_policy_verification",
                    "fixture_set_version": "v1",
                    "include_mined_failures": True,
                    "mined_failure_limit": 5,
                },
                workflow_version="claim_support_policy_mined_remediation_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_row = session.get(AgentTask, verify_task_id)
        assert verify_row is not None
        verify_payload = verify_row.result_json["payload"]
        mined_summary = verify_payload["mined_failure_summary"]
        mined_source = mined_summary["sources"][0]
        assert verify_payload["verification"]["outcome"] == "passed"
        assert verify_payload["evaluation"]["summary"]["gate_outcome"] == "passed"
        assert verify_payload["evaluation"]["summary"]["case_count"] == (
            len(default_claim_support_evaluation_fixtures()) + 1
        )
        assert mined_summary["mined_failure_case_count"] == 1
        assert mined_summary["summary_sha256"]
        assert mined_source["source_case_id"] == "mined_remediated_claim_support_failure"
        assert (
            mined_source["source_evaluation_name"]
            == "claim_support_judge_mined_remediation_source"
        )
        assert mined_source["source_agent_task_id"] == str(source_task_id)

        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_claim_support_calibration_policy",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "activate remediated mined-failure calibration policy",
                },
                workflow_version="claim_support_policy_mined_remediation_integration",
            ),
        )
        apply_task_id = apply_task.task_id
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="claim-support-operator@example.com",
                approval_note="verification replayed and remediated mined failures",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_row = session.get(AgentTask, apply_task_id)
        assert apply_row is not None
        assert apply_row.status == AgentTaskStatus.COMPLETED.value
        apply_payload = apply_row.result_json["payload"]
        assert apply_payload["activated_policy_id"] == str(draft_policy_id)
        assert apply_payload["previous_active_policy_id"] == str(initial_policy_id)
        verification_mined_summary = apply_payload["verification_mined_failure_summary"]
        assert verification_mined_summary["mined_failure_case_count"] == 1
        assert verification_mined_summary["summary_sha256"] == mined_summary["summary_sha256"]
        assert verification_mined_summary["manifest_sha256"] == mined_summary["manifest_sha256"]
        assert apply_payload["success_metrics"][0]["details"][
            "mined_failure_summary_sha256"
        ] == mined_summary["summary_sha256"]
        assert session.get(ClaimSupportCalibrationPolicy, initial_policy_id).status == "retired"
        assert session.get(ClaimSupportCalibrationPolicy, draft_policy_id).status == "active"


def test_claim_support_policy_apply_blocks_stale_draft_after_verification(
    postgres_integration_harness,
):
    with postgres_integration_harness.session_factory() as session:
        initial_policy = ensure_claim_support_calibration_policy(
            session,
            policy_payload=build_claim_support_calibration_policy_payload(),
        )
        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_claim_support_calibration_policy",
                input={
                    "policy_name": "claim_support_judge_calibration_policy",
                    "policy_version": "v_stale",
                    "rationale": "prove stale draft policy rows cannot be activated",
                    "min_hard_case_kind_count": 1,
                    "required_hard_case_kinds": ["exact_source_support"],
                    "required_verdicts": ["supported"],
                },
                workflow_version="claim_support_policy_stale_apply_integration",
            ),
        )
        initial_policy_id = initial_policy.id
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_row = session.get(AgentTask, draft_task_id)
        assert draft_row is not None
        draft_policy_id = UUID(draft_row.result_json["payload"]["policy_id"])
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixtures": [default_claim_support_evaluation_fixtures()[0]],
                },
                workflow_version="claim_support_policy_stale_apply_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_policy = session.get(ClaimSupportCalibrationPolicy, draft_policy_id)
        assert draft_policy is not None
        draft_policy.policy_payload_json = {
            **dict(draft_policy.policy_payload_json or {}),
            "metadata": {"tampered_after_verification": True},
        }
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_claim_support_calibration_policy",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "stale draft rows must not activate",
                },
                workflow_version="claim_support_policy_stale_apply_integration",
            ),
        )
        apply_task_id = apply_task.task_id
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="claim-support-operator@example.com",
                approval_note="exercise stale draft guard",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_row = session.get(AgentTask, apply_task_id)
        assert apply_row is not None
        assert apply_row.status == AgentTaskStatus.FAILED.value
        assert "Draft policy payload no longer matches" in str(apply_row.error_message)
        assert session.get(ClaimSupportCalibrationPolicy, initial_policy_id).status == "active"
        assert session.get(ClaimSupportCalibrationPolicy, draft_policy_id).status == "draft"


def test_claim_support_policy_promotion_blocks_failed_verification(
    postgres_integration_harness,
):
    with postgres_integration_harness.session_factory() as session:
        ensure_claim_support_calibration_policy(
            session,
            policy_payload=build_claim_support_calibration_policy_payload(),
        )
        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_claim_support_calibration_policy",
                input={
                    "policy_name": "claim_support_judge_calibration_policy",
                    "policy_version": "v_bad",
                    "rationale": "prove failed verification blocks activation",
                    "min_hard_case_kind_count": 1,
                    "required_hard_case_kinds": ["nonexistent_hard_case_kind"],
                    "required_verdicts": ["supported"],
                },
                workflow_version="claim_support_policy_failed_promotion_integration",
            ),
        )
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixtures": [default_claim_support_evaluation_fixtures()[0]],
                },
                workflow_version="claim_support_policy_failed_promotion_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_row = session.get(AgentTask, verify_task_id)
        assert verify_row is not None
        assert verify_row.result_json["payload"]["verification"]["outcome"] == "failed"

        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_claim_support_calibration_policy",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "this failed verification must not activate",
                },
                workflow_version="claim_support_policy_failed_promotion_integration",
            ),
        )
        apply_task_id = apply_task.task_id
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="claim-support-operator@example.com",
                approval_note="exercise failed promotion guard",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_row = session.get(AgentTask, apply_task_id)
        assert apply_row is not None
        assert apply_row.status == AgentTaskStatus.FAILED.value
        draft_row = session.get(AgentTask, draft_task_id)
        assert draft_row is not None
        draft_policy = session.get(
            ClaimSupportCalibrationPolicy,
            UUID(draft_row.result_json["payload"]["policy_id"]),
        )
        assert draft_policy is not None
        assert draft_policy.status == "draft"


def test_claim_support_active_policy_resolution_rejects_retired_identity(
    postgres_integration_harness,
):
    policy_payload = build_claim_support_calibration_policy_payload()

    with postgres_integration_harness.session_factory() as session:
        policy = ensure_claim_support_calibration_policy(
            session,
            policy_payload=policy_payload,
        )
        policy.status = "retired"
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        with pytest.raises(ValueError, match="status retired"):
            ensure_claim_support_calibration_policy(
                session,
                policy_payload=policy_payload,
            )
        with pytest.raises(ValueError, match="status retired"):
            resolve_claim_support_calibration_policy(session)


def test_claim_support_policy_draft_rejects_retired_identity(
    postgres_integration_harness,
):
    with postgres_integration_harness.session_factory() as session:
        draft_policy = draft_claim_support_calibration_policy(
            session,
            policy_name="claim_support_judge_calibration_policy",
            policy_version="v_retired_redraft",
            thresholds={
                "min_overall_accuracy": 1.0,
                "min_verdict_precision": 1.0,
                "min_verdict_recall": 1.0,
                "min_support_score": 0.34,
            },
            min_hard_case_kind_count=1,
            required_hard_case_kinds=["exact_source_support"],
            required_verdicts=["supported"],
            owner="integration-test",
            source="integration_test",
            rationale="prove retired policy identities cannot be redrafted",
        )
        draft_policy.status = "retired"
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        with pytest.raises(ValueError, match="cannot be redrafted"):
            draft_claim_support_calibration_policy(
                session,
                policy_name="claim_support_judge_calibration_policy",
                policy_version="v_retired_redraft",
                thresholds={
                    "min_overall_accuracy": 1.0,
                    "min_verdict_precision": 1.0,
                    "min_verdict_recall": 1.0,
                    "min_support_score": 0.34,
                },
                min_hard_case_kind_count=1,
                required_hard_case_kinds=["exact_source_support"],
                required_verdicts=["supported"],
                owner="integration-test",
                source="integration_test",
                rationale="prove retired policy identities cannot be redrafted",
            )


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
