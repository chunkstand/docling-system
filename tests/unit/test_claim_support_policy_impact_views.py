from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.schemas.agent_tasks import (
    ClaimSupportPolicyChangeImpactAlertItemResponse,
    ClaimSupportPolicyChangeImpactAlertResponse,
    ClaimSupportPolicyChangeImpactResponse,
    ClaimSupportPolicyChangeImpactSummaryResponse,
    ClaimSupportPolicyChangeImpactWorklistItemResponse,
    ClaimSupportPolicyChangeImpactWorklistResponse,
    ClaimSupportPolicyChangeImpactWorklistTaskRef,
)
from app.services import claim_support_policy_impact_alerts as _impact_alerts

_NOW = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)


class _FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0
        self.flush_count = 0

    def commit(self) -> None:
        self.commit_count += 1

    def flush(self) -> None:
        self.flush_count += 1


def _impact_response(
    *,
    change_impact_id: UUID | None = None,
) -> ClaimSupportPolicyChangeImpactResponse:
    return ClaimSupportPolicyChangeImpactResponse(
        change_impact_id=change_impact_id or uuid4(),
        activation_task_id=uuid4(),
        impact_scope="claim_support_policy",
        policy_name="claim-support-default",
        policy_version="v2",
        activated_policy_sha256="policy-sha",
        affected_support_judgment_count=2,
        affected_generated_document_count=1,
        affected_verification_count=1,
        replay_recommended_count=1,
        replay_status="blocked",
        impact_payload_sha256="impact-payload-sha",
        created_at=_NOW,
    )


def _summary() -> ClaimSupportPolicyChangeImpactSummaryResponse:
    return ClaimSupportPolicyChangeImpactSummaryResponse(
        total_count=1,
        replay_status_counts={"blocked": 1},
        open_count=1,
        stale_open_count=0,
        stale_after_hours=24,
        stale_cutoff=_NOW,
    )


def _worklist_item(
    *,
    change_impact_id: UUID | None = None,
) -> ClaimSupportPolicyChangeImpactWorklistItemResponse:
    impact = _impact_response(change_impact_id=change_impact_id)
    verification_task_id = uuid4()
    return ClaimSupportPolicyChangeImpactWorklistItemResponse(
        change_impact=impact,
        severity="critical",
        status_label="blocked",
        is_open=True,
        is_stale=False,
        age_hours=3.5,
        status_age_hours=2.0,
        next_action="Inspect blocked replay tasks.",
        recommended_action="inspect_blockers",
        reasons=["Replay closure is blocked by failed tasks."],
        affected_verification_task_ids=[verification_task_id],
        audit_bundle_task_ids=[verification_task_id],
        replay_tasks=[
            ClaimSupportPolicyChangeImpactWorklistTaskRef(
                task_id=uuid4(),
                task_type="verify_technical_report",
                status="failed",
                is_terminal_failure=True,
                is_required_for_closure=True,
            )
        ],
        operator_links={
            "detail": (
                "/agent-tasks/claim-support-policy-change-impacts/"
                f"{impact.change_impact_id}"
            )
        },
    )


def _alert_item(
    *,
    change_impact_id: UUID | None = None,
) -> ClaimSupportPolicyChangeImpactAlertItemResponse:
    impact = _impact_response(change_impact_id=change_impact_id)
    verification_task_id = uuid4()
    return ClaimSupportPolicyChangeImpactAlertItemResponse(
        change_impact=impact,
        alert_kind="blocked",
        severity="critical",
        replay_status="blocked",
        is_stale=False,
        age_hours=2.5,
        status_age_hours=1.0,
        next_action="Inspect blocked replay tasks.",
        recommended_action="inspect_blockers",
        reasons=["Replay closure is blocked by failed tasks."],
        affected_verification_task_ids=[verification_task_id],
        audit_bundle_task_ids=[verification_task_id],
        replay_tasks=[
            ClaimSupportPolicyChangeImpactWorklistTaskRef(
                task_id=uuid4(),
                task_type="verify_technical_report",
                status="failed",
                is_terminal_failure=True,
                is_required_for_closure=True,
            )
        ],
        operator_links={"detail": "/agent-tasks/detail"},
    )


