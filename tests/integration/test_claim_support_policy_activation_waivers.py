from __future__ import annotations

import os
from datetime import timedelta
from uuid import UUID

import pytest

from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskStatus, ClaimSupportCalibrationPolicy
from app.schemas.agent_tasks import AgentTaskApprovalRequest, AgentTaskCreateRequest
from app.services.agent_tasks import approve_agent_task, create_agent_task
from app.services.claim_support_evaluations import (
    build_claim_support_calibration_policy_payload,
    default_claim_support_evaluation_fixtures,
    ensure_claim_support_calibration_policy,
)
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


def test_claim_support_policy_activation_carries_replay_alert_coverage_waiver(
    postgres_integration_harness,
    monkeypatch,
):
    _enable_claim_support_governance_signing(monkeypatch)

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
                    "policy_version": "v_coverage_waiver",
                    "rationale": "activate with an audited replay-alert coverage waiver",
                    "min_hard_case_kind_count": 1,
                    "required_hard_case_kinds": ["exact_source_support"],
                    "required_verdicts": ["supported"],
                },
                workflow_version="claim_support_policy_coverage_waiver_integration",
            ),
        )
        initial_policy_id = initial_policy.id
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        waiver_expires_at = (utcnow() + timedelta(hours=8)).isoformat()
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixtures": [default_claim_support_evaluation_fixtures()[0]],
                    "require_replay_alert_fixture_coverage": False,
                    "replay_alert_fixture_coverage_waived_by": (
                        "claim-support-operator@example.com"
                    ),
                    "replay_alert_fixture_coverage_waiver_reason": (
                        "Exercise audited activation propagation for a coverage waiver."
                    ),
                    "replay_alert_fixture_coverage_waiver_severity": "high",
                    "replay_alert_fixture_coverage_waiver_expires_at": waiver_expires_at,
                    "replay_alert_fixture_coverage_waiver_remediation_owner": (
                        "claim-support-remediation@example.com"
                    ),
                    "include_mined_failures": False,
                },
                workflow_version="claim_support_policy_coverage_waiver_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_row = session.get(AgentTask, verify_task_id)
        assert verify_row is not None
        verify_payload = verify_row.result_json["payload"]
        assert verify_payload["verification"]["outcome"] == "passed"
        waiver = verify_payload["replay_alert_fixture_coverage_waiver"]
        assert waiver["waiver_sha256"]
        assert waiver["artifact_id"]
        assert waiver["waiver_severity"] == "high"
        assert waiver["waiver_expires_at"] == waiver_expires_at
        assert waiver["waiver_remediation_owner"] == (
            "claim-support-remediation@example.com"
        )
        draft_policy_id = UUID(verify_payload["evaluation"]["policy_id"])
        verification_fixture_set_sha256 = verify_payload["evaluation"][
            "fixture_set_sha256"
        ]

        missing_second_approval_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_claim_support_calibration_policy",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "waived activations need second approval",
                },
                workflow_version="claim_support_policy_coverage_waiver_integration",
            ),
        )
        missing_second_approval_task_id = missing_second_approval_task.task_id
        approve_agent_task(
            session,
            missing_second_approval_task_id,
            AgentTaskApprovalRequest(
                approved_by="claim-support-operator@example.com",
                approval_note="regular approval alone is not sufficient",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        failed_apply_row = session.get(AgentTask, missing_second_approval_task_id)
        assert failed_apply_row is not None
        assert failed_apply_row.status == AgentTaskStatus.FAILED.value
        assert "waiver_activation_approved_by" in str(failed_apply_row.error_message)
        assert session.get(ClaimSupportCalibrationPolicy, draft_policy_id).status == "draft"

        same_creator_second_approval_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_claim_support_calibration_policy",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "waiver creator cannot second approve activation",
                    "waiver_activation_approved_by": (
                        "claim-support-operator@example.com"
                    ),
                    "waiver_activation_approval_note": (
                        "This should fail because it reuses the waiver creator."
                    ),
                },
                workflow_version="claim_support_policy_coverage_waiver_integration",
            ),
        )
        same_creator_second_approval_task_id = same_creator_second_approval_task.task_id
        approve_agent_task(
            session,
            same_creator_second_approval_task_id,
            AgentTaskApprovalRequest(
                approved_by="claim-support-primary@example.com",
                approval_note="regular activation approval from primary operator",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        same_creator_apply_row = session.get(
            AgentTask,
            same_creator_second_approval_task_id,
        )
        assert same_creator_apply_row is not None
        assert same_creator_apply_row.status == AgentTaskStatus.FAILED.value
        assert "different operator than the waiver creator" in str(
            same_creator_apply_row.error_message
        )
        assert session.get(ClaimSupportCalibrationPolicy, draft_policy_id).status == "draft"

        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_claim_support_calibration_policy",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "activate the verified waiver propagation policy",
                    "waiver_activation_approved_by": (
                        "claim-support-reviewer@example.com"
                    ),
                    "waiver_activation_approval_note": (
                        "Second reviewer accepted active high-severity waiver "
                        "before activation."
                    ),
                },
                workflow_version="claim_support_policy_coverage_waiver_integration",
            ),
        )
        apply_task_id = apply_task.task_id
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="claim-support-operator@example.com",
                approval_note="waiver artifact reviewed for activation test",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_row = session.get(AgentTask, apply_task_id)
        assert apply_row is not None
        apply_payload = apply_row.result_json["payload"]
        assert apply_payload["verification_replay_alert_fixture_coverage_waiver"][
            "waiver_sha256"
        ] == waiver["waiver_sha256"]
        assert apply_payload["success_metrics"][0]["details"][
            "replay_alert_fixture_coverage_waiver_sha256"
        ] == waiver["waiver_sha256"]
        assert apply_payload["waiver_activation_approval"]["approved_by"] == (
            "claim-support-reviewer@example.com"
        )
        assert (
            apply_payload["success_metrics"][0]["details"]["waiver_activation_approval"][
                "waiver_sha256"
            ]
            == waiver["waiver_sha256"]
        )
        _assert_claim_support_activation_governance(
            session,
            apply_payload=apply_payload,
            activated_policy_id=draft_policy_id,
            previous_policy_id=initial_policy_id,
            verification_fixture_set_sha256=verification_fixture_set_sha256,
            expected_mined_failure_count=0,
            expected_replay_alert_fixture_coverage_waiver_sha256=waiver[
                "waiver_sha256"
            ],
        )


