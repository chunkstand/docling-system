from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import maybe_uuid as _uuid_or_none
from app.core.hashes import embedded_payload_hash_matches as _payload_hash_matches_embedded_field
from app.core.hashes import payload_sha256 as _payload_sha256
from app.db.models import (
    AgentTaskArtifact,
    AuditBundleExport,
    ClaimSupportReplayAlertFixtureCorpusRow,
    ClaimSupportReplayAlertFixtureCorpusSnapshot,
    RetrievalHardNegative,
    RetrievalJudgment,
    RetrievalTrainingRun,
    SemanticGovernanceEvent,
)
from app.services.query_utils import load_by_ids as _load_by_ids
from app.services.semantic_governance import (
    semantic_governance_event_payload as _semantic_governance_event_payload,
)

CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_SOURCE_TYPE = "claim_support_replay_alert_corpus"
CLAIM_SUPPORT_FIXTURE_PROMOTION_ARTIFACT_KIND = "claim_support_policy_impact_fixture_promotion"
CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_SNAPSHOT_ARTIFACT_KIND = (
    "claim_support_replay_alert_fixture_corpus_snapshot"
)
CLAIM_SUPPORT_FIXTURE_PROMOTION_EVENT_KIND = "claim_support_policy_impact_fixture_promoted"
CLAIM_SUPPORT_REPLAY_ESCALATION_EVENT_KIND = "claim_support_policy_impact_replay_escalated"
CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_SNAPSHOT_EVENT_KIND = (
    "claim_support_replay_alert_fixture_corpus_snapshot_activated"
)


def _claim_support_source_details(row: RetrievalJudgment | RetrievalHardNegative) -> dict[str, Any]:
    if row.source_type != CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_SOURCE_TYPE:
        return {}
    payload = row.payload_json if isinstance(row, RetrievalJudgment) else row.details_json
    details = (payload or {}).get("source_details") or {}
    return dict(details) if isinstance(details, dict) else {}


def _claim_support_corpus_source_reference_payloads(
    rows: list[RetrievalJudgment | RetrievalHardNegative],
) -> tuple[list[dict[str, Any]], dict[str, set[UUID]], list[str]]:
    references: list[dict[str, Any]] = []
    ids: dict[str, set[UUID]] = {
        "snapshot_ids": set(),
        "row_ids": set(),
        "promotion_artifact_ids": set(),
        "promotion_event_ids": set(),
        "escalation_event_ids": set(),
        "snapshot_governance_artifact_ids": set(),
        "snapshot_governance_event_ids": set(),
    }
    failures: list[str] = []
    for row in rows:
        details = _claim_support_source_details(row)
        if not details:
            continue
        carrier_type = (
            "retrieval_judgment"
            if isinstance(row, RetrievalJudgment)
            else "retrieval_hard_negative"
        )
        snapshot = details.get("snapshot") if isinstance(details.get("snapshot"), dict) else {}
        corpus_row = details.get("row") if isinstance(details.get("row"), dict) else {}
        snapshot_id = _uuid_or_none(snapshot.get("snapshot_id"))
        corpus_row_id = _uuid_or_none(corpus_row.get("corpus_row_id"))
        promotion_artifact_id = _uuid_or_none(corpus_row.get("promotion_artifact_id"))
        promotion_event_id = _uuid_or_none(corpus_row.get("promotion_event_id"))
        snapshot_artifact_id = _uuid_or_none(snapshot.get("governance_artifact_id"))
        snapshot_event_id = _uuid_or_none(snapshot.get("semantic_governance_event_id"))
        escalation_event_ids = [
            _uuid_or_none(value) for value in corpus_row.get("source_escalation_event_ids") or []
        ]
        if snapshot_id is None:
            failures.append(f"{carrier_type}:{row.id}:snapshot_id_missing")
        else:
            ids["snapshot_ids"].add(snapshot_id)
        if corpus_row_id is None:
            failures.append(f"{carrier_type}:{row.id}:corpus_row_id_missing")
        else:
            ids["row_ids"].add(corpus_row_id)
        if promotion_artifact_id is None:
            failures.append(f"{carrier_type}:{row.id}:promotion_artifact_id_missing")
        else:
            ids["promotion_artifact_ids"].add(promotion_artifact_id)
        if promotion_event_id is None:
            failures.append(f"{carrier_type}:{row.id}:promotion_event_id_missing")
        else:
            ids["promotion_event_ids"].add(promotion_event_id)
        if snapshot_artifact_id is not None:
            ids["snapshot_governance_artifact_ids"].add(snapshot_artifact_id)
        if snapshot_event_id is not None:
            ids["snapshot_governance_event_ids"].add(snapshot_event_id)
        parsed_escalation_ids = [value for value in escalation_event_ids if value is not None]
        if len(parsed_escalation_ids) != len(corpus_row.get("source_escalation_event_ids") or []):
            failures.append(f"{carrier_type}:{row.id}:source_escalation_event_id_invalid")
        ids["escalation_event_ids"].update(parsed_escalation_ids)
        references.append(
            {
                "carrier_type": carrier_type,
                "carrier_id": str(row.id),
                "source_payload_sha256": row.source_payload_sha256,
                "snapshot_id": str(snapshot_id) if snapshot_id else None,
                "snapshot_sha256": snapshot.get("snapshot_sha256"),
                "corpus_row_id": str(corpus_row_id) if corpus_row_id else None,
                "case_id": corpus_row.get("case_id"),
                "case_identity_sha256": corpus_row.get("case_identity_sha256"),
                "fixture_sha256": corpus_row.get("fixture_sha256"),
                "promotion_event_id": str(promotion_event_id) if promotion_event_id else None,
                "promotion_artifact_id": (
                    str(promotion_artifact_id) if promotion_artifact_id else None
                ),
                "promotion_receipt_sha256": corpus_row.get("promotion_receipt_sha256"),
                "snapshot_governance_event_id": (
                    str(snapshot_event_id) if snapshot_event_id else None
                ),
                "snapshot_governance_artifact_id": (
                    str(snapshot_artifact_id) if snapshot_artifact_id else None
                ),
                "snapshot_governance_receipt_sha256": snapshot.get("governance_receipt_sha256"),
                "source_change_impact_ids": list(corpus_row.get("source_change_impact_ids") or []),
                "source_escalation_event_ids": [str(value) for value in parsed_escalation_ids],
            }
        )
    return references, ids, failures


