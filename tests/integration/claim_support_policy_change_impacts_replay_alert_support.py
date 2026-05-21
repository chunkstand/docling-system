from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select

from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTask, AgentTaskArtifact, AgentTaskStatus
from app.db.public.claim_support import ClaimSupportPolicyChangeImpact
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.schemas.agent_task_core import AgentTaskCreateRequest
from app.services.agent_tasks import create_agent_task
from app.services.claim_support_evaluations import (
    build_claim_support_calibration_policy_payload,
    ensure_claim_support_calibration_policy,
)
from app.services.evidence_common import payload_sha256
from tests.integration.claim_support_policy_change_impact_support import (
    _seed_impacted_technical_report_records,
)
from tests.integration.claim_support_policy_integration_task_support import (
    _process_next_task,
)


def _seed_replay_alert_change_impact_state(
    postgres_integration_harness,
) -> dict[str, object]:
    with postgres_integration_harness.session_factory() as session:
        policy = ensure_claim_support_calibration_policy(
            session,
            policy_payload=build_claim_support_calibration_policy_payload(),
        )
        impacted = _seed_impacted_technical_report_records(session)
        now = utcnow() - timedelta(hours=48)
        activation_task = AgentTask(
            id=uuid4(),
            task_type="apply_claim_support_calibration_policy",
            status=AgentTaskStatus.COMPLETED.value,
            priority=100,
            side_effect_level="promotable",
            requires_approval=True,
            input_json={},
            result_json={},
            workflow_version="claim_support_policy_change_impact_integration",
            model_settings_json={},
            created_at=now,
            updated_at=now,
            completed_at=now,
        )
        session.add(activation_task)
        session.flush()
        activation_task_id = activation_task.id
        change_impact_id = uuid4()
        extra_change_impact_id = uuid4()
        fresh_change_impact_id = uuid4()
        for row_change_impact_id in [
            change_impact_id,
            extra_change_impact_id,
            fresh_change_impact_id,
        ]:
            replay_status = (
                "blocked" if row_change_impact_id == extra_change_impact_id else "pending"
            )
            row_created_at = (
                utcnow() if row_change_impact_id == fresh_change_impact_id else now
            )
            impact_payload = {
                "schema_name": "claim_support_policy_change_impact",
                "schema_version": "1.0",
                "change_impact_id": str(row_change_impact_id),
                "replay_recommendations": [
                    {
                        "action": "rerun_draft_technical_report",
                        "target_task_id": str(impacted["draft_task_id"]),
                        "reason": "valid source should not be queued before all work validates",
                        "priority": "high",
                    },
                    {
                        "action": "rerun_verify_technical_report",
                        "target_task_id": str(impacted["draft_task_id"]),
                        "prior_verification_task_id": str(uuid4()),
                        "reason": "missing verifier task should fail prevalidation",
                        "priority": "high",
                    },
                ],
            }
            session.add(
                ClaimSupportPolicyChangeImpact(
                    id=row_change_impact_id,
                    activation_task_id=activation_task_id,
                    activated_policy_id=policy.id,
                    previous_policy_id=None,
                    semantic_governance_event_id=None,
                    governance_artifact_id=None,
                    impact_scope="claim_support_policy:claim_support_judge_calibration_policy",
                    policy_name=policy.policy_name,
                    policy_version=policy.policy_version,
                    activated_policy_sha256=policy.policy_sha256,
                    previous_policy_sha256=None,
                    affected_support_judgment_count=1,
                    affected_generated_document_count=1,
                    affected_verification_count=1,
                    replay_recommended_count=2,
                    replay_status=replay_status,
                    impacted_claim_derivation_ids_json=[str(impacted["derivation_id"])],
                    impacted_task_ids_json=[str(impacted["draft_task_id"])],
                    impacted_verification_task_ids_json=[str(impacted["verify_task_id"])],
                    impact_payload_json=impact_payload,
                    impact_payload_sha256=payload_sha256(impact_payload),
                    replay_task_ids_json=[],
                    replay_task_plan_json={},
                    replay_closure_json={},
                    replay_status_updated_at=row_created_at,
                    created_at=row_created_at,
                )
            )
        session.commit()

    return {
        "activation_task_id": activation_task_id,
        "change_impact_id": change_impact_id,
        "extra_change_impact_id": extra_change_impact_id,
        "fresh_change_impact_id": fresh_change_impact_id,
        "impacted": impacted,
    }


