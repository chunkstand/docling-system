from __future__ import annotations

import os
from copy import deepcopy
from uuid import UUID

import pytest
from sqlalchemy import select

from app.db.public.agent_tasks import AgentTask
from app.db.public.claim_support import ClaimSupportReplayAlertFixtureCorpusRow
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.schemas.agent_tasks import AgentTaskCreateRequest
from app.services.agent_tasks import create_agent_task
from app.services.evidence import (
    get_agent_task_audit_bundle,
    get_agent_task_evidence_manifest,
    get_agent_task_evidence_trace,
    refresh_technical_report_evidence_manifest,
)
from tests.integration.claim_support_policy_change_impacts_replay_alert_support import (
    _build_replay_alert_fixture_promotion_state,
)
from tests.integration.claim_support_policy_integration_task_support import (
    _process_next_task,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_claim_support_change_impact_replay_alert_governance_failures_surface(
    postgres_integration_harness,
):
    state = _build_replay_alert_fixture_promotion_state(postgres_integration_harness)
    impacted = state["impacted"]
    change_impact_id = state["change_impact_id"]
    draft_task_id = state["draft_task_id"]
    promotion_payload = state["promotion_payload"]

    with postgres_integration_harness.session_factory() as session:
        active_corpus_row = session.scalar(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(
                ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id
                == UUID(promotion_payload["active_replay_fixture_corpus_snapshot_id"])
            )
            .order_by(ClaimSupportReplayAlertFixtureCorpusRow.row_index.asc())
            .limit(1)
        )
        assert active_corpus_row is not None
        original_fixture_sha256 = active_corpus_row.fixture_sha256
        active_corpus_row.fixture_sha256 = "tampered-corpus-row-fixture"
        session.commit()

    row_tamper_signal_response = postgres_integration_harness.client.get(
        "/agent-tasks/analytics/decision-signals"
    )
    assert row_tamper_signal_response.status_code == 200
    row_tamper_signals = row_tamper_signal_response.json()
    assert any(
        row["task_type"] == "claim_support_replay_alert_fixture_corpus"
        and row["threshold_crossed"]
        == "invalid_claim_support_replay_alert_fixture_corpus_snapshot_governance"
        for row in row_tamper_signals
    )

    with postgres_integration_harness.session_factory() as session:
        tampered_row_verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixture_set_name": "integration_replay_alert_row_tamper",
                    "fixture_set_version": "v1",
                    "include_replay_alert_fixtures": True,
                    "replay_alert_fixture_limit": 10,
                    "require_replay_alert_fixture_coverage": True,
                    "include_mined_failures": False,
                },
                workflow_version="claim_support_policy_replay_alert_coverage",
            ),
        )
        tampered_row_verify_task_id = tampered_row_verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        tampered_row_verify_row = session.get(AgentTask, tampered_row_verify_task_id)
        assert tampered_row_verify_row is not None
        tampered_row_payload = tampered_row_verify_row.result_json["payload"]
        tampered_row_summary = tampered_row_payload["replay_alert_fixture_summary"]
        assert tampered_row_payload["verification"]["outcome"] == "failed"
        assert tampered_row_payload["evaluation"]["summary"][
            "replay_alert_fixture_coverage_passed"
        ] is False
        assert tampered_row_summary["active_replay_alert_fixture_corpus_governed"] is False
        assert (
            "snapshot_db_row_payload_mismatch"
            in tampered_row_summary[
                "active_replay_alert_fixture_corpus_governance_failures"
            ]
        )
        assert (
            "snapshot_db_fixture_hash_mismatch"
            in tampered_row_summary[
                "active_replay_alert_fixture_corpus_governance_failures"
            ]
        )

    with postgres_integration_harness.session_factory() as session:
        active_corpus_row = session.scalar(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(
                ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id
                == UUID(promotion_payload["active_replay_fixture_corpus_snapshot_id"])
            )
            .order_by(ClaimSupportReplayAlertFixtureCorpusRow.row_index.asc())
            .limit(1)
        )
        assert active_corpus_row is not None
        active_corpus_row.fixture_sha256 = original_fixture_sha256
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        tampered_snapshot_governance_event = session.get(
            SemanticGovernanceEvent,
            UUID(promotion_payload["active_replay_fixture_corpus_governance_event_id"]),
        )
        assert tampered_snapshot_governance_event is not None
        tampered_snapshot_governance_payload = deepcopy(
            tampered_snapshot_governance_event.event_payload_json
        )
        tampered_snapshot_governance_payload[
            "claim_support_replay_alert_fixture_corpus_snapshot"
        ]["snapshot_sha256"] = "tampered-corpus-snapshot"
        tampered_snapshot_governance_event.event_payload_json = (
            tampered_snapshot_governance_payload
        )
        session.commit()

    invalid_governance_signal_response = postgres_integration_harness.client.get(
        "/agent-tasks/analytics/decision-signals"
    )
    assert invalid_governance_signal_response.status_code == 200
    invalid_governance_signals = invalid_governance_signal_response.json()
    assert any(
        row["task_type"] == "claim_support_replay_alert_fixture_corpus"
        and row["threshold_crossed"]
        == "invalid_claim_support_replay_alert_fixture_corpus_snapshot_governance"
        for row in invalid_governance_signals
    )

    with postgres_integration_harness.session_factory() as session:
        tampered_governance_audit_bundle = get_agent_task_audit_bundle(
            session,
            impacted["verify_task_id"],
        )
        assert tampered_governance_audit_bundle["audit_checklist"][
            "replay_alert_fixture_corpus_snapshot_governed"
        ] is False
        assert tampered_governance_audit_bundle["audit_checklist"][
            "replay_alert_fixture_corpus_trace_complete"
        ] is False
        assert tampered_governance_audit_bundle["audit_checklist"][
            "invalid_replay_alert_fixture_corpus_snapshot_governance_count"
        ] == 1
        assert tampered_governance_audit_bundle["change_impact"]["impacted"] is True
        assert any(
            impact["impact_type"]
            == "claim_support_replay_alert_fixture_corpus_snapshot_governance_invalid"
            for impact in tampered_governance_audit_bundle["change_impact"]["impacts"]
        )

        refresh_technical_report_evidence_manifest(
            session,
            task_id=impacted["verify_task_id"],
        )
        tampered_governance_manifest = get_agent_task_evidence_manifest(
            session,
            impacted["verify_task_id"],
        )
        assert tampered_governance_manifest["audit_checklist"][
            "replay_alert_fixture_corpus_snapshot_governed"
        ] is False
        tampered_governance_trace = get_agent_task_evidence_trace(
            session,
            impacted["verify_task_id"],
        )
        assert any(
            node["node_kind"]
            == "claim_support_replay_alert_fixture_corpus_snapshot"
            and (node["payload"].get("governance_integrity") or {}).get("complete")
            is False
            for node in tampered_governance_trace["nodes"]
        )

    with postgres_integration_harness.session_factory() as session:
        invalid_governance_verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixture_set_name": "integration_replay_alert_invalid_governance",
                    "fixture_set_version": "v1",
                    "include_replay_alert_fixtures": True,
                    "replay_alert_fixture_limit": 10,
                    "require_replay_alert_fixture_coverage": True,
                    "include_mined_failures": False,
                },
                workflow_version="claim_support_policy_replay_alert_coverage",
            ),
        )
        invalid_governance_verify_task_id = invalid_governance_verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        invalid_governance_verify_row = session.get(
            AgentTask,
            invalid_governance_verify_task_id,
        )
        assert invalid_governance_verify_row is not None
        invalid_governance_payload = invalid_governance_verify_row.result_json["payload"]
        invalid_governance_summary = invalid_governance_payload[
            "replay_alert_fixture_summary"
        ]
        assert invalid_governance_payload["verification"]["outcome"] == "failed"
        assert invalid_governance_payload["evaluation"]["summary"][
            "replay_alert_fixture_coverage_passed"
        ] is False
        assert invalid_governance_summary[
            "active_replay_alert_fixture_corpus_governed"
        ] is False
        assert (
            "snapshot_governance_event_payload_hash_mismatch"
            in invalid_governance_summary[
                "active_replay_alert_fixture_corpus_governance_failures"
            ]
        )

    with postgres_integration_harness.session_factory() as session:
        tampered_promotion_event = session.get(
            SemanticGovernanceEvent,
            UUID(promotion_payload["promotion_event_id"]),
        )
        assert tampered_promotion_event is not None
        tampered_promotion_payload = deepcopy(tampered_promotion_event.event_payload_json)
        tampered_promotion_payload[
            "claim_support_policy_impact_fixture_promotion"
        ]["receipt_sha256"] = "tampered-promotion-receipt"
        tampered_promotion_event.event_payload_json = tampered_promotion_payload
        session.commit()

    invalid_corpus_signal_response = postgres_integration_harness.client.get(
        "/agent-tasks/analytics/decision-signals"
    )
    assert invalid_corpus_signal_response.status_code == 200
    invalid_corpus_signals = invalid_corpus_signal_response.json()
    assert any(
        row["task_type"] == "claim_support_replay_alert_fixture_corpus"
        and row["threshold_crossed"]
        == "invalid_claim_support_replay_alert_fixture_corpus_promotions>0"
        for row in invalid_corpus_signals
    )
    assert any(
        row["task_type"] == "claim_support_policy_change_impact_fixture_coverage"
        and row["threshold_crossed"]
        == "stale_unconverted_claim_support_replay_escalations>0"
        for row in invalid_corpus_signals
    )

    with postgres_integration_harness.session_factory() as session:
        invalid_corpus_verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_claim_support_calibration_policy",
                input={
                    "target_task_id": str(draft_task_id),
                    "fixture_set_name": "integration_replay_alert_invalid_corpus",
                    "fixture_set_version": "v1",
                    "include_replay_alert_fixtures": True,
                    "replay_alert_fixture_limit": 10,
                    "require_replay_alert_fixture_coverage": True,
                    "include_mined_failures": False,
                },
                workflow_version="claim_support_policy_replay_alert_coverage",
            ),
        )
        invalid_corpus_verify_task_id = invalid_corpus_verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        invalid_corpus_verify_row = session.get(
            AgentTask,
            invalid_corpus_verify_task_id,
        )
        assert invalid_corpus_verify_row is not None
        invalid_corpus_payload = invalid_corpus_verify_row.result_json["payload"]
        invalid_corpus_summary = invalid_corpus_payload[
            "replay_alert_fixture_summary"
        ]
        assert invalid_corpus_payload["verification"]["outcome"] == "failed"
        assert invalid_corpus_payload["evaluation"]["summary"][
            "replay_alert_fixture_coverage_passed"
        ] is False
        assert invalid_corpus_payload["evaluation"]["summary"][
            "active_replay_alert_fixture_corpus_invalid_promotion_event_count"
        ] == 1
        assert invalid_corpus_summary[
            "active_replay_alert_fixture_corpus_invalid_promotion_event_count"
        ] == 1
        assert invalid_corpus_summary["included_replay_alert_fixture_count"] == 1
        assert invalid_corpus_summary["stale_unconverted_escalation_event_count"] == 1
        assert invalid_corpus_summary["active_replay_alert_fixture_corpus_snapshot"][
            "invalid_promotion_events"
        ][0]["failures"]

    with postgres_integration_harness.session_factory() as session:
        tampered_closure_event = session.get(
            SemanticGovernanceEvent,
            UUID(promotion_payload["waiver_closure_event_ids"][0]),
        )
        assert tampered_closure_event is not None
        tampered_event_payload = deepcopy(tampered_closure_event.event_payload_json)
        tampered_event_payload[
            "claim_support_replay_alert_fixture_coverage_waiver_closure"
        ]["promotion_receipt_sha256"] = "tampered-promotion-receipt"
        tampered_closure_event.event_payload_json = tampered_event_payload
        session.commit()

    tampered_signal_response = postgres_integration_harness.client.get(
        "/agent-tasks/analytics/decision-signals"
    )
    assert tampered_signal_response.status_code == 200
    tampered_signals = tampered_signal_response.json()
    assert any(
        row["threshold_crossed"]
        == "invalid_claim_support_replay_alert_fixture_coverage_waiver_closures>0"
        for row in tampered_signals
    )
    assert any(
        row["threshold_crossed"]
        == "active_claim_support_replay_alert_fixture_coverage_waivers>0"
        for row in tampered_signals
    )
    assert any(
        row["threshold_crossed"]
        == "high_severity_active_claim_support_replay_alert_fixture_coverage_waivers>0"
        for row in tampered_signals
    )
    assert any(
        row["threshold_crossed"]
        == "waived_claim_support_replay_alert_escalations_promotable>0"
        for row in tampered_signals
    )
    assert not any(
        row["threshold_crossed"]
        == "closed_claim_support_replay_alert_fixture_coverage_waivers>0"
        for row in tampered_signals
    )

    with postgres_integration_harness.session_factory() as session:
        tampered_audit_bundle = get_agent_task_audit_bundle(
            session,
            impacted["verify_task_id"],
        )
        tampered_impacts = {
            row["change_impact_id"]: row
            for row in tampered_audit_bundle["change_impact"][
                "claim_support_policy_change_impacts"
            ]["impacts"]
        }
        tampered_closure = tampered_impacts[str(change_impact_id)][
            "waiver_closure_governance_events"
        ][0]
        assert tampered_closure["integrity_verified"] is False
        assert "closure_receipt_hash_mismatch" in tampered_closure["integrity_failures"]
        assert tampered_audit_bundle["audit_checklist"][
            "replay_alert_waiver_closure_integrity_verified"
        ] is False
        assert tampered_audit_bundle["audit_checklist"][
            "invalid_replay_alert_fixture_coverage_waiver_closure_count"
        ] == 1
        assert tampered_audit_bundle["audit_checklist"][
            "replay_alert_waiver_lifecycle_clear"
        ] is False
        assert tampered_audit_bundle["audit_checklist"]["complete"] is False
        assert tampered_audit_bundle["change_impact"]["impacted"] is True
        assert any(
            impact["impact_type"]
            == "claim_support_replay_alert_fixture_coverage_waiver_closure_invalid"
            for impact in tampered_audit_bundle["change_impact"]["impacts"]
        )