def test_claim_support_policy_activation_blocks_expired_replay_alert_coverage_waiver(
    postgres_integration_harness,
    monkeypatch,
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
                    "policy_version": "v_expiring_coverage_waiver",
                    "rationale": "prove expired coverage waivers cannot activate",
                    "min_hard_case_kind_count": 1,
                    "required_hard_case_kinds": ["exact_source_support"],
                    "required_verdicts": ["supported"],
                },
                workflow_version="claim_support_policy_expired_waiver_integration",
            ),
        )
        initial_policy_id = initial_policy.id
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    waiver_expires_at = utcnow() + timedelta(hours=1)
    with postgres_integration_harness.session_factory() as session:
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixtures": [default_claim_support_evaluation_fixtures()[0]],
                    "require_replay_alert_fixture_coverage": False,
                    "replay_alert_fixture_coverage_waived_by": (
                        "claim-support-operator@example.com"
                    ),
                    "replay_alert_fixture_coverage_waiver_reason": (
                        "Temporary waiver that expires before activation."
                    ),
                    "replay_alert_fixture_coverage_waiver_severity": "medium",
                    "replay_alert_fixture_coverage_waiver_expires_at": (
                        waiver_expires_at.isoformat()
                    ),
                    "include_mined_failures": False,
                },
                workflow_version="claim_support_policy_expired_waiver_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_row = session.get(AgentTask, verify_task_id)
        assert verify_row is not None
        assert verify_row.result_json["payload"]["verification"]["outcome"] == "passed"
        draft_policy_id = UUID(verify_row.result_json["payload"]["evaluation"]["policy_id"])

        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_claim_support_calibration_policy",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "expired waiver must not activate",
                    "waiver_activation_approved_by": (
                        "claim-support-reviewer@example.com"
                    ),
                    "waiver_activation_approval_note": (
                        "Second reviewer approval cannot override expiration."
                    ),
                },
                workflow_version="claim_support_policy_expired_waiver_integration",
            ),
        )
        apply_task_id = apply_task.task_id
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="claim-support-operator@example.com",
                approval_note="regular activation approval",
            ),
        )

    monkeypatch.setattr(
        "app.services.agent_actions.claim_support_activation.utcnow",
        lambda: waiver_expires_at + timedelta(minutes=1),
    )
    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_row = session.get(AgentTask, apply_task_id)
        assert apply_row is not None
        assert apply_row.status == AgentTaskStatus.FAILED.value
        assert "waiver expired" in str(apply_row.error_message)
        assert session.get(ClaimSupportCalibrationPolicy, initial_policy_id).status == "active"
        assert session.get(ClaimSupportCalibrationPolicy, draft_policy_id).status == "draft"
