from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.db.models import AgentTaskArtifact, SemanticGovernanceEvent
from app.services.agent_tasks import _valid_replay_alert_fixture_coverage_waiver_closure_event
from app.services.evidence import _waiver_closure_event_integrity, payload_sha256

WAIVER_ARTIFACT_KIND = "claim_support_replay_alert_fixture_coverage_waiver"
WAIVER_CLOSURE_ARTIFACT_KIND = "claim_support_replay_alert_fixture_coverage_waiver_closure"
PROMOTION_ARTIFACT_KIND = "claim_support_policy_impact_fixture_promotion"
PROMOTION_EVENT_KIND = "claim_support_policy_impact_fixture_promoted"
WAIVER_CLOSED_EVENT_KIND = "claim_support_replay_alert_fixture_coverage_waiver_closed"


class FakeSession:
    def __init__(
        self,
        *,
        artifacts: dict[UUID, AgentTaskArtifact],
        events: dict[UUID, SemanticGovernanceEvent],
    ) -> None:
        self.artifacts = artifacts
        self.events = events

    def get(self, model, row_id):
        row_uuid = UUID(str(row_id))
        if model is AgentTaskArtifact:
            return self.artifacts.get(row_uuid)
        if model is SemanticGovernanceEvent:
            return self.events.get(row_uuid)
        return None


def _artifact(
    *,
    artifact_id: UUID,
    artifact_kind: str,
    payload: dict,
) -> AgentTaskArtifact:
    return AgentTaskArtifact(
        id=artifact_id,
        task_id=uuid4(),
        artifact_kind=artifact_kind,
        storage_path=None,
        payload_json=payload,
        created_at=datetime(2026, 4, 28, tzinfo=UTC),
    )


def _event(
    *,
    event_id: UUID,
    event_kind: str,
    artifact_id: UUID | None,
    receipt_sha256: str,
    payload: dict | None = None,
) -> SemanticGovernanceEvent:
    return SemanticGovernanceEvent(
        id=event_id,
        event_kind=event_kind,
        governance_scope="claim_support_policy:test",
        subject_table="agent_task_artifacts",
        subject_id=artifact_id,
        task_id=uuid4(),
        agent_task_artifact_id=artifact_id,
        receipt_sha256=receipt_sha256,
        payload_sha256="payload-sha",
        event_hash="event-sha",
        deduplication_key=f"event:{event_id}",
        event_payload_json=payload or {},
        created_by="unit-test",
        created_at=datetime(2026, 4, 28, tzinfo=UTC),
    )


def _closure_payload(
    *,
    waiver_artifact_id: UUID,
    waiver_sha256: str,
    promotion_event_id: UUID,
    promotion_artifact_id: UUID,
    promotion_receipt_sha256: str,
    escalation_event_id: UUID,
    coverage_promotion_event_ids: list[UUID],
) -> dict:
    basis = {
        "schema_name": "claim_support_replay_alert_fixture_coverage_waiver_closure_receipt",
        "schema_version": "1.0",
        "closure_status": "closed_by_fixture_promotion",
        "closed_by": "unit-test",
        "closed_at": datetime(2026, 4, 28, tzinfo=UTC).isoformat(),
        "waiver_artifact_id": str(waiver_artifact_id),
        "waiver_task_id": str(uuid4()),
        "waiver_sha256": waiver_sha256,
        "waiver_severity": "high",
        "waiver_expires_at": datetime(2026, 4, 29, tzinfo=UTC).isoformat(),
        "waiver_stale_unconverted_escalation_event_count": 1,
        "waived_escalation_event_ids": [str(escalation_event_id)],
        "covered_escalation_event_ids": [str(escalation_event_id)],
        "coverage_promotion_event_ids": [
            str(event_id) for event_id in coverage_promotion_event_ids
        ],
        "coverage_promotion_artifact_ids": [str(promotion_artifact_id)],
        "coverage_promotion_receipt_sha256s": [promotion_receipt_sha256],
        "source_change_impact_ids": [str(uuid4())],
        "source_escalation_event_ids": [str(escalation_event_id)],
        "fixture_set_id": str(uuid4()),
        "fixture_set_name": "unit_fixture_set",
        "fixture_set_version": "v1",
        "fixture_set_sha256": "fixture-set-sha",
        "promotion_event_id": str(promotion_event_id),
        "promotion_receipt_sha256": promotion_receipt_sha256,
        "promotion_artifact_id": str(promotion_artifact_id),
        "promotion_artifact_kind": PROMOTION_ARTIFACT_KIND,
        "promotion_artifact_path": None,
        "promotion_payload_sha256": "promotion-payload-sha",
        "closure_reason": "unit test closure",
        "semantic_basis": {},
        "deduplication_key": f"waiver-closed:{waiver_artifact_id}",
    }
    return {**basis, "receipt_sha256": payload_sha256(basis)}


