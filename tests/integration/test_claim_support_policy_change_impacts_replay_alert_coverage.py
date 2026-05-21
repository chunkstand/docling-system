from __future__ import annotations

import os
from uuid import UUID

import pytest
from sqlalchemy import select

from app.db.public.agent_tasks import AgentTaskArtifact
from app.db.public.claim_support import (
    ClaimSupportReplayAlertFixtureCoverageWaiverEscalation,
    ClaimSupportReplayAlertFixtureCoverageWaiverLedger,
)
from tests.integration.claim_support_policy_change_impacts_replay_alert_support import (
    _build_replay_alert_fixture_promotion_state,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_claim_support_change_impact_replay_alert_coverage_waiver_and_candidates(
    postgres_integration_harness,
):
    state = _build_replay_alert_fixture_promotion_state(postgres_integration_harness)
    change_impact_id = state["change_impact_id"]
    extra_change_impact_id = state["extra_change_impact_id"]
    fresh_change_impact_id = state["fresh_change_impact_id"]
    unconverted_gate_payload = state["unconverted_gate_payload"]
    waived_gate_payload = state["waived_gate_payload"]
    waiver = state["waiver"]

    assert unconverted_gate_payload["verification"]["outcome"] == "failed"
    assert unconverted_gate_payload["evaluation"]["summary"][
        "replay_alert_fixture_coverage_passed"
    ] is False

    assert waived_gate_payload["verification"]["outcome"] == "passed"
    assert waived_gate_payload["evaluation"]["summary"][
        "replay_alert_fixture_coverage_required"
    ] is False
    assert waived_gate_payload["evaluation"]["summary"][
        "replay_alert_fixture_coverage_waiver_sha256"
    ] == waiver["waiver_sha256"]
    assert waiver["waived_by"] == "claim-support-operator@example.com"
    assert waiver["artifact_kind"] == (
        "claim_support_replay_alert_fixture_coverage_waiver"
    )
    assert waiver["stale_unconverted_escalation_event_count"] == 2
    assert waiver["waiver_severity"] == "critical"
    assert waiver["waiver_review_due_at"]
    assert waiver["waiver_remediation_owner"] == (
        "claim-support-remediation@example.com"
    )

    with postgres_integration_harness.session_factory() as session:
        waiver_artifact = session.get(AgentTaskArtifact, UUID(waiver["artifact_id"]))
        assert waiver_artifact is not None
        assert waiver_artifact.artifact_kind == (
            "claim_support_replay_alert_fixture_coverage_waiver"
        )
        assert waiver_artifact.payload_json["waiver_sha256"] == waiver["waiver_sha256"]
        assert waiver_artifact.payload_json["schema_version"] == "1.1"
        assert waiver["coverage_ledger_id"]
        assert waiver["waived_escalation_event_count"] == 2
        assert waiver["waived_escalation_set_sha256"]
        assert waiver["stale_unconverted_escalation_set_sha256"] == waiver[
            "waived_escalation_set_sha256"
        ]
        assert len(waiver["stale_unconverted_escalation_event_ids"]) == 2
        assert len(waiver["stale_unconverted_escalation_events"]) == 2
        assert waiver["replay_alert_fixture_summary"][
            "has_more_unconverted_escalations"
        ] is True
        assert len(
            waiver["replay_alert_fixture_summary"]["unconverted_escalation_events"]
        ) == 1
        waiver_ledger = session.get(
            ClaimSupportReplayAlertFixtureCoverageWaiverLedger,
            UUID(waiver["coverage_ledger_id"]),
        )
        assert waiver_ledger is not None
        assert str(waiver_ledger.waiver_artifact_id) == waiver["artifact_id"]
        assert waiver_ledger.waived_escalation_event_count == 2
        assert waiver_ledger.waived_escalation_set_sha256 == waiver[
            "waived_escalation_set_sha256"
        ]
        waiver_ledger_rows = list(
            session.scalars(
                select(ClaimSupportReplayAlertFixtureCoverageWaiverEscalation)
                .where(
                    ClaimSupportReplayAlertFixtureCoverageWaiverEscalation.ledger_id
                    == waiver_ledger.id
                )
                .order_by(
                    ClaimSupportReplayAlertFixtureCoverageWaiverEscalation.created_at.asc()
                )
            )
        )
        assert len(waiver_ledger_rows) == 2
        assert {str(row.escalation_event_id) for row in waiver_ledger_rows} == set(
            waiver["stale_unconverted_escalation_event_ids"]
        )
        assert any(
            metric["metric_key"] == "claim_support_replay_alert_fixture_coverage"
            and metric["passed"] is True
            and metric["details"]["waiver"]["waiver_sha256"] == waiver["waiver_sha256"]
            for metric in waived_gate_payload["evaluation"]["success_metrics"]
        )

    waiver_signal_response = postgres_integration_harness.client.get(
        "/agent-tasks/analytics/decision-signals"
    )
    assert waiver_signal_response.status_code == 200
    assert any(
        row["task_type"] == "claim_support_replay_alert_fixture_coverage_waiver"
        and row["threshold_crossed"]
        == "expired_claim_support_replay_alert_fixture_coverage_waivers>0"
        for row in waiver_signal_response.json()
    )

    fixture_candidate_response = postgres_integration_harness.client.get(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/fixture-candidates"
        "?limit=5&stale_after_hours=24"
    )
    assert fixture_candidate_response.status_code == 200
    fixture_candidate_payload = fixture_candidate_response.json()
    assert fixture_candidate_payload["summary"]["candidate_count"] == 2
    assert fixture_candidate_payload["summary"]["source_escalation_event_count"] == 2
    assert fixture_candidate_payload["matching_count"] == 2
    candidate_change_impact_ids = {
        row["change_impact_id"] for row in fixture_candidate_payload["items"]
    }
    assert candidate_change_impact_ids == {
        str(change_impact_id),
        str(extra_change_impact_id),
    }
    assert str(fresh_change_impact_id) not in candidate_change_impact_ids
    assert all(row["escalation_event_ids"] for row in fixture_candidate_payload["items"])
    assert all(row["already_promoted"] for row in fixture_candidate_payload["items"])
    assert all(
        row["candidate_id"]
        == row["fixture"]["replay_alert_source"]["candidate_identity_sha256"]
        for row in fixture_candidate_payload["items"]
    )
    assert all(
        row["fixture"]["replay_alert_source"]["draft_source"]
        == "reconstructed_claim_derivation"
        for row in fixture_candidate_payload["items"]
    )
