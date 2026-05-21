from __future__ import annotations

import os
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTask, AgentTaskArtifact
from app.db.public.claim_support import ClaimSupportPolicyChangeImpact
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.schemas.agent_tasks import AgentTaskCreateRequest
from app.services.agent_tasks import create_agent_task
from app.services.evidence import (
    get_agent_task_audit_bundle,
    get_agent_task_evidence_manifest,
)
from tests.integration.claim_support_policy_change_impacts_replay_alert_support import (
    _seed_replay_alert_change_impact_state,
)
from tests.integration.claim_support_policy_integration_task_support import (
    _process_next_task,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_claim_support_change_impact_replay_alert_prevalidation_and_escalation(
    postgres_integration_harness,
):
    state = _seed_replay_alert_change_impact_state(postgres_integration_harness)
    impacted = state["impacted"]
    change_impact_id = state["change_impact_id"]
    extra_change_impact_id = state["extra_change_impact_id"]
    fresh_change_impact_id = state["fresh_change_impact_id"]
    activation_task_id = state["activation_task_id"]

    response = postgres_integration_harness.client.post(
        (
            "/agent-tasks/claim-support-policy-change-impacts/"
            f"{change_impact_id}/replay-tasks"
        ),
        json={"requested_by": "claim-support-operator@example.com"},
    )
    assert response.status_code == 409
    assert (
        response.json()["error_code"]
        == "claim_support_impact_replay_source_task_not_found"
    )

    with postgres_integration_harness.session_factory() as session:
        impact_row = session.get(ClaimSupportPolicyChangeImpact, change_impact_id)
        assert impact_row is not None
        assert impact_row.replay_status == "pending"
        assert impact_row.replay_task_ids_json == []
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
        assert replay_rows == []

    worklist_response = postgres_integration_harness.client.get(
        "/agent-tasks/claim-support-policy-change-impacts/worklist"
        "?limit=1&stale_after_hours=24"
    )
    assert worklist_response.status_code == 200
    worklist_payload = worklist_response.json()
    assert worklist_payload["limit"] == 1
    assert worklist_payload["matching_count"] == 3
    assert worklist_payload["item_count"] == 1
    assert worklist_payload["has_more"] is True

    full_worklist_response = postgres_integration_harness.client.get(
        "/agent-tasks/claim-support-policy-change-impacts/worklist"
        "?limit=5&stale_after_hours=24"
    )
    assert full_worklist_response.status_code == 200
    worklist_item = next(
        row
        for row in full_worklist_response.json()["items"]
        if row["change_impact"]["change_impact_id"] == str(change_impact_id)
    )
    assert worklist_item["is_stale"] is True
    assert worklist_item["severity"] == "warning"
    assert worklist_item["recommended_action"] == "queue_replay"

    alert_response = postgres_integration_harness.client.get(
        "/agent-tasks/claim-support-policy-change-impacts/alerts"
        "?limit=1&stale_after_hours=24"
    )
    assert alert_response.status_code == 200
    alert_payload = alert_response.json()
    assert alert_payload["matching_count"] == 2
    assert alert_payload["item_count"] == 1
    assert alert_payload["has_more"] is True
    assert alert_payload["items"][0]["alert_kind"] == "blocked"
    assert alert_payload["items"][0]["severity"] == "critical"

    with postgres_integration_harness.session_factory() as session:
        pre_escalation_manifest = get_agent_task_evidence_manifest(
            session,
            impacted["verify_task_id"],
        )
        pre_escalation_manifest_id = pre_escalation_manifest["evidence_manifest_id"]
        pre_escalation_impacts = pre_escalation_manifest["change_impact"][
            "claim_support_policy_change_impacts"
        ]["impacts"]
        assert not any(
            row["escalation_governance_events"] for row in pre_escalation_impacts
        )
        session.commit()

    escalation_response = postgres_integration_harness.client.post(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/escalations"
        "?limit=5&stale_after_hours=24",
        json={"requested_by": "claim-support-operator@example.com"},
    )
    assert escalation_response.status_code == 200
    escalation_payload = escalation_response.json()
    assert escalation_payload["recorded_escalation_count"] == 2
    assert escalation_payload["matching_count"] == 2
    assert all(row["escalation_events"] for row in escalation_payload["items"])

    duplicate_escalation_response = postgres_integration_harness.client.post(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/escalations"
        "?limit=5&stale_after_hours=24",
        json={"requested_by": "claim-support-operator@example.com"},
    )
    assert duplicate_escalation_response.status_code == 200
    assert duplicate_escalation_response.json()["recorded_escalation_count"] == 0

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
        assert len(escalation_events) == 2
        assert {event.created_by for event in escalation_events} == {
            "claim-support-operator@example.com"
        }
        stale_escalation_created_at = utcnow() - timedelta(hours=25)
        for event in escalation_events:
            event.created_at = stale_escalation_created_at
        escalation_artifacts = list(
            session.scalars(
                select(AgentTaskArtifact).where(
                    AgentTaskArtifact.artifact_kind
                    == "claim_support_policy_impact_replay_escalation"
                )
            )
        )
        assert len(escalation_artifacts) == 2
        assert {artifact.task_id for artifact in escalation_artifacts} == {
            activation_task_id
        }
        assert all(
            artifact.payload_json["receipt_sha256"]
            for artifact in escalation_artifacts
        )

        audit_bundle = get_agent_task_audit_bundle(session, impacted["verify_task_id"])
        policy_impacts = audit_bundle["change_impact"][
            "claim_support_policy_change_impacts"
        ]
        matching_impacts = {
            row["change_impact_id"]: row for row in policy_impacts["impacts"]
        }
        assert matching_impacts[str(change_impact_id)]["escalation_governance_events"]
        assert matching_impacts[str(extra_change_impact_id)][
            "escalation_governance_events"
        ]
        assert not matching_impacts[str(fresh_change_impact_id)][
            "escalation_governance_events"
        ]

        manifest = get_agent_task_evidence_manifest(session, impacted["verify_task_id"])
        assert manifest["evidence_manifest_id"] == pre_escalation_manifest_id
        manifest_impacts = manifest["change_impact"][
            "claim_support_policy_change_impacts"
        ]["impacts"]
        assert any(row["escalation_governance_events"] for row in manifest_impacts)
        session.commit()

    coverage_signal_response = postgres_integration_harness.client.get(
        "/agent-tasks/analytics/decision-signals"
    )
    assert coverage_signal_response.status_code == 200
    assert any(
        row["task_type"] == "claim_support_policy_change_impact_fixture_coverage"
        and row["threshold_crossed"]
        == "stale_unconverted_claim_support_replay_escalations>0"
        for row in coverage_signal_response.json()
    )

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
        assert unconverted_gate_payload["verification"]["outcome"] == "failed"
        assert unconverted_gate_payload["evaluation"]["summary"][
            "replay_alert_fixture_coverage_passed"
        ] is False
        assert unconverted_gate_payload["replay_alert_fixture_summary"][
            "included_replay_alert_fixture_count"
        ] == 0
        assert unconverted_gate_payload["replay_alert_fixture_summary"][
            "stale_unconverted_escalation_event_count"
        ] == 2
        assert any(
            metric["metric_key"] == "claim_support_replay_alert_fixture_coverage"
            and metric["passed"] is False
            for metric in unconverted_gate_payload["evaluation"]["success_metrics"]
        )

    missing_waiver_response = postgres_integration_harness.client.post(
        "/agent-tasks",
        json={
            "task_type": "verify_claim_support_calibration_policy",
            "input": {
                "target_task_id": str(unconverted_gate_draft_task_id),
                "fixture_set_name": "integration_replay_alert_missing_waiver",
                "fixture_set_version": "v1",
                "require_replay_alert_fixture_coverage": False,
            },
            "workflow_version": "claim_support_policy_replay_alert_coverage",
        },
    )
    assert missing_waiver_response.status_code == 422
    assert missing_waiver_response.json()["error_code"] == "invalid_agent_task_input"

    missing_lifecycle_response = postgres_integration_harness.client.post(
        "/agent-tasks",
        json={
            "task_type": "verify_claim_support_calibration_policy",
            "input": {
                "target_task_id": str(unconverted_gate_draft_task_id),
                "fixture_set_name": "integration_replay_alert_missing_lifecycle",
                "fixture_set_version": "v1",
                "require_replay_alert_fixture_coverage": False,
                "replay_alert_fixture_coverage_waived_by": (
                    "claim-support-operator@example.com"
                ),
                "replay_alert_fixture_coverage_waiver_reason": (
                    "Exercise waiver lifecycle validation."
                ),
            },
            "workflow_version": "claim_support_policy_replay_alert_coverage",
        },
    )
    assert missing_lifecycle_response.status_code == 422
    assert missing_lifecycle_response.json()["error_code"] == "invalid_agent_task_input"

    excessive_ttl_response = postgres_integration_harness.client.post(
        "/agent-tasks",
        json={
            "task_type": "verify_claim_support_calibration_policy",
            "input": {
                "target_task_id": str(unconverted_gate_draft_task_id),
                "fixture_set_name": "integration_replay_alert_excessive_ttl",
                "fixture_set_version": "v1",
                "require_replay_alert_fixture_coverage": False,
                "replay_alert_fixture_coverage_waived_by": (
                    "claim-support-operator@example.com"
                ),
                "replay_alert_fixture_coverage_waiver_reason": (
                    "Exercise waiver maximum lifecycle validation."
                ),
                "replay_alert_fixture_coverage_waiver_severity": "medium",
                "replay_alert_fixture_coverage_waiver_expires_at": (
                    utcnow() + timedelta(hours=73)
                ).isoformat(),
            },
            "workflow_version": "claim_support_policy_replay_alert_coverage",
        },
    )
    assert excessive_ttl_response.status_code == 422
    assert excessive_ttl_response.json()["error_code"] == "invalid_agent_task_input"
