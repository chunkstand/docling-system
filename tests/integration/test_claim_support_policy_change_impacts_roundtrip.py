from __future__ import annotations

import os
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text, update

from app.core.time import utcnow
from app.db.public.agent_tasks import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskArtifactImmutabilityEvent,
    AgentTaskStatus,
)
from app.db.public.claim_support import (
    ClaimSupportPolicyChangeImpact,
    ClaimSupportReplayAlertFixtureCoverageWaiverEscalation,
)
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.services.claim_support_evaluations import (
    build_claim_support_calibration_policy_payload,
    ensure_claim_support_calibration_policy,
)
from app.services.claim_support_policy_governance import (
    persist_claim_support_policy_change_impact,
)
from app.services.claim_support_replay_alert_waivers import (
    record_replay_alert_fixture_coverage_waiver_ledger,
)
from app.services.evidence import payload_sha256
from tests.integration.claim_support_policy_activation_governance_triggers import (
    _drop_claim_support_governance_immutability_trigger,
    _install_claim_support_governance_immutability_trigger,
)
from tests.integration.claim_support_policy_change_impact_support import (
    _claim_support_change_impact_payload_without_replay,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_claim_support_change_impact_without_replay_records_terminal_closure(
    postgres_integration_harness,
    postgres_schema_engine,
):
    change_impact_id = uuid4()
    with postgres_integration_harness.session_factory() as session:
        policy = ensure_claim_support_calibration_policy(
            session,
            policy_payload=build_claim_support_calibration_policy_payload(),
        )
        activation_task = AgentTask(
            id=uuid4(),
            task_type="apply_claim_support_policy",
            status=AgentTaskStatus.COMPLETED.value,
            priority=100,
            side_effect_level="promotable",
            requires_approval=True,
            input_json={},
            result_json={},
            workflow_version="claim_support_policy_activation_v1",
            model_settings_json={},
            created_at=utcnow(),
            updated_at=utcnow(),
            completed_at=utcnow(),
        )
        session.add(activation_task)
        session.flush()
        activation_task_id = activation_task.id

        row = persist_claim_support_policy_change_impact(
            session,
            impact_payload=_claim_support_change_impact_payload_without_replay(
                change_impact_id=change_impact_id,
            ),
            task=activation_task,
            activated_policy=policy,
            previous_active_policy=None,
            governance_event=None,
            governance_artifact=None,
            change_impact_id=change_impact_id,
            storage_service=postgres_integration_harness.storage_service,
        )
        session.commit()
        assert row.replay_status == "no_action_required"
        assert row.replay_closed_at is not None
        assert row.replay_closure_sha256
        assert row.replay_closure_json["status"] == "no_action_required"
        assert row.replay_closure_json["closed"] is True

    with postgres_integration_harness.session_factory() as session:
        closure_events = list(
            session.scalars(
                select(SemanticGovernanceEvent)
                .where(
                    SemanticGovernanceEvent.subject_table
                    == "claim_support_policy_change_impacts",
                    SemanticGovernanceEvent.subject_id == change_impact_id,
                    SemanticGovernanceEvent.event_kind
                    == "claim_support_policy_impact_replay_closed",
                )
                .order_by(SemanticGovernanceEvent.created_at.asc())
            )
        )
        assert len(closure_events) == 1
        closure_event = closure_events[0]
        assert closure_event.task_id == activation_task_id
        assert closure_event.receipt_sha256
        closure_artifact = session.get(
            AgentTaskArtifact,
            closure_event.agent_task_artifact_id,
        )
        assert closure_artifact is not None
        assert closure_artifact.task_id == activation_task_id
        assert (
            closure_artifact.artifact_kind
            == "claim_support_policy_impact_replay_closure"
        )
        assert (
            closure_artifact.payload_json["receipt_sha256"]
            == closure_event.receipt_sha256
        )
        closure_artifact_id = closure_artifact.id

    schema_name = _install_claim_support_governance_immutability_trigger(
        postgres_integration_harness,
        postgres_schema_engine,
    )
    try:
        with postgres_integration_harness.session_factory() as session:
            session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
            session.execute(
                update(AgentTaskArtifact)
                .where(AgentTaskArtifact.id == closure_artifact_id)
                .values(payload_json={"tampered": True})
            )
            session.commit()

        with postgres_integration_harness.session_factory() as session:
            closure_artifact = session.get(AgentTaskArtifact, closure_artifact_id)
            assert closure_artifact is not None
            assert (
                closure_artifact.payload_json["schema_name"]
                == "claim_support_policy_impact_replay_closure_receipt"
            )
            mutation_events = list(
                session.scalars(
                    select(AgentTaskArtifactImmutabilityEvent)
                    .where(
                        AgentTaskArtifactImmutabilityEvent.artifact_id
                        == closure_artifact_id
                    )
                    .order_by(AgentTaskArtifactImmutabilityEvent.created_at.asc())
                )
            )
            assert [row.mutation_operation for row in mutation_events] == ["UPDATE"]

        with postgres_integration_harness.session_factory() as session:
            session.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
            session.execute(
                delete(AgentTaskArtifact).where(
                    AgentTaskArtifact.id == closure_artifact_id
                )
            )
            session.commit()

        with postgres_integration_harness.session_factory() as session:
            assert session.get(AgentTaskArtifact, closure_artifact_id) is not None
            mutation_events = list(
                session.scalars(
                    select(AgentTaskArtifactImmutabilityEvent)
                    .where(
                        AgentTaskArtifactImmutabilityEvent.artifact_id
                        == closure_artifact_id
                    )
                    .order_by(AgentTaskArtifactImmutabilityEvent.created_at.asc())
                )
            )
            assert [row.mutation_operation for row in mutation_events] == [
                "UPDATE",
                "DELETE",
            ]
    finally:
        _drop_claim_support_governance_immutability_trigger(
            postgres_integration_harness,
            schema_name,
        )

    with postgres_integration_harness.session_factory() as session:
        impact_row = session.get(ClaimSupportPolicyChangeImpact, change_impact_id)
        assert impact_row is not None
        closure = dict(impact_row.replay_closure_json)
        closure_basis = {
            **closure,
            "status": "closed",
        }
        closure_basis.pop("replay_closure_sha256", None)
        tampered_closure = {
            **closure_basis,
            "replay_closure_sha256": payload_sha256(closure_basis),
        }
        impact_row.replay_closure_json = tampered_closure
        impact_row.replay_closure_sha256 = tampered_closure["replay_closure_sha256"]
        session.commit()

    tampered_response = postgres_integration_harness.client.post(
        f"/agent-tasks/claim-support-policy-change-impacts/{change_impact_id}/replay-status",
    )
    assert tampered_response.status_code == 409
    assert (
        tampered_response.json()["error_code"]
        == "claim_support_impact_replay_terminal_status_mismatch"
    )


def test_replay_alert_waiver_ledger_derives_sparse_waiver_sources(
    postgres_integration_harness,
):
    with postgres_integration_harness.session_factory() as session:
        now = utcnow() - timedelta(hours=30)
        task = AgentTask(
            id=uuid4(),
            task_type="verify_claim_support_calibration_policy",
            status=AgentTaskStatus.COMPLETED.value,
            priority=100,
            side_effect_level="read_only",
            requires_approval=False,
            input_json={},
            result_json={},
            workflow_version="claim_support_policy_replay_alert_coverage",
            model_settings_json={},
            created_at=now,
            updated_at=now,
            completed_at=now,
        )
        session.add(task)
        change_impact_id = uuid4()
        impact_payload = {
            "schema_name": "claim_support_policy_change_impact",
            "schema_version": "1.0",
            "change_impact_id": str(change_impact_id),
        }
        session.add(
            ClaimSupportPolicyChangeImpact(
                id=change_impact_id,
                activation_task_id=task.id,
                activated_policy_id=None,
                previous_policy_id=None,
                semantic_governance_event_id=None,
                governance_artifact_id=None,
                impact_scope="claim_support_policy:unit",
                policy_name="claim_support_judge_calibration_policy",
                policy_version="v_sparse_waiver",
                activated_policy_sha256="policy-sha",
                previous_policy_sha256=None,
                affected_support_judgment_count=1,
                affected_generated_document_count=1,
                affected_verification_count=1,
                replay_recommended_count=1,
                replay_status="blocked",
                impacted_claim_derivation_ids_json=[],
                impacted_task_ids_json=[],
                impacted_verification_task_ids_json=[str(task.id)],
                impact_payload_json=impact_payload,
                impact_payload_sha256=payload_sha256(impact_payload),
                replay_task_ids_json=[],
                replay_task_plan_json={},
                replay_closure_json={},
                replay_status_updated_at=now,
                created_at=now,
            )
        )
        escalation_receipt = {
            "schema_name": "claim_support_policy_impact_replay_escalation_receipt",
            "schema_version": "1.0",
            "change_impact_id": str(change_impact_id),
            "alert_kind": "blocked",
            "replay_status": "blocked",
            "affected_verification_task_ids": [str(task.id)],
            "receipt_sha256": "escalation-receipt-sha",
        }
        escalation_event = SemanticGovernanceEvent(
            id=uuid4(),
            event_kind="claim_support_policy_impact_replay_escalated",
            governance_scope="claim_support_policy:unit",
            subject_table="claim_support_policy_change_impacts",
            subject_id=change_impact_id,
            task_id=task.id,
            agent_task_artifact_id=None,
            receipt_sha256=escalation_receipt["receipt_sha256"],
            payload_sha256=payload_sha256(escalation_receipt),
            event_hash="escalation-event-sha",
            deduplication_key=f"sparse-waiver-escalation:{change_impact_id}",
            event_payload_json={
                "claim_support_policy_impact_replay_escalation": escalation_receipt,
            },
            created_by="unit-test",
            created_at=now,
        )
        session.add(escalation_event)
        session.flush()
        waiver_basis = {
            "schema_name": "claim_support_replay_alert_fixture_coverage_waiver",
            "schema_version": "1.1",
            "verification_task_id": str(task.id),
            "target_task_id": str(task.id),
            "waived_by": "claim-support-operator@example.com",
            "waiver_reason": "Sparse payload still carries event IDs.",
            "waiver_severity": "high",
            "waiver_expires_at": (utcnow() + timedelta(hours=4)).isoformat(),
            "waiver_review_due_at": (utcnow() + timedelta(hours=2)).isoformat(),
            "waiver_status": "active",
            "waived_at": utcnow().isoformat(),
            "stale_unconverted_escalation_event_count": 1,
            "stale_unconverted_escalation_event_ids": [str(escalation_event.id)],
            "replay_alert_fixture_summary": {
                "has_more_unconverted_escalations": True,
                "stale_unconverted_escalation_event_count": 1,
            },
        }
        waiver_payload = {
            **waiver_basis,
            "waiver_sha256": payload_sha256(waiver_basis),
        }
        waiver_artifact = AgentTaskArtifact(
            task_id=task.id,
            artifact_kind="claim_support_replay_alert_fixture_coverage_waiver",
            storage_path=None,
            payload_json=waiver_payload,
            created_at=utcnow(),
        )
        session.add(waiver_artifact)
        session.flush()

        ledger = record_replay_alert_fixture_coverage_waiver_ledger(
            session,
            waiver_artifact=waiver_artifact,
            waiver_payload=waiver_payload,
        )

        assert ledger.source_change_impact_ids_json == [str(change_impact_id)]
        assert str(task.id) in ledger.source_verification_task_ids_json
        ledger_rows = list(
            session.scalars(
                select(ClaimSupportReplayAlertFixtureCoverageWaiverEscalation).where(
                    ClaimSupportReplayAlertFixtureCoverageWaiverEscalation.ledger_id
                    == ledger.id
                )
            )
        )
        assert len(ledger_rows) == 1
        assert ledger_rows[0].change_impact_id == change_impact_id
        assert ledger_rows[0].alert_kind == "blocked"