def _build_replay_alert_fixture_promotion_state(
    postgres_integration_harness,
) -> dict[str, object]:
    state = _seed_replay_alert_change_impact_state(postgres_integration_harness)

    escalation_response = postgres_integration_harness.client.post(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/escalations"
        "?limit=5&stale_after_hours=24",
        json={"requested_by": "claim-support-operator@example.com"},
    )
    assert escalation_response.status_code == 200

    duplicate_escalation_response = postgres_integration_harness.client.post(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/escalations"
        "?limit=5&stale_after_hours=24",
        json={"requested_by": "claim-support-operator@example.com"},
    )
    assert duplicate_escalation_response.status_code == 200

    with postgres_integration_harness.session_factory() as session:
        escalation_events = list(
            session.scalars(
                select(SemanticGovernanceEvent)
                .where(
                    SemanticGovernanceEvent.subject_table
                    == "claim_support_policy_change_impacts",
                    SemanticGovernanceEvent.event_kind
                    == "claim_support_policy_impact_replay_escalated",
                )
                .order_by(SemanticGovernanceEvent.created_at.asc())
            )
        )
        stale_escalation_created_at = utcnow() - timedelta(hours=25)
        for event in escalation_events:
            event.created_at = stale_escalation_created_at
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        unconverted_gate_draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_claim_support_calibration_policy",
                input={
                    "policy_name": "claim_support_judge_calibration_policy",
                    "policy_version": "v_replay_alert_unconverted_gate",
                    "rationale": (
                        "prove stale replay escalations must become fixture coverage"
                    ),
                },
                workflow_version="claim_support_policy_replay_alert_coverage",
            ),
        )
        unconverted_gate_draft_task_id = unconverted_gate_draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        unconverted_gate_verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(unconverted_gate_draft_task_id),
                    "fixture_set_name": "integration_replay_alert_unconverted_gate",
                    "fixture_set_version": "v1",
                    "include_replay_alert_fixtures": True,
                    "replay_alert_fixture_limit": 10,
                    "require_replay_alert_fixture_coverage": True,
                    "include_mined_failures": False,
                },
                workflow_version="claim_support_policy_replay_alert_coverage",
            ),
        )
        unconverted_gate_verify_task_id = unconverted_gate_verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        unconverted_gate_verify_row = session.get(
            AgentTask,
            unconverted_gate_verify_task_id,
        )
        assert unconverted_gate_verify_row is not None
        unconverted_gate_payload = unconverted_gate_verify_row.result_json["payload"]

    with postgres_integration_harness.session_factory() as session:
        waiver_expires_at = (utcnow() + timedelta(hours=8)).isoformat()
        waived_gate_verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(unconverted_gate_draft_task_id),
                    "fixture_set_name": "integration_replay_alert_coverage_waiver",
                    "fixture_set_version": "v1",
                    "include_replay_alert_fixtures": True,
                    "replay_alert_fixture_limit": 1,
                    "require_replay_alert_fixture_coverage": False,
                    "replay_alert_fixture_coverage_waived_by": (
                        "claim-support-operator@example.com"
                    ),
                    "replay_alert_fixture_coverage_waiver_reason": (
                        "Emergency calibration validation before replay-alert fixtures "
                        "are promoted."
                    ),
                    "replay_alert_fixture_coverage_waiver_severity": "critical",
                    "replay_alert_fixture_coverage_waiver_expires_at": waiver_expires_at,
                    "replay_alert_fixture_coverage_waiver_remediation_owner": (
                        "claim-support-remediation@example.com"
                    ),
                    "include_mined_failures": False,
                },
                workflow_version="claim_support_policy_replay_alert_coverage",
            ),
        )
        waived_gate_verify_task_id = waived_gate_verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        waived_gate_verify_row = session.get(AgentTask, waived_gate_verify_task_id)
        assert waived_gate_verify_row is not None
        waived_gate_payload = waived_gate_verify_row.result_json["payload"]
        waiver = waived_gate_payload["replay_alert_fixture_coverage_waiver"]
        session.add(
            AgentTaskArtifact(
                task_id=waived_gate_verify_task_id,
                artifact_kind="claim_support_replay_alert_fixture_coverage_waiver",
                storage_path=None,
                payload_json={
                    "schema_name": "claim_support_replay_alert_fixture_coverage_waiver",
                    "schema_version": "1.1",
                    "waiver_sha256": "expired-waiver-fixture-signal",
                    "waiver_severity": "medium",
                    "waiver_expires_at": (
                        utcnow() - timedelta(hours=1)
                    ).isoformat(),
                    "stale_unconverted_escalation_event_count": 0,
                },
                created_at=utcnow(),
            )
        )
        session.commit()

    first_promotion_response = postgres_integration_harness.client.post(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/fixture-promotions"
        "?limit=1&stale_after_hours=24",
        json={
            "fixture_set_name": "integration_replay_alert_promotions",
            "fixture_set_version": "v1",
            "requested_by": "claim-support-operator@example.com",
        },
    )
    assert first_promotion_response.status_code == 200
    first_promotion_payload = first_promotion_response.json()

    second_promotion_response = postgres_integration_harness.client.post(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/fixture-promotions"
        "?limit=5&stale_after_hours=24",
        json={
            "fixture_set_name": "integration_replay_alert_promotions",
            "fixture_set_version": "v1",
            "requested_by": "claim-support-operator@example.com",
        },
    )
    assert second_promotion_response.status_code == 200
    promotion_payload = second_promotion_response.json()

    duplicate_promotion_response = postgres_integration_harness.client.post(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/fixture-promotions"
        "?limit=5&stale_after_hours=24",
        json={
            "fixture_set_name": "integration_replay_alert_promotions",
            "fixture_set_version": "v1",
            "requested_by": "claim-support-operator@example.com",
        },
    )
    assert duplicate_promotion_response.status_code == 200

    with postgres_integration_harness.session_factory() as session:
        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_claim_support_calibration_policy",
                input={
                    "policy_name": "claim_support_judge_calibration_policy",
                    "policy_version": "v_replay_alert_coverage",
                    "rationale": "require promoted replay-alert fixture coverage",
                    "min_hard_case_kind_count": 2,
                    "required_hard_case_kinds": [
                        "replay_alert_blocked_policy_change_impact",
                        "replay_alert_stale_policy_change_impact",
                    ],
                    "required_verdicts": [
                        "supported",
                        "unsupported",
                        "insufficient_evidence",
                    ],
                },
                workflow_version="claim_support_policy_replay_alert_coverage",
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
                    "fixture_set_name": "integration_replay_alert_coverage_verification",
                    "fixture_set_version": "v1",
                    "include_replay_alert_fixtures": True,
                    "replay_alert_fixture_limit": 10,
                    "require_replay_alert_fixture_coverage": True,
                    "include_mined_failures": False,
                },
                workflow_version="claim_support_policy_replay_alert_coverage",
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_row = session.get(AgentTask, verify_task_id)
        assert verify_row is not None
        verify_payload = verify_row.result_json["payload"]

    return {
        **state,
        "duplicate_escalation_payload": duplicate_escalation_response.json(),
        "unconverted_gate_draft_task_id": unconverted_gate_draft_task_id,
        "unconverted_gate_verify_task_id": unconverted_gate_verify_task_id,
        "unconverted_gate_payload": unconverted_gate_payload,
        "waived_gate_verify_task_id": waived_gate_verify_task_id,
        "waived_gate_payload": waived_gate_payload,
        "waiver": waiver,
        "first_promotion_payload": first_promotion_payload,
        "promotion_payload": promotion_payload,
        "duplicate_promotion_payload": duplicate_promotion_response.json(),
        "draft_task_id": draft_task_id,
        "verify_task_id": verify_task_id,
        "verify_payload": verify_payload,
    }
