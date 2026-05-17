from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import app.services.claim_support_replay_alert_fixture_corpus as replay_alert_corpus
import app.services.evidence_claim_support_replay_alert_corpus as corpus_owner
import app.services.evidence_claim_support_replay_alerts as replay_alerts


class _FakeSession:
    def __init__(self, *, rows=None, snapshots=None):
        self._rows = list(rows or [])
        self._snapshots = list(snapshots or [])

    def scalars(self, statement):
        sql = str(statement)
        if "claim_support_replay_alert_fixture_corpus_rows" in sql:
            return list(self._rows)
        if "claim_support_replay_alert_fixture_corpus_snapshots" in sql:
            return list(self._snapshots)
        return []


def _snapshot(**overrides):
    payload = {
        "id": uuid4(),
        "snapshot_name": "active_claim_support_replay_alert_fixtures",
        "status": "active",
        "snapshot_sha256": "snapshot-sha",
        "semantic_governance_event_id": uuid4(),
        "governance_artifact_id": uuid4(),
        "governance_receipt_sha256": "receipt-sha",
        "fixture_count": 1,
        "promotion_event_count": 1,
        "promotion_fixture_set_count": 1,
        "invalid_promotion_event_count": 0,
        "source_promotion_event_ids_json": [],
        "source_promotion_artifact_ids_json": ["artifact-1"],
        "source_promotion_receipt_sha256s_json": ["receipt-1"],
        "source_fixture_set_ids_json": ["fixture-set-1"],
        "source_fixture_set_sha256s_json": ["fixture-set-sha"],
        "source_escalation_event_ids_json": ["event-1"],
        "invalid_promotion_event_ids_json": [],
        "snapshot_payload_json": {"invalid_promotion_events": []},
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def _row(**overrides):
    payload = {
        "id": uuid4(),
        "snapshot_id": uuid4(),
        "row_index": 0,
        "case_id": "case-1",
        "case_identity_sha256": "case-sha",
        "fixture_sha256": "fixture-sha",
        "fixture_set_id": uuid4(),
        "promotion_event_id": uuid4(),
        "promotion_artifact_id": uuid4(),
        "promotion_receipt_sha256": "promotion-receipt-sha",
        "source_change_impact_ids_json": ["impact-1"],
        "source_escalation_event_ids_json": ["event-1"],
        "replay_alert_source_json": {"kind": "promotion"},
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_replay_alert_corpus_owner_uses_shared_governance_integrity() -> None:
    assert (
        corpus_owner.replay_alert_fixture_corpus_snapshot_governance_integrity
        is replay_alert_corpus.replay_alert_fixture_corpus_snapshot_governance_integrity
    )


def test_replay_alert_corpus_snapshot_payload_includes_rows_and_integrity(monkeypatch) -> None:
    snapshot = _snapshot()
    row = _row(snapshot_id=snapshot.id)
    session = _FakeSession(rows=[row])

    monkeypatch.setattr(
        corpus_owner,
        "replay_alert_fixture_corpus_snapshot_governance_integrity",
        lambda *_args, **_kwargs: {"complete": True, "failures": []},
    )

    payload = corpus_owner.replay_alert_fixture_corpus_snapshot_payload(session, snapshot)

    assert payload["snapshot_id"] == str(snapshot.id)
    assert payload["row_count"] == 1
    assert payload["rows"] == [corpus_owner.replay_alert_fixture_corpus_row_payload(row)]
    assert payload["governance_integrity"] == {"complete": True, "failures": []}
    assert payload["trace_complete"] is True


def test_replay_alert_corpus_snapshots_by_promotion_event_matches_declared_sources(
    monkeypatch,
) -> None:
    matching_event = SimpleNamespace(id=uuid4())
    other_event = SimpleNamespace(id=uuid4())
    snapshot = _snapshot(source_promotion_event_ids_json=[str(matching_event.id)])
    session = _FakeSession(snapshots=[snapshot])

    monkeypatch.setattr(
        corpus_owner,
        "replay_alert_fixture_corpus_snapshot_payload",
        lambda *_args, **_kwargs: {"snapshot_id": str(snapshot.id)},
    )

    payloads = corpus_owner.claim_support_replay_alert_fixture_corpus_snapshots_by_promotion_event(
        session,
        [matching_event, other_event],
    )

    assert payloads == {matching_event.id: [{"snapshot_id": str(snapshot.id)}]}


def test_evidence_claim_support_replay_alerts_facade_reexports_corpus_owner() -> None:
    assert (
        replay_alerts.replay_alert_fixture_corpus_snapshot_payload
        is corpus_owner.replay_alert_fixture_corpus_snapshot_payload
    )
    assert (
        replay_alerts.claim_support_replay_alert_fixture_corpus_snapshots_by_promotion_event
        is corpus_owner.claim_support_replay_alert_fixture_corpus_snapshots_by_promotion_event
    )


def test_evidence_claim_support_replay_alerts_facade_stays_within_budget() -> None:
    with open(replay_alerts.__file__, encoding="utf-8") as handle:
        line_count = sum(1 for _ in handle)

    assert line_count <= 600
