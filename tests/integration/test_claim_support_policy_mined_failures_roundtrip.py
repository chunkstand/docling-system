from __future__ import annotations

import os
from copy import deepcopy
from uuid import UUID

import pytest

from app.db.public.agent_tasks import AgentTask, AgentTaskStatus
from app.db.public.claim_support import ClaimSupportCalibrationPolicy
from app.schemas.agent_tasks import AgentTaskApprovalRequest, AgentTaskCreateRequest
from app.services.agent_tasks import approve_agent_task, create_agent_task
from app.services.claim_support_evaluations import default_claim_support_evaluation_fixtures
from tests.integration.claim_support_policy_activation_governance_assertions import (
    _assert_claim_support_activation_governance,
)
from tests.integration.claim_support_policy_activation_governance_triggers import (
    _enable_claim_support_governance_signing,
)
from tests.integration.claim_support_policy_integration_task_support import (
    _process_next_task,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)

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
    monkeypatch,
):
    _enable_claim_support_governance_signing(monkeypatch)

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
        verification_fixture_set_sha256 = verify_payload["evaluation"]["fixture_set_sha256"]
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
        _assert_claim_support_activation_governance(
            session,
            apply_payload=apply_payload,
            activated_policy_id=draft_policy_id,
            previous_policy_id=initial_policy_id,
            verification_fixture_set_sha256=verification_fixture_set_sha256,
            expected_mined_failure_count=1,
            expected_mined_failure_summary_sha256=mined_summary["summary_sha256"],
        )
        assert session.get(ClaimSupportCalibrationPolicy, initial_policy_id).status == "retired"
        assert session.get(ClaimSupportCalibrationPolicy, draft_policy_id).status == "active"