def _session_for_closure(
    *,
    coverage_promotion_event_ids: list[UUID] | None = None,
) -> tuple[FakeSession, SemanticGovernanceEvent, dict, UUID, str]:
    waiver_artifact_id = uuid4()
    closure_artifact_id = uuid4()
    promotion_artifact_id = uuid4()
    promotion_event_id = uuid4()
    escalation_event_id = uuid4()
    waiver_sha256 = "waiver-sha"
    promotion_receipt_sha256 = "promotion-receipt-sha"
    closure_payload = _closure_payload(
        waiver_artifact_id=waiver_artifact_id,
        waiver_sha256=waiver_sha256,
        promotion_event_id=promotion_event_id,
        promotion_artifact_id=promotion_artifact_id,
        promotion_receipt_sha256=promotion_receipt_sha256,
        escalation_event_id=escalation_event_id,
        coverage_promotion_event_ids=coverage_promotion_event_ids
        if coverage_promotion_event_ids is not None
        else [promotion_event_id],
    )
    closure_event = _event(
        event_id=uuid4(),
        event_kind=WAIVER_CLOSED_EVENT_KIND,
        artifact_id=closure_artifact_id,
        receipt_sha256=closure_payload["receipt_sha256"],
        payload={
            "claim_support_replay_alert_fixture_coverage_waiver_closure": closure_payload
        },
    )
    promotion_event = _event(
        event_id=promotion_event_id,
        event_kind=PROMOTION_EVENT_KIND,
        artifact_id=promotion_artifact_id,
        receipt_sha256=promotion_receipt_sha256,
    )
    session = FakeSession(
        artifacts={
            closure_artifact_id: _artifact(
                artifact_id=closure_artifact_id,
                artifact_kind=WAIVER_CLOSURE_ARTIFACT_KIND,
                payload=closure_payload,
            ),
            waiver_artifact_id: _artifact(
                artifact_id=waiver_artifact_id,
                artifact_kind=WAIVER_ARTIFACT_KIND,
                payload={"waiver_sha256": waiver_sha256},
            ),
            promotion_artifact_id: _artifact(
                artifact_id=promotion_artifact_id,
                artifact_kind=PROMOTION_ARTIFACT_KIND,
                payload={
                    "receipt_sha256": promotion_receipt_sha256,
                    "source_escalation_event_ids": [str(escalation_event_id)],
                },
            ),
        },
        events={
            promotion_event_id: promotion_event,
            closure_event.id: closure_event,
        },
    )
    return session, closure_event, closure_payload, waiver_artifact_id, waiver_sha256


def test_waiver_closure_integrity_accepts_declared_promotion_event_chain() -> None:
    session, closure_event, closure_payload, waiver_artifact_id, waiver_sha256 = (
        _session_for_closure()
    )

    integrity_verified, failures = _waiver_closure_event_integrity(
        session,
        closure_event,
        closure_payload,
    )

    assert integrity_verified is True
    assert failures == []
    assert _valid_replay_alert_fixture_coverage_waiver_closure_event(
        session,
        closure_event,
    ) == (waiver_artifact_id, waiver_sha256)


def test_waiver_closure_integrity_rejects_hash_valid_missing_promotion_event() -> None:
    missing_event_id = uuid4()
    session, closure_event, closure_payload, _waiver_artifact_id, _waiver_sha256 = (
        _session_for_closure(coverage_promotion_event_ids=[missing_event_id])
    )

    integrity_verified, failures = _waiver_closure_event_integrity(
        session,
        closure_event,
        closure_payload,
    )

    assert integrity_verified is False
    assert "coverage_promotion_event_missing" in failures
    assert _valid_replay_alert_fixture_coverage_waiver_closure_event(
        session,
        closure_event,
    ) is None
