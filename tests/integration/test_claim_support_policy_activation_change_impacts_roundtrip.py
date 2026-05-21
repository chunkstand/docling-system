from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.time import utcnow
from app.db.public.agent_tasks import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskStatus,
    AgentTaskVerification,
)
from app.db.public.claim_support import (
    ClaimSupportCalibrationPolicy,
    ClaimSupportPolicyChangeImpact,
)
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.schemas.agent_tasks import AgentTaskApprovalRequest, AgentTaskCreateRequest
from app.services.agent_task_worker import finalize_agent_task_success
from app.services.agent_tasks import approve_agent_task, create_agent_task
from app.services.claim_support_evaluations import (
    build_claim_support_calibration_policy_payload,
    default_claim_support_evaluation_fixtures,
    ensure_claim_support_calibration_policy,
)
from app.services.evidence import get_agent_task_audit_bundle, payload_sha256
from tests.integration.claim_support_policy_activation_governance_assertions import (
    _assert_claim_support_activation_governance,
)
from tests.integration.claim_support_policy_activation_governance_triggers import (
    _enable_claim_support_governance_signing,
)
from tests.integration.claim_support_policy_change_impact_support import (
    _seed_impacted_technical_report_records,
)
from tests.integration.claim_support_policy_integration_task_support import (
    _process_next_task,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_claim_support_policy_activation_records_change_impact_for_prior_reports(
    postgres_integration_harness,
    monkeypatch,
):
    _enable_claim_support_governance_signing(monkeypatch)

    with postgres_integration_harness.session_factory() as session:
        initial_policy = ensure_claim_support_calibration_policy(
            session,
            policy_payload=build_claim_support_calibration_policy_payload(),
        )
        impacted = _seed_impacted_technical_report_records(session)
        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_claim_support_calibration_policy",
                input={
                    "policy_name": "claim_support_judge_calibration_policy",
                    "policy_version": "v_change_impact",
                    "rationale": "prove policy activation identifies stale report support gates",
                    "min_hard_case_kind_count": 1,
                    "required_hard_case_kinds": ["exact_source_support"],
                    "required_verdicts": ["supported"],
                },
                workflow_version="claim_support_policy_change_impact_integration",
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
                workflow_version="claim_support_policy_change_impact_integration",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_row = session.get(AgentTask, verify_task_id)
        assert verify_row is not None
        verify_payload = verify_row.result_json["payload"]
        assert verify_payload["verification"]["outcome"] == "passed"
        verification_fixture_set_sha256 = verify_payload["evaluation"][
            "fixture_set_sha256"
        ]
        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_claim_support_calibration_policy",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "activate policy and enumerate downstream report impact",
                },
                workflow_version="claim_support_policy_change_impact_integration",
            ),
        )
        apply_task_id = apply_task.task_id
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="claim-support-operator@example.com",
                approval_note="impact analysis required before relying on prior reports",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_row = session.get(AgentTask, apply_task_id)
        assert apply_row is not None
        assert apply_row.status == AgentTaskStatus.COMPLETED.value
        apply_payload = apply_row.result_json["payload"]
        governance_payload = _assert_claim_support_activation_governance(
            session,
            apply_payload=apply_payload,
            activated_policy_id=draft_policy_id,
            previous_policy_id=initial_policy_id,
            verification_fixture_set_sha256=verification_fixture_set_sha256,
            expected_mined_failure_count=0,
            expected_affected_support_judgment_count=1,
            expected_affected_generated_document_count=1,
            expected_affected_verification_count=1,
            expected_impacted_draft_task_id=impacted["draft_task_id"],
            expected_impacted_verification_task_id=impacted["verify_task_id"],
            expected_impacted_derivation_id=impacted["derivation_id"],
        )
        change_impact = governance_payload["activation_change_impact"]
        assert change_impact["affected_support_judgments"][0][
            "support_judgment_sha256"
        ] == impacted["support_judgment_sha256"]
        assert {
            row["action"] for row in change_impact["replay_recommendations"]
        } == {"rerun_draft_technical_report", "rerun_verify_technical_report"}
        assert (
            session.get(ClaimSupportCalibrationPolicy, initial_policy_id).status
            == "retired"
        )
        assert (
            session.get(ClaimSupportCalibrationPolicy, draft_policy_id).status
            == "active"
        )

    replay_response = postgres_integration_harness.client.post(
        (
            "/agent-tasks/claim-support-policy-change-impacts/"
            f"{apply_payload['activation_change_impact_id']}/replay-tasks"
        ),
        json={"requested_by": "claim-support-operator@example.com"},
    )
    assert replay_response.status_code == 200
    replay_payload = replay_response.json()
    assert replay_payload["replay_status"] == "queued"
    assert len(replay_payload["replay_task_ids"]) == 2
    replay_plan = dict(replay_payload["replay_task_plan"])
    replay_plan_sha256 = replay_plan.pop("replay_task_plan_sha256")
    assert payload_sha256(replay_plan) == replay_plan_sha256
    replay_tasks = {
        row["task_type"]: row for row in replay_payload["replay_task_plan"]["tasks"]
    }
    replay_draft_task_id = UUID(
        replay_tasks["draft_technical_report"]["replay_task_id"]
    )
    replay_verify_task_id = UUID(
        replay_tasks["verify_technical_report"]["replay_task_id"]
    )
    assert replay_tasks["draft_technical_report"]["source_task_input_sha256"]
    assert replay_tasks["draft_technical_report"]["source_task_result_sha256"]
    assert replay_tasks["draft_technical_report"]["replay_task_input_sha256"]

    with postgres_integration_harness.session_factory() as session:
        impact_row = session.get(
            ClaimSupportPolicyChangeImpact,
            UUID(apply_payload["activation_change_impact_id"]),
        )
        assert impact_row is not None
        assert impact_row.replay_status == "queued"
        assert impact_row.replay_closure_sha256 is None
        assert impact_row.replay_task_ids_json == [
            str(replay_draft_task_id),
            str(replay_verify_task_id),
        ]

        replay_draft = session.get(AgentTask, replay_draft_task_id)
        replay_verify = session.get(AgentTask, replay_verify_task_id)
        assert replay_draft is not None
        assert replay_verify is not None
        assert replay_draft.parent_task_id == apply_task_id
        assert (
            replay_draft.input_json["target_task_id"]
            == str(impacted["harness_task_id"])
        )
        assert replay_draft.status == AgentTaskStatus.QUEUED.value
        assert replay_verify.input_json["target_task_id"] == str(replay_draft_task_id)
        assert replay_verify.status == AgentTaskStatus.BLOCKED.value

    duplicate_replay_response = postgres_integration_harness.client.post(
        (
            "/agent-tasks/claim-support-policy-change-impacts/"
            f"{apply_payload['activation_change_impact_id']}/replay-tasks"
        ),
        json={"requested_by": "claim-support-operator@example.com"},
    )
    assert duplicate_replay_response.status_code == 200
    assert duplicate_replay_response.json()["replay_task_ids"] == replay_payload[
        "replay_task_ids"
    ]
    with postgres_integration_harness.session_factory() as session:
        replay_rows = (
            session.execute(
                select(AgentTask).where(
                    AgentTask.workflow_version
                    == "claim_support_policy_change_impact_replay_v1"
                )
            )
            .scalars()
            .all()
        )
        assert {row.id for row in replay_rows} == {
            replay_draft_task_id,
            replay_verify_task_id,
        }

    with postgres_integration_harness.session_factory() as session:
        impact_row = session.get(
            ClaimSupportPolicyChangeImpact,
            UUID(apply_payload["activation_change_impact_id"]),
        )
        assert impact_row is not None
        impact_row.replay_task_plan_json = {
            **dict(impact_row.replay_task_plan_json or {}),
            "created_by": "tampered-operator@example.com",
        }
        session.commit()

    tampered_plan_response = postgres_integration_harness.client.post(
        (
            "/agent-tasks/claim-support-policy-change-impacts/"
            f"{apply_payload['activation_change_impact_id']}/replay-status"
        ),
    )
    assert tampered_plan_response.status_code == 409
    assert (
        tampered_plan_response.json()["error_code"]
        == "claim_support_impact_replay_plan_hash_mismatch"
    )

    with postgres_integration_harness.session_factory() as session:
        impact_row = session.get(
            ClaimSupportPolicyChangeImpact,
            UUID(apply_payload["activation_change_impact_id"]),
        )
        assert impact_row is not None
        impact_row.replay_task_plan_json = replay_payload["replay_task_plan"]
        session.commit()

    preclosure_response = postgres_integration_harness.client.post(
        (
            "/agent-tasks/claim-support-policy-change-impacts/"
            f"{apply_payload['activation_change_impact_id']}/replay-status"
        ),
    )
    assert preclosure_response.status_code == 200
    preclosure_payload = preclosure_response.json()
    assert preclosure_payload["replay_status"] == "queued"
    assert preclosure_payload["replay_closure_sha256"] is None
    assert preclosure_payload["replay_closure"]["closed"] is False

    with postgres_integration_harness.session_factory() as session:
        preclosure_audit_bundle = get_agent_task_audit_bundle(
            session,
            impacted["verify_task_id"],
        )
        policy_impacts = preclosure_audit_bundle["change_impact"][
            "claim_support_policy_change_impacts"
        ]
        assert preclosure_audit_bundle["change_impact"]["impacted"] is True
        assert policy_impacts["related_count"] == 1
        assert policy_impacts["open_count"] == 1
        assert policy_impacts["clear"] is False

    worklist_response = postgres_integration_harness.client.get(
        "/agent-tasks/claim-support-policy-change-impacts/worklist"
        "?limit=5&stale_after_hours=1"
    )
    assert worklist_response.status_code == 200
    worklist_items = worklist_response.json()["items"]
    worklist_item = next(
        row
        for row in worklist_items
        if row["change_impact"]["change_impact_id"]
        == apply_payload["activation_change_impact_id"]
    )
    assert worklist_item["recommended_action"] == "monitor_replay"
    assert worklist_item["affected_verification_task_ids"] == [
        str(impacted["verify_task_id"])
    ]
    assert worklist_item["audit_bundle_task_ids"] == [str(impacted["verify_task_id"])]
    assert {row["task_id"] for row in worklist_item["replay_tasks"]} == {
        str(replay_draft_task_id),
        str(replay_verify_task_id),
    }
    assert {
        row["task_id"]
        for row in worklist_item["replay_tasks"]
        if row["is_required_for_closure"]
    } == {str(replay_verify_task_id)}
    assert worklist_item["operator_links"]["affected_audit_bundles"] == [
        f"/agent-tasks/{impacted['verify_task_id']}/audit-bundle"
    ]

    decision_signals_response = postgres_integration_harness.client.get(
        "/agent-tasks/analytics/decision-signals"
    )
    assert decision_signals_response.status_code == 200
    assert any(
        row["task_type"] == "claim_support_policy_change_impact_replay"
        and row["status"] == "watch"
        for row in decision_signals_response.json()
    )

    with postgres_integration_harness.session_factory() as session:
        now = utcnow()
        replay_draft = session.get(AgentTask, replay_draft_task_id)
        replay_verify = session.get(AgentTask, replay_verify_task_id)
        assert replay_draft is not None
        assert replay_verify is not None
        replay_draft.status = AgentTaskStatus.COMPLETED.value
        replay_draft.completed_at = now
        replay_draft.updated_at = now
        replay_verify.status = AgentTaskStatus.COMPLETED.value
        replay_verify.completed_at = now
        replay_verify.updated_at = now
        session.add(
            AgentTaskVerification(
                id=uuid4(),
                target_task_id=replay_draft_task_id,
                verification_task_id=replay_verify_task_id,
                verifier_type="technical_report_gate",
                outcome="passed",
                metrics_json={"claim_count": 1},
                reasons_json=[],
                details_json={
                    "replay_of_change_impact_id": apply_payload[
                        "activation_change_impact_id"
                    ]
                },
                created_at=now,
                completed_at=now,
            )
        )
        finalize_agent_task_success(
            session,
            replay_verify,
            {
                "schema_name": "synthetic_replay_verification_completion",
                "payload": {
                    "verification": {
                        "target_task_id": str(replay_draft_task_id),
                        "verification_task_id": str(replay_verify_task_id),
                        "outcome": "passed",
                    }
                },
            },
            storage_service=postgres_integration_harness.storage_service,
        )

    detail_response = postgres_integration_harness.client.get(
        (
            "/agent-tasks/claim-support-policy-change-impacts/"
            f"{apply_payload['activation_change_impact_id']}"
        ),
    )
    assert detail_response.status_code == 200
    closure_payload = detail_response.json()
    assert closure_payload["replay_status"] == "closed"
    assert closure_payload["replay_closure_sha256"]
    assert closure_payload["replay_closure"]["closed"] is True
    assert closure_payload["replay_closure"]["passed_verification_task_count"] == 1

    idempotent_closure_response = postgres_integration_harness.client.post(
        (
            "/agent-tasks/claim-support-policy-change-impacts/"
            f"{apply_payload['activation_change_impact_id']}/replay-status"
        ),
    )
    assert idempotent_closure_response.status_code == 200
    assert idempotent_closure_response.json()["replay_status"] == "closed"

    summary_response = postgres_integration_harness.client.get(
        "/agent-tasks/claim-support-policy-change-impacts/summary"
    )
    assert summary_response.status_code == 200
    assert summary_response.json()["replay_status_counts"]["closed"] >= 1

    open_worklist_response = postgres_integration_harness.client.get(
        "/agent-tasks/claim-support-policy-change-impacts/worklist?limit=10"
    )
    assert open_worklist_response.status_code == 200
    assert all(
        row["change_impact"]["change_impact_id"]
        != apply_payload["activation_change_impact_id"]
        for row in open_worklist_response.json()["items"]
    )

    closed_worklist_response = postgres_integration_harness.client.get(
        "/agent-tasks/claim-support-policy-change-impacts/worklist"
        "?include_closed=true&limit=10"
    )
    assert closed_worklist_response.status_code == 200
    closed_worklist_item = next(
        row
        for row in closed_worklist_response.json()["items"]
        if row["change_impact"]["change_impact_id"]
        == apply_payload["activation_change_impact_id"]
    )
    assert closed_worklist_item["severity"] == "cleared"
    assert closed_worklist_item["closure_receipt_sha256"]
    assert closed_worklist_item["closure_events"]
    assert closed_worklist_item["operator_links"]["closure_artifact"]

    with postgres_integration_harness.session_factory() as session:
        closure_events = list(
            session.scalars(
                select(SemanticGovernanceEvent)
                .where(
                    SemanticGovernanceEvent.subject_table
                    == "claim_support_policy_change_impacts",
                    SemanticGovernanceEvent.subject_id
                    == UUID(apply_payload["activation_change_impact_id"]),
                    SemanticGovernanceEvent.event_kind
                    == "claim_support_policy_impact_replay_closed",
                )
                .order_by(SemanticGovernanceEvent.created_at.asc())
            )
        )
        assert len(closure_events) == 1
        closure_event = closure_events[0]
        assert closure_event.task_id == replay_verify_task_id
        assert closure_event.receipt_sha256
        closure_artifact = session.get(
            AgentTaskArtifact,
            closure_event.agent_task_artifact_id,
        )
        assert closure_artifact is not None
        assert (
            closure_artifact.artifact_kind
            == "claim_support_policy_impact_replay_closure"
        )
        assert (
            closure_artifact.payload_json["receipt_sha256"]
            == closure_event.receipt_sha256
        )
        assert (
            closure_event.event_payload_json[
                "claim_support_policy_impact_replay_closure"
            ]["replay_closure_sha256"]
            == closure_payload["replay_closure_sha256"]
        )

        closed_audit_bundle = get_agent_task_audit_bundle(
            session,
            impacted["verify_task_id"],
        )
        closed_policy_impacts = closed_audit_bundle["change_impact"][
            "claim_support_policy_change_impacts"
        ]
        assert closed_audit_bundle["change_impact"]["impacted"] is False
        assert closed_policy_impacts["related_count"] == 1
        assert closed_policy_impacts["open_count"] == 0
        assert closed_policy_impacts["closed_count"] == 1
        assert closed_policy_impacts["clear"] is True
        assert closed_policy_impacts["impacts"][0]["closure_governance_events"][0][
            "event_id"
        ] == str(closure_event.id)
