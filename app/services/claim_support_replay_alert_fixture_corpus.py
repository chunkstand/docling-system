from __future__ import annotations

from importlib import import_module
from typing import Any

from app.core.coercion import maybe_uuid as _uuid_or_none

ACTIVE_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_NAME = (
    "active_claim_support_replay_alert_fixtures"
)
CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND = (
    "claim_support_policy_impact_fixture_promotion"
)
CLAIM_SUPPORT_IMPACT_FIXTURE_PROMOTION_EVENT_KIND = (
    "claim_support_policy_impact_fixture_promoted"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_ARTIFACT_KIND = (
    "claim_support_replay_alert_fixture_corpus_snapshot"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_KIND = (
    "claim_support_replay_alert_fixture_corpus_snapshot_activated"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_RECEIPT_SCHEMA = (
    "claim_support_replay_alert_fixture_corpus_snapshot_receipt"
)
CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_PAYLOAD_KEY = (
    "claim_support_replay_alert_fixture_corpus_snapshot"
)


def build_replay_alert_fixture_corpus(session):
    return import_module(
        "app.services.claim_support_replay_alert_fixture_corpus_build"
    ).build_replay_alert_fixture_corpus(session)


def record_replay_alert_fixture_corpus_snapshot_governance(
    session,
    *,
    snapshot,
    storage_service=None,
    recorded_by: str = "docling-system",
):
    return import_module(
        "app.services.claim_support_replay_alert_fixture_corpus_governance"
    ).record_replay_alert_fixture_corpus_snapshot_governance(
        session,
        snapshot=snapshot,
        storage_service=storage_service,
        recorded_by=recorded_by,
    )


def replay_alert_fixture_corpus_snapshot_governance_integrity(
    session,
    snapshot,
):
    return import_module(
        "app.services.claim_support_replay_alert_fixture_corpus_governance"
    ).replay_alert_fixture_corpus_snapshot_governance_integrity(
        session,
        snapshot,
    )


def ensure_active_replay_alert_fixture_corpus_snapshot(
    session,
    *,
    storage_service=None,
    recorded_by: str = "docling-system",
):
    return import_module(
        "app.services.claim_support_replay_alert_fixture_corpus_governance"
    ).ensure_active_replay_alert_fixture_corpus_snapshot(
        session,
        storage_service=storage_service,
        recorded_by=recorded_by,
    )


def replay_alert_fixture_corpus_snapshot_summary(
    snapshot,
    *,
    session=None,
):
    if snapshot is None:
        return None
    summary = {
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
            str(snapshot.governance_artifact_id)
            if snapshot.governance_artifact_id
            else None
        ),
        "governance_receipt_sha256": snapshot.governance_receipt_sha256,
        "fixture_count": snapshot.fixture_count,
        "promotion_event_count": snapshot.promotion_event_count,
        "promotion_fixture_set_count": snapshot.promotion_fixture_set_count,
        "invalid_promotion_event_count": snapshot.invalid_promotion_event_count,
        "source_promotion_event_ids": list(snapshot.source_promotion_event_ids_json),
        "source_promotion_artifact_ids": list(snapshot.source_promotion_artifact_ids_json),
        "source_promotion_receipt_sha256s": list(
            snapshot.source_promotion_receipt_sha256s_json
        ),
        "source_fixture_set_ids": list(snapshot.source_fixture_set_ids_json),
        "source_fixture_set_sha256s": list(snapshot.source_fixture_set_sha256s_json),
        "source_escalation_event_ids": list(snapshot.source_escalation_event_ids_json),
        "invalid_promotion_event_ids": list(snapshot.invalid_promotion_event_ids_json),
        "invalid_promotion_events": list(
            (snapshot.snapshot_payload_json or {}).get("invalid_promotion_events") or []
        ),
        "created_at": snapshot.created_at.isoformat(),
        "superseded_at": snapshot.superseded_at.isoformat()
        if snapshot.superseded_at
        else None,
    }
    if session is not None:
        summary["governance_integrity"] = (
            replay_alert_fixture_corpus_snapshot_governance_integrity(
                session,
                snapshot,
            )
        )
    return summary


def active_replay_alert_fixture_corpus_snapshot_summary(
    session,
    *,
    ensure_current: bool = True,
):
    snapshot = (
        ensure_active_replay_alert_fixture_corpus_snapshot(session)
        if ensure_current
        else import_module(
            "app.services.claim_support_replay_alert_fixture_corpus_governance"
        )._active_snapshot(session)
    )
    return replay_alert_fixture_corpus_snapshot_summary(snapshot, session=session)


def active_replay_alert_fixture_corpus_rows(
    session,
    *,
    exclude_case_ids: set[str] | None = None,
    limit: int = 100,
):
    return import_module(
        "app.services.claim_support_replay_alert_fixture_corpus_governance"
    ).active_replay_alert_fixture_corpus_rows(
        session,
        exclude_case_ids=exclude_case_ids,
        limit=limit,
    )


def refresh_active_replay_alert_fixture_corpus_summary(
    session,
    *,
    storage_service=None,
    recorded_by: str = "docling-system",
):
    snapshot = ensure_active_replay_alert_fixture_corpus_snapshot(
        session,
        storage_service=storage_service,
        recorded_by=recorded_by,
    )
    return replay_alert_fixture_corpus_snapshot_summary(snapshot, session=session)


def active_replay_alert_fixture_corpus_response_fields(
    summary: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "active_replay_fixture_corpus_snapshot_id": _uuid_or_none(
            summary.get("snapshot_id") if summary else None
        ),
        "active_replay_fixture_corpus_sha256": (
            summary.get("snapshot_sha256") if summary else None
        ),
        "active_replay_fixture_corpus_fixture_count": (
            int(summary.get("fixture_count") or 0) if summary else 0
        ),
        "active_replay_fixture_corpus_governance_event_id": _uuid_or_none(
            summary.get("semantic_governance_event_id") if summary else None
        ),
        "active_replay_fixture_corpus_governance_artifact_id": _uuid_or_none(
            summary.get("governance_artifact_id") if summary else None
        ),
        "active_replay_fixture_corpus_governance_receipt_sha256": (
            summary.get("governance_receipt_sha256") if summary else None
        ),
        "active_replay_fixture_corpus_governed": bool(
            ((summary or {}).get("governance_integrity") or {}).get("complete")
        )
        if summary
        else False,
    }
