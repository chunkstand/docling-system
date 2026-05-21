from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.public.claim_support import (
    ClaimSupportReplayAlertFixtureCorpusRow,
    ClaimSupportReplayAlertFixtureCorpusSnapshot,
)
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.services.claim_support_replay_alert_fixture_corpus import (
    replay_alert_fixture_corpus_snapshot_governance_integrity,
)
from app.services.evidence_common import uuid_or_none_safe as _uuid_or_none_safe


def replay_alert_fixture_corpus_row_payload(
    row: ClaimSupportReplayAlertFixtureCorpusRow,
) -> dict[str, Any]:
    return {
        "row_id": str(row.id),
        "snapshot_id": str(row.snapshot_id),
        "row_index": row.row_index,
        "case_id": row.case_id,
        "case_identity_sha256": row.case_identity_sha256,
        "fixture_sha256": row.fixture_sha256,
        "fixture_set_id": str(row.fixture_set_id) if row.fixture_set_id else None,
        "promotion_event_id": (str(row.promotion_event_id) if row.promotion_event_id else None),
        "promotion_artifact_id": (
            str(row.promotion_artifact_id) if row.promotion_artifact_id else None
        ),
        "promotion_receipt_sha256": row.promotion_receipt_sha256,
        "source_change_impact_ids": list(row.source_change_impact_ids_json or []),
        "source_escalation_event_ids": list(row.source_escalation_event_ids_json or []),
        "replay_alert_source": dict(row.replay_alert_source_json or {}),
    }


def replay_alert_fixture_corpus_snapshot_payload(
    session: Session,
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot,
) -> dict[str, Any]:
    rows = list(
        session.scalars(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot.id)
            .order_by(
                ClaimSupportReplayAlertFixtureCorpusRow.row_index.asc(),
                ClaimSupportReplayAlertFixtureCorpusRow.id.asc(),
            )
        )
    )
    governance_integrity = replay_alert_fixture_corpus_snapshot_governance_integrity(
        session,
        snapshot,
    )
    return {
        "snapshot_id": str(snapshot.id),
        "snapshot_name": snapshot.snapshot_name,
        "status": snapshot.status,
        "snapshot_sha256": snapshot.snapshot_sha256,
        "semantic_governance_event_id": (
            str(snapshot.semantic_governance_event_id)
            if snapshot.semantic_governance_event_id
            else None
        ),
        "governance_artifact_id": (
            str(snapshot.governance_artifact_id) if snapshot.governance_artifact_id else None
        ),
        "governance_receipt_sha256": snapshot.governance_receipt_sha256,
        "fixture_count": snapshot.fixture_count,
        "promotion_event_count": snapshot.promotion_event_count,
        "promotion_fixture_set_count": snapshot.promotion_fixture_set_count,
        "invalid_promotion_event_count": snapshot.invalid_promotion_event_count,
        "source_promotion_event_ids": list(snapshot.source_promotion_event_ids_json or []),
        "source_promotion_artifact_ids": list(snapshot.source_promotion_artifact_ids_json or []),
        "source_promotion_receipt_sha256s": list(
            snapshot.source_promotion_receipt_sha256s_json or []
        ),
        "source_fixture_set_ids": list(snapshot.source_fixture_set_ids_json or []),
        "source_fixture_set_sha256s": list(snapshot.source_fixture_set_sha256s_json or []),
        "source_escalation_event_ids": list(snapshot.source_escalation_event_ids_json or []),
        "invalid_promotion_event_ids": list(snapshot.invalid_promotion_event_ids_json or []),
        "invalid_promotion_events": list(
            (snapshot.snapshot_payload_json or {}).get("invalid_promotion_events") or []
        ),
        "rows": [replay_alert_fixture_corpus_row_payload(row) for row in rows],
        "row_count": len(rows),
        "governance_integrity": governance_integrity,
        "trace_complete": bool(rows) and governance_integrity["complete"],
    }


def claim_support_replay_alert_fixture_corpus_snapshots_by_promotion_event(
    session: Session,
    events: list[SemanticGovernanceEvent],
) -> dict[UUID, list[dict[str, Any]]]:
    event_ids = {event.id for event in events}
    if not event_ids:
        return {}
    snapshots = list(
        session.scalars(
            select(ClaimSupportReplayAlertFixtureCorpusSnapshot).order_by(
                ClaimSupportReplayAlertFixtureCorpusSnapshot.created_at.asc(),
                ClaimSupportReplayAlertFixtureCorpusSnapshot.id.asc(),
            )
        )
    )
    by_event_id: dict[UUID, list[dict[str, Any]]] = {}
    for snapshot in snapshots:
        source_event_ids = {
            parsed
            for parsed in (
                _uuid_or_none_safe(value)
                for value in (snapshot.source_promotion_event_ids_json or [])
            )
            if parsed is not None
        }
        matching_event_ids = event_ids & source_event_ids
        if not matching_event_ids:
            continue
        payload = replay_alert_fixture_corpus_snapshot_payload(session, snapshot)
        for event_id in sorted(matching_event_ids, key=str):
            by_event_id.setdefault(event_id, []).append(payload)
    return by_event_id