def _sorted_text_values(values: list[Any] | tuple[Any, ...] | set[Any] | None) -> list[str]:
    return sorted(str(value) for value in values or [])


def _agent_task_artifact_payload(row: AgentTaskArtifact) -> dict[str, Any]:
    payload = row.payload_json or {}
    receipt_sha256 = payload.get("receipt_sha256")
    return {
        "artifact_id": str(row.id),
        "task_id": str(row.task_id),
        "attempt_id": str(row.attempt_id) if row.attempt_id else None,
        "artifact_kind": row.artifact_kind,
        "storage_path": row.storage_path,
        "payload_sha256": _payload_sha256(payload),
        "receipt_sha256": receipt_sha256,
        "receipt_hash_matches": _payload_hash_matches_embedded_field(
            payload,
            hash_field="receipt_sha256",
        ),
        "payload": payload,
        "created_at": row.created_at.isoformat(),
    }


def _claim_support_corpus_snapshot_payload(
    row: ClaimSupportReplayAlertFixtureCorpusSnapshot,
) -> dict[str, Any]:
    snapshot_payload = row.snapshot_payload_json or {}
    computed_sha256 = _payload_sha256(snapshot_payload)
    return {
        "snapshot_id": str(row.id),
        "snapshot_name": row.snapshot_name,
        "status": row.status,
        "snapshot_sha256": row.snapshot_sha256,
        "computed_snapshot_sha256": computed_sha256,
        "snapshot_hash_matches": computed_sha256 == row.snapshot_sha256,
        "fixture_count": row.fixture_count,
        "promotion_event_count": row.promotion_event_count,
        "promotion_fixture_set_count": row.promotion_fixture_set_count,
        "invalid_promotion_event_count": row.invalid_promotion_event_count,
        "source_promotion_event_ids": list(row.source_promotion_event_ids_json or []),
        "source_promotion_artifact_ids": list(row.source_promotion_artifact_ids_json or []),
        "source_promotion_receipt_sha256s": list(row.source_promotion_receipt_sha256s_json or []),
        "source_fixture_set_ids": list(row.source_fixture_set_ids_json or []),
        "source_fixture_set_sha256s": list(row.source_fixture_set_sha256s_json or []),
        "source_escalation_event_ids": list(row.source_escalation_event_ids_json or []),
        "invalid_promotion_event_ids": list(row.invalid_promotion_event_ids_json or []),
        "semantic_governance_event_id": (
            str(row.semantic_governance_event_id) if row.semantic_governance_event_id else None
        ),
        "governance_artifact_id": (
            str(row.governance_artifact_id) if row.governance_artifact_id else None
        ),
        "governance_receipt_sha256": row.governance_receipt_sha256,
        "snapshot_payload": snapshot_payload,
        "created_at": row.created_at.isoformat(),
        "superseded_at": row.superseded_at.isoformat() if row.superseded_at else None,
    }


