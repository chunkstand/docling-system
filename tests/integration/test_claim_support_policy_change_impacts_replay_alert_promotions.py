from __future__ import annotations

import os
from uuid import UUID

import pytest
from sqlalchemy import select

from app.db.models import (
    AgentTaskArtifact,
    ClaimSupportFixtureSet,
    ClaimSupportReplayAlertFixtureCorpusRow,
    ClaimSupportReplayAlertFixtureCorpusSnapshot,
    ClaimSupportReplayAlertFixtureCoverageWaiverEscalation,
    ClaimSupportReplayAlertFixtureCoverageWaiverLedger,
    SemanticGovernanceEvent,
)
from app.services.claim_support_evaluations import (
    default_claim_support_evaluation_fixtures,
)
from app.services.evidence import (
    get_agent_task_audit_bundle,
    get_agent_task_evidence_manifest,
    get_agent_task_evidence_trace,
)
from tests.integration.claim_support_policy_change_impacts_replay_alert_support import (
    _build_replay_alert_fixture_promotion_state,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_claim_support_change_impact_replay_alert_fixture_promotions_and_coverage(
    postgres_integration_harness,
):
    state = _build_replay_alert_fixture_promotion_state(postgres_integration_harness)
    impacted = state["impacted"]
    change_impact_id = state["change_impact_id"]
    fresh_change_impact_id = state["fresh_change_impact_id"]
    waiver = state["waiver"]
    first_promotion_payload = state["first_promotion_payload"]
    promotion_payload = state["promotion_payload"]
    duplicate_promotion_payload = state["duplicate_promotion_payload"]
    verify_payload = state["verify_payload"]
    first_promoted_fixture_set_id = None
    promoted_fixture_set_id = None

    assert first_promotion_payload["promoted_candidate_count"] == 1
    assert first_promotion_payload["fixture_count"] == (
        len(default_claim_support_evaluation_fixtures()) + 1
    )
    assert first_promotion_payload["promotion_event_id"]
    assert first_promotion_payload["promotion_receipt_sha256"]
    assert first_promotion_payload["created"] is True
    assert first_promotion_payload["waiver_closure_count"] == 0
    assert first_promotion_payload["candidate_matching_count"] == 1
    assert first_promotion_payload["candidate_item_count"] == 1
    assert first_promotion_payload["has_more_candidates"] is False
    assert first_promotion_payload["candidate_summary"]["candidate_count"] == 1
    assert (
        first_promotion_payload["candidate_summary"]["source_escalation_event_count"]
        == 1
    )
    assert first_promotion_payload["active_replay_fixture_corpus_snapshot_id"]
    assert first_promotion_payload["active_replay_fixture_corpus_governed"] is True

    assert promotion_payload["promoted_candidate_count"] == 1
    assert promotion_payload["skipped_candidate_count"] == 1
    assert promotion_payload["fixture_count"] == (
        len(default_claim_support_evaluation_fixtures()) + 1
    )
    assert promotion_payload["promotion_event_id"]
    assert promotion_payload["promotion_receipt_sha256"]
    assert promotion_payload["created"] is True
    assert promotion_payload["waiver_closure_count"] == 1
    assert promotion_payload["waiver_closure_event_ids"]
    assert promotion_payload["waiver_closure_artifact_ids"]
    assert promotion_payload["waiver_closure_receipt_sha256s"]
    assert promotion_payload["closed_waiver_artifact_ids"] == [waiver["artifact_id"]]
    assert promotion_payload["candidate_matching_count"] == 1
    assert promotion_payload["candidate_item_count"] == 1
    assert promotion_payload["has_more_candidates"] is False
    assert promotion_payload["candidate_summary"]["candidate_count"] == 2
    assert promotion_payload["candidate_summary"]["promoted_candidate_count"] == 1
    assert promotion_payload["candidate_summary"]["unpromoted_candidate_count"] == 1
    assert promotion_payload["candidate_summary"]["source_escalation_event_count"] == 2
    assert len(promotion_payload["source_change_impact_ids"]) == 1
    assert str(fresh_change_impact_id) not in promotion_payload["source_change_impact_ids"]
    assert len(promotion_payload["source_escalation_event_ids"]) == 1
    assert promotion_payload["active_replay_fixture_corpus_snapshot_id"]
    assert promotion_payload["active_replay_fixture_corpus_sha256"]
    assert promotion_payload["active_replay_fixture_corpus_fixture_count"] == 2
    assert promotion_payload["active_replay_fixture_corpus_governance_event_id"]
    assert promotion_payload["active_replay_fixture_corpus_governance_artifact_id"]
    assert promotion_payload["active_replay_fixture_corpus_governance_receipt_sha256"]
    assert promotion_payload["active_replay_fixture_corpus_governed"] is True
    assert all(row["already_promoted"] for row in promotion_payload["candidates"])
    assert duplicate_promotion_payload["promoted_candidate_count"] == 0

    promoted_candidate_response = postgres_integration_harness.client.get(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/fixture-candidates"
        "?limit=5&stale_after_hours=24"
    )
    assert promoted_candidate_response.status_code == 200
    promoted_candidate_payload = promoted_candidate_response.json()
    assert promoted_candidate_payload["summary"]["promoted_candidate_count"] == 2
    assert promoted_candidate_payload["summary"]["unpromoted_candidate_count"] == 0
    assert all(row["promotion_events"] for row in promoted_candidate_payload["items"])

    unpromoted_candidate_response = postgres_integration_harness.client.get(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/fixture-candidates"
        "?limit=5&stale_after_hours=24&include_promoted=false"
    )
    assert unpromoted_candidate_response.status_code == 200
    assert unpromoted_candidate_response.json()["matching_count"] == 0

    with postgres_integration_harness.session_factory() as session:
        first_fixture_set = session.get(
            ClaimSupportFixtureSet,
            UUID(first_promotion_payload["fixture_set_id"]),
        )
        assert first_fixture_set is not None
        first_promoted_fixture_set_id = first_fixture_set.id
        assert first_fixture_set.fixture_set_name == "integration_replay_alert_promotions"
        assert first_fixture_set.fixture_count == len(
            default_claim_support_evaluation_fixtures()
        ) + 1

        fixture_set = session.get(
            ClaimSupportFixtureSet,
            UUID(promotion_payload["fixture_set_id"]),
        )
        assert fixture_set is not None
        promoted_fixture_set_id = fixture_set.id
        assert fixture_set.fixture_set_name == "integration_replay_alert_promotions"
        assert fixture_set.fixture_count == len(
            default_claim_support_evaluation_fixtures()
        ) + 1
        assert fixture_set.metadata_json["source"] == (
            "claim_support_policy_change_impact_replay_alerts"
        )

        active_corpus_snapshot = session.scalar(
            select(ClaimSupportReplayAlertFixtureCorpusSnapshot)
            .where(ClaimSupportReplayAlertFixtureCorpusSnapshot.status == "active")
            .order_by(ClaimSupportReplayAlertFixtureCorpusSnapshot.created_at.desc())
            .limit(1)
        )
        assert active_corpus_snapshot is not None
        assert str(active_corpus_snapshot.id) == promotion_payload[
            "active_replay_fixture_corpus_snapshot_id"
        ]
        assert active_corpus_snapshot.fixture_count == 2
        assert active_corpus_snapshot.promotion_event_count == 2
        assert active_corpus_snapshot.semantic_governance_event_id is not None
        assert active_corpus_snapshot.governance_artifact_id is not None
        assert active_corpus_snapshot.governance_receipt_sha256
        assert set(active_corpus_snapshot.source_fixture_set_ids_json) == {
            str(first_fixture_set.id),
            str(fixture_set.id),
        }

        active_corpus_governance_event = session.get(
            SemanticGovernanceEvent,
            active_corpus_snapshot.semantic_governance_event_id,
        )
        assert active_corpus_governance_event is not None
        assert active_corpus_governance_event.event_kind == (
            "claim_support_replay_alert_fixture_corpus_snapshot_activated"
        )
        assert active_corpus_governance_event.subject_id == active_corpus_snapshot.id
        assert active_corpus_governance_event.receipt_sha256 == (
            active_corpus_snapshot.governance_receipt_sha256
        )
        active_corpus_governance_receipt = (
            active_corpus_governance_event.event_payload_json[
                "claim_support_replay_alert_fixture_corpus_snapshot"
            ]
        )
        assert active_corpus_governance_receipt["snapshot_id"] == str(
            active_corpus_snapshot.id
        )
        assert active_corpus_governance_receipt["snapshot_sha256"] == (
            active_corpus_snapshot.snapshot_sha256
        )
        assert set(active_corpus_governance_receipt["source_promotion_event_ids"]) == set(
            active_corpus_snapshot.source_promotion_event_ids_json
        )

        active_corpus_governance_artifact = session.get(
            AgentTaskArtifact,
            active_corpus_snapshot.governance_artifact_id,
        )
        assert active_corpus_governance_artifact is not None
        assert active_corpus_governance_artifact.artifact_kind == (
            "claim_support_replay_alert_fixture_corpus_snapshot"
        )
        assert active_corpus_governance_artifact.payload_json["receipt_sha256"] == (
            active_corpus_snapshot.governance_receipt_sha256
        )

        active_corpus_rows = list(
            session.scalars(
                select(ClaimSupportReplayAlertFixtureCorpusRow)
                .where(
                    ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id
                    == active_corpus_snapshot.id
                )
                .order_by(ClaimSupportReplayAlertFixtureCorpusRow.row_index.asc())
            )
        )
        assert len(active_corpus_rows) == 2
        assert {str(row.fixture_set_id) for row in active_corpus_rows} == {
            str(first_fixture_set.id),
            str(fixture_set.id),
        }
        assert {str(row.promotion_artifact_id) for row in active_corpus_rows} == {
            first_promotion_payload["artifact_id"],
            promotion_payload["artifact_id"],
        }

        promotion_event = session.get(
            SemanticGovernanceEvent,
            UUID(promotion_payload["promotion_event_id"]),
        )
        assert promotion_event is not None
        assert promotion_event.event_kind == (
            "claim_support_policy_impact_fixture_promoted"
        )
        assert promotion_event.subject_id == fixture_set.id
        assert promotion_event.receipt_sha256 == promotion_payload[
            "promotion_receipt_sha256"
        ]
        promotion_receipt = promotion_event.event_payload_json[
            "claim_support_policy_impact_fixture_promotion"
        ]
        assert promotion_receipt["fixture_set_id"] == str(fixture_set.id)
        assert promotion_receipt["candidate_count"] == 1
        assert set(promotion_receipt["source_escalation_event_ids"]) == set(
            promotion_payload["source_escalation_event_ids"]
        )
        assert {row["candidate_id"] for row in promotion_receipt["candidates"]} == {
            row["candidate_id"] for row in promotion_payload["candidates"]
        }
        assert all(
            row["candidate_identity_sha256"] == row["candidate_id"]
            for row in promotion_receipt["candidates"]
        )
        assert all(
            row["source_payload_sha256"] for row in promotion_receipt["candidates"]
        )

        waiver_closure_event = session.get(
            SemanticGovernanceEvent,
            UUID(promotion_payload["waiver_closure_event_ids"][0]),
        )
        assert waiver_closure_event is not None
        assert waiver_closure_event.event_kind == (
            "claim_support_replay_alert_fixture_coverage_waiver_closed"
        )
        waiver_closure_receipt = waiver_closure_event.event_payload_json[
            "claim_support_replay_alert_fixture_coverage_waiver_closure"
        ]
        assert waiver_closure_receipt["waiver_artifact_id"] == waiver["artifact_id"]
        assert waiver_closure_receipt["waiver_sha256"] == waiver["waiver_sha256"]
        assert waiver_closure_receipt["promotion_artifact_id"] == promotion_payload[
            "artifact_id"
        ]
        assert waiver_closure_receipt["promotion_receipt_sha256"] == (
            promotion_payload["promotion_receipt_sha256"]
        )
        combined_escalation_event_ids = {
            *first_promotion_payload["source_escalation_event_ids"],
            *promotion_payload["source_escalation_event_ids"],
        }
        assert set(waiver_closure_receipt["covered_escalation_event_ids"]) == set(
            combined_escalation_event_ids
        )
        assert set(waiver_closure_receipt["coverage_promotion_artifact_ids"]) == {
            first_promotion_payload["artifact_id"],
            promotion_payload["artifact_id"],
        }
        assert set(waiver_closure_receipt["coverage_promotion_receipt_sha256s"]) == {
            first_promotion_payload["promotion_receipt_sha256"],
            promotion_payload["promotion_receipt_sha256"],
        }

        waiver_closure_artifact = session.get(
            AgentTaskArtifact,
            UUID(promotion_payload["waiver_closure_artifact_ids"][0]),
        )
        assert waiver_closure_artifact is not None
        assert waiver_closure_artifact.artifact_kind == (
            "claim_support_replay_alert_fixture_coverage_waiver_closure"
        )
        assert waiver_closure_artifact.payload_json["receipt_sha256"] == (
            waiver_closure_event.receipt_sha256
        )

        waiver_ledger = session.get(
            ClaimSupportReplayAlertFixtureCoverageWaiverLedger,
            UUID(waiver["coverage_ledger_id"]),
        )
        assert waiver_ledger is not None
        assert waiver_ledger.coverage_complete is True
        assert waiver_ledger.coverage_status == "closed"
        assert waiver_ledger.covered_escalation_event_count == 2
        assert waiver_ledger.closure_event_id == waiver_closure_event.id
        assert waiver_ledger.closure_artifact_id == waiver_closure_artifact.id
        assert waiver_ledger.closure_receipt_sha256 == waiver_closure_event.receipt_sha256
        assert set(waiver_ledger.promotion_artifact_ids_json) == {
            first_promotion_payload["artifact_id"],
            promotion_payload["artifact_id"],
        }
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
        assert all(row.covered for row in waiver_ledger_rows)
        assert {
            str(row.covered_by_promotion_artifact_id) for row in waiver_ledger_rows
        } == {
            first_promotion_payload["artifact_id"],
            promotion_payload["artifact_id"],
        }

        audit_bundle = get_agent_task_audit_bundle(session, impacted["verify_task_id"])
        assert audit_bundle["audit_checklist"][
            "replay_alert_waiver_closure_integrity_verified"
        ] is True
        assert audit_bundle["audit_checklist"][
            "unresolved_replay_alert_fixture_coverage_waiver_count"
        ] == 0
        assert audit_bundle["audit_checklist"][
            "invalid_replay_alert_fixture_coverage_waiver_closure_count"
        ] == 0
        assert audit_bundle["audit_checklist"]["replay_alert_waiver_lifecycle_clear"] is True
        assert audit_bundle["audit_checklist"][
            "active_replay_alert_fixture_corpus_snapshot_id"
        ] == str(active_corpus_snapshot.id)
        assert audit_bundle["audit_checklist"][
            "active_replay_alert_fixture_corpus_sha256"
        ] == active_corpus_snapshot.snapshot_sha256
        assert audit_bundle["audit_checklist"][
            "replay_alert_fixture_corpus_snapshot_governed"
        ] is True
        assert audit_bundle["audit_checklist"][
            "replay_alert_fixture_corpus_trace_complete"
        ] is True
        matching_impacts = {
            row["change_impact_id"]: row
            for row in audit_bundle["change_impact"][
                "claim_support_policy_change_impacts"
            ]["impacts"]
        }
        assert matching_impacts[str(change_impact_id)][
            "fixture_promotion_governance_events"
        ]
        assert matching_impacts[str(change_impact_id)][
            "waiver_closure_governance_events"
        ][0]["waiver_sha256"] == waiver["waiver_sha256"]
        assert matching_impacts[str(change_impact_id)][
            "waiver_closure_governance_events"
        ][0]["integrity_verified"] is True
        assert audit_bundle["change_impact"]["claim_support_policy_change_impacts"][
            "waiver_lifecycle"
        ]["closed_waiver_count"] == 1

        manifest = get_agent_task_evidence_manifest(session, impacted["verify_task_id"])
        assert manifest["audit_checklist"][
            "replay_alert_waiver_closure_integrity_verified"
        ] is True
        assert manifest["audit_checklist"]["replay_alert_waiver_lifecycle_clear"] is True
        assert manifest["audit_checklist"][
            "active_replay_alert_fixture_corpus_snapshot_id"
        ] == str(active_corpus_snapshot.id)
        assert manifest["audit_checklist"][
            "active_replay_alert_fixture_corpus_sha256"
        ] == active_corpus_snapshot.snapshot_sha256
        assert manifest["audit_checklist"][
            "replay_alert_fixture_corpus_snapshot_governed"
        ] is True
        assert manifest["audit_checklist"][
            "replay_alert_fixture_corpus_trace_complete"
        ] is True
        manifest_impacts = {
            row["change_impact_id"]: row
            for row in manifest["change_impact"][
                "claim_support_policy_change_impacts"
            ]["impacts"]
        }
        assert manifest_impacts[str(change_impact_id)][
            "fixture_promotion_governance_events"
        ]
        assert manifest_impacts[str(change_impact_id)][
            "waiver_closure_governance_events"
        ][0]["promotion_artifact_id"] == promotion_payload["artifact_id"]
        assert manifest_impacts[str(change_impact_id)][
            "waiver_closure_governance_events"
        ][0]["integrity_failures"] == []

        trace = get_agent_task_evidence_trace(session, impacted["verify_task_id"])
        assert any(
            edge["edge_kind"] == "replay_fixture_promotion_event"
            for edge in trace["edges"]
        )
        assert any(
            edge["edge_kind"] == "replay_fixture_waiver_closure_event"
            for edge in trace["edges"]
        )
        assert any(
            edge["edge_kind"] == "verification_uses_replay_fixture_corpus_snapshot"
            for edge in trace["edges"]
        )
        assert any(
            edge["edge_kind"] == "replay_fixture_corpus_snapshot_governance_event"
            for edge in trace["edges"]
        )
        assert any(
            edge["edge_kind"] == "replay_fixture_corpus_row_promotion_event"
            for edge in trace["edges"]
        )

    replay_summary = verify_payload["replay_alert_fixture_summary"]
    assert verify_payload["verification"]["outcome"] == "passed"
    assert verify_payload["evaluation"]["summary"][
        "replay_alert_fixture_coverage_passed"
    ] is True
    assert replay_summary["included_replay_alert_fixture_count"] == 2
    assert replay_summary["stale_unconverted_escalation_event_count"] == 0
    assert replay_summary["fixture_source"] == (
        "active_replay_alert_fixture_corpus_snapshot"
    )
    assert replay_summary["active_replay_alert_fixture_corpus_snapshot"][
        "fixture_count"
    ] == 2
    assert replay_summary["active_replay_alert_fixture_corpus_governed"] is True
    assert replay_summary["active_replay_alert_fixture_corpus_governance_event_id"]
    assert replay_summary["active_replay_alert_fixture_corpus_governance_artifact_id"]
    assert set(
        replay_summary["active_replay_alert_fixture_corpus_snapshot"][
            "source_fixture_set_ids"
        ]
    ) == {
        str(first_promoted_fixture_set_id),
        str(promoted_fixture_set_id),
    }
    assert replay_summary["latest_promoted_fixture_set"]["fixture_set_id"] == str(
        promoted_fixture_set_id
    )
    assert verify_payload["mined_failure_summary"]["replay_alert_fixture_count"] == 2
    assert verify_payload["evaluation"]["summary"]["case_count"] == (
        len(default_claim_support_evaluation_fixtures()) + 2
    )
    assert set(
        verify_payload["evaluation"]["summary"]["required_hard_case_kinds"]
    ) == {
        "replay_alert_blocked_policy_change_impact",
        "replay_alert_stale_policy_change_impact",
    }

    converted_signal_response = postgres_integration_harness.client.get(
        "/agent-tasks/analytics/decision-signals"
    )
    assert converted_signal_response.status_code == 200
    converted_signals = converted_signal_response.json()
    assert not any(
        row["task_type"] == "claim_support_policy_change_impact_fixture_coverage"
        for row in converted_signals
    )
    assert not any(
        row["threshold_crossed"]
        in {
            "active_claim_support_replay_alert_fixture_coverage_waivers>0",
            "high_severity_active_claim_support_replay_alert_fixture_coverage_waivers>0",
            "expiring_claim_support_replay_alert_fixture_coverage_waivers>0",
            "waived_claim_support_replay_alert_escalations_promotable>0",
        }
        for row in converted_signals
    )
    assert any(
        row["threshold_crossed"]
        == "expired_claim_support_replay_alert_fixture_coverage_waivers>0"
        for row in converted_signals
    )
    assert any(
        row["task_type"]
        == "claim_support_replay_alert_fixture_coverage_waiver_closure"
        and row["threshold_crossed"]
        == "closed_claim_support_replay_alert_fixture_coverage_waivers>0"
        for row in converted_signals
    )
    assert any(
        row["task_type"] == "claim_support_replay_alert_fixture_corpus"
        and row["threshold_crossed"]
        == "active_claim_support_replay_alert_fixture_corpus_snapshot"
        for row in converted_signals
    )