def test_claim_support_policy_change_impact_alerts_enriches_event_metadata(
    monkeypatch,
) -> None:
    item = _worklist_item()
    artifact_id = uuid4()
    event = SimpleNamespace(
        id=uuid4(),
        event_hash="event-hash",
        receipt_sha256="receipt-sha",
        agent_task_artifact_id=artifact_id,
        event_payload_json={
            "claim_support_policy_impact_replay_escalation": {"alert_kind": "blocked"}
        },
        created_at=_NOW,
    )
    artifact = SimpleNamespace(
        id=artifact_id,
        artifact_kind="claim_support_policy_impact_replay_escalation",
        storage_path="storage/impact-escalation.json",
    )

    monkeypatch.setattr(
        _impact_alerts,
        "_alert_row_ids",
        lambda *_args, **_kwargs: [item.change_impact.change_impact_id],
    )
    monkeypatch.setattr(
        _impact_alerts,
        "claim_support_policy_change_impact_worklist",
        lambda *_args, **_kwargs: ClaimSupportPolicyChangeImpactWorklistResponse(
            summary=_summary(),
            generated_at=_NOW,
            stale_after_hours=24,
            item_count=1,
            matching_count=1,
            items=[item],
        ),
    )
    monkeypatch.setattr(
        _impact_alerts,
        "_alert_events_by_row",
        lambda *_args, **_kwargs: {item.change_impact.change_impact_id: [event]},
    )
    monkeypatch.setattr(
        _impact_alerts,
        "_artifact_rows_by_id",
        lambda *_args, **_kwargs: {artifact_id: artifact},
    )

    response = _impact_alerts.claim_support_policy_change_impact_alerts(
        object(),
        stale_after_hours=24,
        limit=5,
    )

    assert response.matching_count == 1
    assert response.item_count == 1
    assert response.items[0].alert_kind == "blocked"
    assert response.items[0].escalation_events[0].artifact_kind == (
        "claim_support_policy_impact_replay_escalation"
    )
    assert response.items[0].operator_links["alerts"].endswith("/alerts")
    assert response.items[0].operator_links["record_escalations"].endswith(
        "/alerts/escalations"
    )


def test_record_alert_escalations_reports_created_count(monkeypatch) -> None:
    session = _FakeSession()
    change_impact_id = uuid4()
    initial_feed = ClaimSupportPolicyChangeImpactAlertResponse(
        summary=_summary(),
        generated_at=_NOW,
        stale_after_hours=24,
        item_count=1,
        matching_count=1,
        items=[_alert_item(change_impact_id=change_impact_id)],
    )
    recorded_feed = ClaimSupportPolicyChangeImpactAlertResponse(
        summary=_summary(),
        generated_at=_NOW,
        stale_after_hours=24,
        item_count=1,
        matching_count=1,
        items=[_alert_item(change_impact_id=change_impact_id)],
    )
    worklist_item = _worklist_item(change_impact_id=change_impact_id)
    feeds = iter([initial_feed, recorded_feed])

    monkeypatch.setattr(
        _impact_alerts,
        "claim_support_policy_change_impact_alerts",
        lambda *_args, **_kwargs: next(feeds),
    )
    monkeypatch.setattr(
        _impact_alerts,
        "get_impact_row",
        lambda *_args, **_kwargs: SimpleNamespace(id=change_impact_id),
    )
    monkeypatch.setattr(
        _impact_alerts,
        "_fresh_alert_worklist_item",
        lambda *_args, **_kwargs: (worklist_item, "blocked"),
    )
    monkeypatch.setattr(
        _impact_alerts,
        "_record_alert_escalation_event",
        lambda *_args, **_kwargs: (SimpleNamespace(id=uuid4()), True),
    )
    monkeypatch.setattr(
        _impact_alerts,
        "_refresh_existing_evidence_manifests_for_alert_item",
        lambda *_args, **_kwargs: None,
    )

    response = _impact_alerts.record_claim_support_policy_change_impact_alert_escalations(
        session,
        requested_by="unit-test",
    )

    assert session.commit_count == 1
    assert response.recorded_escalation_count == 1
    assert response.items[0].change_impact.change_impact_id == change_impact_id