def _claim_support_corpus_row_payload(
    row: ClaimSupportReplayAlertFixtureCorpusRow,
) -> dict[str, Any]:
    fixture = row.fixture_json or {}
    computed_fixture_sha256 = _payload_sha256(fixture)
    return {
        "corpus_row_id": str(row.id),
        "snapshot_id": str(row.snapshot_id),
        "row_index": row.row_index,
        "case_id": row.case_id,
        "case_identity_sha256": row.case_identity_sha256,
        "fixture_sha256": row.fixture_sha256,
        "computed_fixture_sha256": computed_fixture_sha256,
        "fixture_hash_matches": computed_fixture_sha256 == row.fixture_sha256,
        "fixture": fixture,
        "fixture_set_id": str(row.fixture_set_id) if row.fixture_set_id else None,
        "promotion_event_id": str(row.promotion_event_id) if row.promotion_event_id else None,
        "promotion_artifact_id": (
            str(row.promotion_artifact_id) if row.promotion_artifact_id else None
        ),
        "promotion_receipt_sha256": row.promotion_receipt_sha256,
        "source_change_impact_ids": list(row.source_change_impact_ids_json or []),
        "source_escalation_event_ids": list(row.source_escalation_event_ids_json or []),
        "replay_alert_source": row.replay_alert_source_json or {},
        "created_at": row.created_at.isoformat(),
    }


