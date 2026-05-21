from __future__ import annotations

import os
from uuid import UUID

import pytest
from sqlalchemy import delete, select, text, update

from app.db.public.agent_tasks import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskArtifactImmutabilityEvent,
    AgentTaskStatus,
)
from app.db.public.claim_support import ClaimSupportCalibrationPolicy
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
    _drop_claim_support_governance_immutability_trigger,
    _enable_claim_support_governance_signing,
    _install_claim_support_governance_immutability_trigger,
)
from tests.integration.claim_support_policy_integration_task_support import (
    _process_next_task,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)

def test_claim_support_policy_promotion_workflow_activates_verified_policy(
    postgres_integration_harness,
    postgres_schema_engine,
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
        _assert_claim_support_activation_governance(
            session,
            apply_payload=apply_payload,
            activated_policy_id=draft_policy_id,
            previous_policy_id=initial_policy_id,
            verification_fixture_set_sha256=verification_fixture_set_sha256,
            expected_mined_failure_count=0,
        )
        governance_artifact_id = UUID(apply_payload["activation_governance_artifact_id"])

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

    schema_name = _install_claim_support_governance_immutability_trigger(
        postgres_integration_harness,
        postgres_schema_engine,
    )
    try:
        with postgres_integration_harness.session_factory() as session:
            session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
            session.execute(
                update(AgentTaskArtifact)
                .where(AgentTaskArtifact.id == governance_artifact_id)
                .values(payload_json={"tampered": True})
            )
            session.commit()

        with postgres_integration_harness.session_factory() as session:
            governance_artifact = session.get(AgentTaskArtifact, governance_artifact_id)
            assert governance_artifact is not None
            assert (
                governance_artifact.payload_json["schema_name"]
                == "claim_support_policy_activation_governance"
            )
            mutation_events = list(
                session.scalars(
                    select(AgentTaskArtifactImmutabilityEvent).where(
                        AgentTaskArtifactImmutabilityEvent.artifact_id
                        == governance_artifact_id
                    )
                )
            )
            assert len(mutation_events) == 1
            assert mutation_events[0].event_kind == "mutation_blocked"
            assert mutation_events[0].mutation_operation == "UPDATE"
            assert mutation_events[0].attempted_payload_sha256 is None

        with postgres_integration_harness.session_factory() as session:
            session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
            session.execute(
                delete(AgentTaskArtifact).where(AgentTaskArtifact.id == governance_artifact_id)
            )
            session.commit()

        with postgres_integration_harness.session_factory() as session:
            assert session.get(AgentTaskArtifact, governance_artifact_id) is not None
            mutation_events = list(
                session.scalars(
                    select(AgentTaskArtifactImmutabilityEvent)
                    .where(
                        AgentTaskArtifactImmutabilityEvent.artifact_id
                        == governance_artifact_id
                    )
                    .order_by(AgentTaskArtifactImmutabilityEvent.created_at.asc())
                )
            )
            assert [row.mutation_operation for row in mutation_events] == ["UPDATE", "DELETE"]
    finally:
        _drop_claim_support_governance_immutability_trigger(
            postgres_integration_harness,
            schema_name,
        )

    with postgres_integration_harness.session_factory() as session:
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