def claim_support_replay_alert_corpus_lineage_payload(
    session: Session,
    *,
    judgments: list[RetrievalJudgment],
    hard_negatives: list[RetrievalHardNegative],
) -> dict[str, Any]:
    references, ids, failures = _claim_support_corpus_source_reference_payloads(
        [*judgments, *hard_negatives]
    )
    snapshots = _load_by_ids(
        session,
        ClaimSupportReplayAlertFixtureCorpusSnapshot,
        ids["snapshot_ids"],
    )
    rows = _load_by_ids(session, ClaimSupportReplayAlertFixtureCorpusRow, ids["row_ids"])
    promotion_artifacts = _load_by_ids(
        session,
        AgentTaskArtifact,
        ids["promotion_artifact_ids"],
    )
    snapshot_governance_artifacts = _load_by_ids(
        session,
        AgentTaskArtifact,
        ids["snapshot_governance_artifact_ids"],
    )
    promotion_events = _load_by_ids(
        session,
        SemanticGovernanceEvent,
        ids["promotion_event_ids"],
    )
    escalation_events = _load_by_ids(
        session,
        SemanticGovernanceEvent,
        ids["escalation_event_ids"],
    )
    snapshot_governance_events = _load_by_ids(
        session,
        SemanticGovernanceEvent,
        ids["snapshot_governance_event_ids"],
    )

    missing = {
        "snapshot_ids": sorted(str(value) for value in ids["snapshot_ids"] - set(snapshots)),
        "row_ids": sorted(str(value) for value in ids["row_ids"] - set(rows)),
        "promotion_artifact_ids": sorted(
            str(value) for value in ids["promotion_artifact_ids"] - set(promotion_artifacts)
        ),
        "promotion_event_ids": sorted(
            str(value) for value in ids["promotion_event_ids"] - set(promotion_events)
        ),
        "escalation_event_ids": sorted(
            str(value) for value in ids["escalation_event_ids"] - set(escalation_events)
        ),
        "snapshot_governance_artifact_ids": sorted(
            str(value)
            for value in ids["snapshot_governance_artifact_ids"]
            - set(snapshot_governance_artifacts)
        ),
        "snapshot_governance_event_ids": sorted(
            str(value)
            for value in ids["snapshot_governance_event_ids"] - set(snapshot_governance_events)
        ),
    }
    for key, values in missing.items():
        failures.extend(f"{key}:{value}:missing" for value in values)

    snapshot_payloads = [_claim_support_corpus_snapshot_payload(row) for row in snapshots.values()]
    corpus_row_payloads = [_claim_support_corpus_row_payload(row) for row in rows.values()]
    promotion_artifact_payloads = [
        _agent_task_artifact_payload(row) for row in promotion_artifacts.values()
    ]
    snapshot_artifact_payloads = [
        _agent_task_artifact_payload(row) for row in snapshot_governance_artifacts.values()
    ]
    promotion_event_payloads = [
        _semantic_governance_event_payload(row) for row in promotion_events.values()
    ]
    escalation_event_payloads = [
        _semantic_governance_event_payload(row) for row in escalation_events.values()
    ]
    snapshot_event_payloads = [
        _semantic_governance_event_payload(row) for row in snapshot_governance_events.values()
    ]

    reference_snapshot_hashes_match = all(
        (snapshot_id := _uuid_or_none(reference.get("snapshot_id"))) in snapshots
        and snapshots[snapshot_id].snapshot_sha256 == reference.get("snapshot_sha256")
        for reference in references
    )
    reference_row_identity_hashes_match = all(
        (corpus_row_id := _uuid_or_none(reference.get("corpus_row_id"))) in rows
        and rows[corpus_row_id].fixture_sha256 == reference.get("fixture_sha256")
        and rows[corpus_row_id].case_id == reference.get("case_id")
        and rows[corpus_row_id].case_identity_sha256 == reference.get("case_identity_sha256")
        and rows[corpus_row_id].snapshot_id == _uuid_or_none(reference.get("snapshot_id"))
        for reference in references
    )
    reference_row_promotion_links_match = all(
        (corpus_row_id := _uuid_or_none(reference.get("corpus_row_id"))) in rows
        and str(rows[corpus_row_id].promotion_event_id) == reference.get("promotion_event_id")
        and str(rows[corpus_row_id].promotion_artifact_id) == reference.get("promotion_artifact_id")
        and rows[corpus_row_id].promotion_receipt_sha256
        == reference.get("promotion_receipt_sha256")
        for reference in references
    )
    reference_row_source_links_match = all(
        (corpus_row_id := _uuid_or_none(reference.get("corpus_row_id"))) in rows
        and _sorted_text_values(rows[corpus_row_id].source_change_impact_ids_json)
        == _sorted_text_values(reference.get("source_change_impact_ids"))
        and _sorted_text_values(rows[corpus_row_id].source_escalation_event_ids_json)
        == _sorted_text_values(reference.get("source_escalation_event_ids"))
        for reference in references
    )
    reference_snapshot_governance_links_match = all(
        (snapshot_id := _uuid_or_none(reference.get("snapshot_id"))) in snapshots
        and str(snapshots[snapshot_id].semantic_governance_event_id)
        == reference.get("snapshot_governance_event_id")
        and str(snapshots[snapshot_id].governance_artifact_id)
        == reference.get("snapshot_governance_artifact_id")
        and snapshots[snapshot_id].governance_receipt_sha256
        == reference.get("snapshot_governance_receipt_sha256")
        for reference in references
    )
    promotion_artifact_hashes_match = all(
        row["artifact_kind"] == CLAIM_SUPPORT_FIXTURE_PROMOTION_ARTIFACT_KIND
        and row["receipt_hash_matches"]
        for row in promotion_artifact_payloads
    )
    snapshot_artifact_hashes_match = all(
        row["artifact_kind"] == CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_SNAPSHOT_ARTIFACT_KIND
        and row["receipt_hash_matches"]
        for row in snapshot_artifact_payloads
    )
    promotion_event_kinds_match = all(
        row.event_kind == CLAIM_SUPPORT_FIXTURE_PROMOTION_EVENT_KIND
        for row in promotion_events.values()
    )
    escalation_event_kinds_match = all(
        row.event_kind == CLAIM_SUPPORT_REPLAY_ESCALATION_EVENT_KIND
        and row.subject_table == "claim_support_policy_change_impacts"
        for row in escalation_events.values()
    )
    snapshot_event_kinds_match = all(
        row.event_kind == CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_SNAPSHOT_EVENT_KIND
        and row.subject_table == "claim_support_replay_alert_fixture_corpus_snapshots"
        for row in snapshot_governance_events.values()
    )
    promotion_event_integrity_complete = all(
        row["integrity"]["complete"] for row in promotion_event_payloads
    )
    escalation_event_integrity_complete = all(
        row["integrity"]["complete"] for row in escalation_event_payloads
    )
    snapshot_event_integrity_complete = all(
        row["integrity"]["complete"] for row in snapshot_event_payloads
    )
    row_snapshot_links_match = all(row.snapshot_id in snapshots for row in rows.values())
    row_promotion_links_match = all(
        row.promotion_event_id in promotion_events
        and row.promotion_artifact_id in promotion_artifacts
        for row in rows.values()
    )
    row_escalation_links_match = all(
        all(
            _uuid_or_none(value) in escalation_events
            for value in row.source_escalation_event_ids_json
        )
        for row in rows.values()
    )
    snapshot_governance_links_match = all(
        row.semantic_governance_event_id in snapshot_governance_events
        and row.governance_artifact_id in snapshot_governance_artifacts
        for row in snapshots.values()
    )
    row_fixture_hashes_match = all(row["fixture_hash_matches"] for row in corpus_row_payloads)
    snapshot_hashes_match = all(row["snapshot_hash_matches"] for row in snapshot_payloads)
    source_references_resolve = not any(missing.values()) and not failures
    integrity = {
        "source_reference_count": len(references),
        "snapshot_count": len(snapshot_payloads),
        "row_count": len(corpus_row_payloads),
        "promotion_artifact_count": len(promotion_artifact_payloads),
        "promotion_event_count": len(promotion_event_payloads),
        "escalation_event_count": len(escalation_event_payloads),
        "snapshot_governance_artifact_count": len(snapshot_artifact_payloads),
        "snapshot_governance_event_count": len(snapshot_event_payloads),
        "source_references_resolve": source_references_resolve,
        "reference_snapshot_hashes_match": reference_snapshot_hashes_match,
        "reference_row_identity_hashes_match": reference_row_identity_hashes_match,
        "reference_row_promotion_links_match": reference_row_promotion_links_match,
        "reference_row_source_links_match": reference_row_source_links_match,
        "reference_snapshot_governance_links_match": (reference_snapshot_governance_links_match),
        "row_fixture_hashes_match": row_fixture_hashes_match,
        "snapshot_hashes_match": snapshot_hashes_match,
        "promotion_artifact_hashes_match": promotion_artifact_hashes_match,
        "snapshot_artifact_hashes_match": snapshot_artifact_hashes_match,
        "promotion_event_kinds_match": promotion_event_kinds_match,
        "escalation_event_kinds_match": escalation_event_kinds_match,
        "snapshot_event_kinds_match": snapshot_event_kinds_match,
        "promotion_event_integrity_complete": promotion_event_integrity_complete,
        "escalation_event_integrity_complete": escalation_event_integrity_complete,
        "snapshot_event_integrity_complete": snapshot_event_integrity_complete,
        "row_snapshot_links_match": row_snapshot_links_match,
        "row_promotion_links_match": row_promotion_links_match,
        "row_escalation_links_match": row_escalation_links_match,
        "snapshot_governance_links_match": snapshot_governance_links_match,
        "missing": missing,
        "failures": sorted(set(failures)),
    }
    integrity["complete"] = all(
        bool(integrity[key])
        for key in (
            "source_references_resolve",
            "reference_snapshot_hashes_match",
            "reference_row_identity_hashes_match",
            "reference_row_promotion_links_match",
            "reference_row_source_links_match",
            "reference_snapshot_governance_links_match",
            "row_fixture_hashes_match",
            "snapshot_hashes_match",
            "promotion_artifact_hashes_match",
            "snapshot_artifact_hashes_match",
            "promotion_event_kinds_match",
            "escalation_event_kinds_match",
            "snapshot_event_kinds_match",
            "promotion_event_integrity_complete",
            "escalation_event_integrity_complete",
            "snapshot_event_integrity_complete",
            "row_snapshot_links_match",
            "row_promotion_links_match",
            "row_escalation_links_match",
            "snapshot_governance_links_match",
        )
    )
    return {
        "source_references": references,
        "snapshots": sorted(snapshot_payloads, key=lambda row: row["snapshot_id"]),
        "rows": sorted(corpus_row_payloads, key=lambda row: (row["snapshot_id"], row["row_index"])),
        "promotion_artifacts": sorted(
            promotion_artifact_payloads,
            key=lambda row: row["artifact_id"],
        ),
        "promotion_events": sorted(promotion_event_payloads, key=lambda row: row["event_id"]),
        "escalation_events": sorted(escalation_event_payloads, key=lambda row: row["event_id"]),
        "snapshot_governance_artifacts": sorted(
            snapshot_artifact_payloads,
            key=lambda row: row["artifact_id"],
        ),
        "snapshot_governance_events": sorted(
            snapshot_event_payloads,
            key=lambda row: row["event_id"],
        ),
        "integrity": integrity,
    }


def training_run_claim_support_replay_alert_corpus_lineage_payload(
    session: Session,
    training_run: RetrievalTrainingRun,
) -> dict[str, Any]:
    judgments = (
        session.execute(
            select(RetrievalJudgment)
            .where(RetrievalJudgment.judgment_set_id == training_run.judgment_set_id)
            .order_by(RetrievalJudgment.created_at.asc(), RetrievalJudgment.id.asc())
        )
        .scalars()
        .all()
    )
    hard_negatives = (
        session.execute(
            select(RetrievalHardNegative)
            .where(RetrievalHardNegative.judgment_set_id == training_run.judgment_set_id)
            .order_by(RetrievalHardNegative.created_at.asc(), RetrievalHardNegative.id.asc())
        )
        .scalars()
        .all()
    )
    return claim_support_replay_alert_corpus_lineage_payload(
        session,
        judgments=judgments,
        hard_negatives=hard_negatives,
    )


def payload_requires_claim_support_replay_alert_corpus_lineage(
    payload: dict[str, Any],
) -> bool:
    corpus_integrity = payload.get("claim_support_replay_alert_corpus_integrity") or {}
    if corpus_integrity.get("source_reference_count", 0):
        return True
    return any(
        row.get("source_type") == CLAIM_SUPPORT_REPLAY_ALERT_CORPUS_SOURCE_TYPE
        for row in [
            *(payload.get("retrieval_judgments") or []),
            *(payload.get("retrieval_hard_negatives") or []),
        ]
        if isinstance(row, dict)
    )


def payload_claim_support_replay_alert_corpus_lineage_complete(
    payload: dict[str, Any],
) -> bool:
    if not payload_requires_claim_support_replay_alert_corpus_lineage(payload):
        return True
    audit_checklist = payload.get("audit_checklist") or {}
    corpus_integrity = payload.get("claim_support_replay_alert_corpus_integrity") or {}
    return (
        audit_checklist.get("claim_support_replay_alert_corpus_lineage_complete") is True
        and corpus_integrity.get("complete") is True
    )


def training_audit_bundle_claim_support_replay_alert_corpus_lineage_status(
    session: Session,
    bundle: AuditBundleExport | None,
    training_run: RetrievalTrainingRun,
) -> dict[str, Any]:
    payload = (bundle.bundle_payload_json or {}).get("payload") if bundle else {}
    payload = payload if isinstance(payload, dict) else {}
    bundle_integrity = payload.get("claim_support_replay_alert_corpus_integrity") or {}
    current_lineage = training_run_claim_support_replay_alert_corpus_lineage_payload(
        session,
        training_run,
    )
    current_integrity = current_lineage["integrity"]
    bundle_source_reference_count = int(bundle_integrity.get("source_reference_count") or 0)
    current_source_reference_count = int(current_integrity.get("source_reference_count") or 0)
    bundle_required = payload_requires_claim_support_replay_alert_corpus_lineage(payload)
    current_required = current_source_reference_count > 0
    required = bundle_required or current_required
    bundle_complete = payload_claim_support_replay_alert_corpus_lineage_complete(payload)
    current_complete = True if not current_required else current_integrity.get("complete") is True
    source_reference_counts_match = bundle_source_reference_count == current_source_reference_count
    complete = (
        True
        if not required
        else bundle_complete and current_complete and source_reference_counts_match
    )
    return {
        "required": required,
        "bundle_required": bundle_required,
        "current_required": current_required,
        "bundle_source_reference_count": bundle_source_reference_count,
        "current_source_reference_count": current_source_reference_count,
        "source_reference_counts_match": source_reference_counts_match,
        "bundle_complete": bundle_complete,
        "current_complete": current_complete,
        "complete": complete,
        "current_failures": list(current_integrity.get("failures") or []),
        "current_missing": current_integrity.get("missing") or {},
    }
