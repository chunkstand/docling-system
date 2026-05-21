# ruff: noqa: E501, F401, I001
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.public.agent_tasks import AgentTaskVerification
from app.db.public.audit_and_evidence import ClaimEvidenceDerivation, EvidencePackageExport
from app.db.public.claim_support import ClaimSupportPolicyChangeImpact
from app.db.public.ingest import Document
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.services.evidence_common import uuid_values as _uuid_values
from app.services.evidence_constants import (
    CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND,
    CLAIM_SUPPORT_POLICY_IMPACT_OPEN_REPLAY_STATUSES,
    CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_CLOSED_EVENT_KIND,
    CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND,
)
from app.services.evidence_records import select_by_ids as _select_by_ids
from app.services.evidence_claim_support_replay_alerts import (
    claim_support_replay_alert_fixture_corpus_snapshots_by_promotion_event as _claim_support_replay_alert_fixture_corpus_snapshots_by_promotion_event,
    claim_support_replay_alert_waiver_closure_events_by_impact as _claim_support_replay_alert_waiver_closure_events_by_impact,
    claim_support_replay_alert_waiver_lifecycle_summary as _claim_support_replay_alert_waiver_lifecycle_summary,
    waiver_closure_event_payload as _waiver_closure_event_payload,
)

def _export_document_run_map(export: EvidencePackageExport) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    payload = export.package_payload_json or {}
    for card in payload.get("evidence_cards") or []:
        document_id = card.get("document_id")
        run_id = card.get("run_id")
        if document_id and run_id:
            mapping.setdefault(str(document_id), set()).add(str(run_id))
    if not mapping:
        run_ids = {str(value) for value in export.run_ids_json or []}
        for document_id in export.document_ids_json or []:
            mapping[str(document_id)] = set(run_ids)
    return mapping


def _empty_claim_support_policy_change_impact_summary() -> dict[str, Any]:
    waiver_lifecycle = {
        "related_waiver_count": 0,
        "unresolved_waiver_count": 0,
        "closed_waiver_count": 0,
        "invalid_waiver_closure_count": 0,
        "waiver_closure_integrity_verified": True,
        "clear": True,
    }
    replay_alert_fixture_corpus = {
        "related_snapshot_count": 0,
        "invalid_snapshot_governance_count": 0,
        "governance_integrity_verified": True,
        "trace_complete": True,
        "active_replay_alert_fixture_corpus_snapshot_id": None,
        "active_replay_alert_fixture_corpus_sha256": None,
        "invalid_snapshot_ids": [],
        "snapshots": [],
    }
    return {
        "related_count": 0,
        "open_count": 0,
        "closed_count": 0,
        "blocked_count": 0,
        "replay_status_counts": {},
        "waiver_lifecycle": waiver_lifecycle,
        "replay_alert_fixture_corpus": replay_alert_fixture_corpus,
        "clear": True,
        "impacts": [],
    }


def _claim_support_policy_change_impact_refs(
    session: Session,
    exports: list[EvidencePackageExport],
) -> dict[str, set[str]]:
    report_export_ids = [row.id for row in exports if row.package_kind == "technical_report_claims"]
    if not report_export_ids:
        return {
            "claim_derivation_ids": set(),
            "draft_task_ids": set(),
            "verification_task_ids": set(),
        }
    derivations = list(
        session.scalars(
            select(ClaimEvidenceDerivation)
            .where(ClaimEvidenceDerivation.evidence_package_export_id.in_(report_export_ids))
            .order_by(ClaimEvidenceDerivation.created_at.asc())
        )
    )
    draft_task_ids = {
        str(row.agent_task_id) for row in derivations if row.agent_task_id is not None
    }
    draft_task_ids.update(
        str(row.agent_task_id)
        for row in exports
        if row.package_kind == "technical_report_claims" and row.agent_task_id is not None
    )
    verification_rows = (
        list(
            session.scalars(
                select(AgentTaskVerification)
                .where(
                    AgentTaskVerification.target_task_id.in_(_uuid_values(draft_task_ids)),
                    AgentTaskVerification.verifier_type == "technical_report_gate",
                )
                .order_by(AgentTaskVerification.created_at.asc())
            )
        )
        if draft_task_ids
        else []
    )
    return {
        "claim_derivation_ids": {str(row.id) for row in derivations},
        "draft_task_ids": draft_task_ids,
        "verification_task_ids": {
            str(row.verification_task_id)
            for row in verification_rows
            if row.verification_task_id is not None
        },
    }


def _claim_support_policy_change_impact_events_by_row(
    session: Session,
    rows: list[ClaimSupportPolicyChangeImpact],
    *,
    event_kind: str = CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_CLOSED_EVENT_KIND,
) -> dict[UUID, list[SemanticGovernanceEvent]]:
    row_ids = [row.id for row in rows]
    if not row_ids:
        return {}
    events = list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.subject_table == "claim_support_policy_change_impacts",
                SemanticGovernanceEvent.subject_id.in_(row_ids),
                SemanticGovernanceEvent.event_kind == event_kind,
            )
            .order_by(
                SemanticGovernanceEvent.created_at.asc(),
                SemanticGovernanceEvent.event_sequence.asc(),
            )
        )
    )
    events_by_row: dict[UUID, list[SemanticGovernanceEvent]] = {}
    for event in events:
        if event.subject_id is not None:
            events_by_row.setdefault(event.subject_id, []).append(event)
    return events_by_row


def _claim_support_policy_fixture_promotion_events_by_impact(
    session: Session,
    rows: list[ClaimSupportPolicyChangeImpact],
) -> dict[UUID, list[SemanticGovernanceEvent]]:
    row_ids = {str(row.id) for row in rows}
    if not row_ids:
        return {}
    events = list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(
                SemanticGovernanceEvent.event_kind
                == CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND
            )
            .order_by(
                SemanticGovernanceEvent.created_at.asc(),
                SemanticGovernanceEvent.event_sequence.asc(),
            )
        )
    )
    events_by_row: dict[UUID, list[SemanticGovernanceEvent]] = {}
    rows_by_id = {str(row.id): row for row in rows}
    for event in events:
        promotion_payload = (event.event_payload_json or {}).get(
            "claim_support_policy_impact_fixture_promotion"
        ) or {}
        source_change_impact_ids = {
            str(value) for value in promotion_payload.get("source_change_impact_ids") or [] if value
        }
        for row_id in sorted(source_change_impact_ids & row_ids):
            events_by_row.setdefault(rows_by_id[row_id].id, []).append(event)
    return events_by_row


def _fixture_promotion_event_payload(event: SemanticGovernanceEvent) -> dict[str, Any]:
    promotion_payload = (event.event_payload_json or {}).get(
        "claim_support_policy_impact_fixture_promotion"
    ) or {}
    return {
        "event_id": str(event.id),
        "event_hash": event.event_hash,
        "receipt_sha256": event.receipt_sha256,
        "agent_task_artifact_id": str(event.agent_task_artifact_id)
        if event.agent_task_artifact_id
        else None,
        "payload_sha256": event.payload_sha256,
        "fixture_set_id": promotion_payload.get("fixture_set_id"),
        "fixture_set_name": promotion_payload.get("fixture_set_name"),
        "fixture_set_version": promotion_payload.get("fixture_set_version"),
        "fixture_set_sha256": promotion_payload.get("fixture_set_sha256"),
        "candidate_count": promotion_payload.get("candidate_count"),
        "source_escalation_event_ids": list(
            promotion_payload.get("source_escalation_event_ids") or []
        ),
    }

def _claim_support_policy_change_impact_summary(
    session: Session,
    exports: list[EvidencePackageExport],
) -> dict[str, Any]:
    refs = _claim_support_policy_change_impact_refs(session, exports)
    if not any(refs.values()):
        return _empty_claim_support_policy_change_impact_summary()
    rows = list(
        session.scalars(
            select(ClaimSupportPolicyChangeImpact).order_by(
                ClaimSupportPolicyChangeImpact.created_at.asc(),
                ClaimSupportPolicyChangeImpact.id.asc(),
            )
        )
    )
    matching_rows: list[ClaimSupportPolicyChangeImpact] = []
    for row in rows:
        if (
            set(str(value) for value in (row.impacted_claim_derivation_ids_json or []))
            & refs["claim_derivation_ids"]
            or set(str(value) for value in (row.impacted_task_ids_json or []))
            & refs["draft_task_ids"]
            or set(str(value) for value in (row.impacted_verification_task_ids_json or []))
            & refs["verification_task_ids"]
        ):
            matching_rows.append(row)

    if not matching_rows:
        return _empty_claim_support_policy_change_impact_summary()

    events_by_row = _claim_support_policy_change_impact_events_by_row(session, matching_rows)
    escalation_events_by_row = _claim_support_policy_change_impact_events_by_row(
        session,
        matching_rows,
        event_kind=CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND,
    )
    fixture_promotion_events_by_row = _claim_support_policy_fixture_promotion_events_by_impact(
        session, matching_rows
    )
    corpus_snapshots_by_promotion_event = (
        _claim_support_replay_alert_fixture_corpus_snapshots_by_promotion_event(
            session,
            [
                event
                for event_rows in fixture_promotion_events_by_row.values()
                for event in event_rows
            ],
        )
    )
    waiver_closure_events_by_row = _claim_support_replay_alert_waiver_closure_events_by_impact(
        session, matching_rows
    )
    waiver_lifecycle = _claim_support_replay_alert_waiver_lifecycle_summary(
        session,
        matching_rows,
        waiver_closure_events_by_row,
    )
    status_counts: dict[str, int] = {}
    impact_rows: list[dict[str, Any]] = []
    for row in matching_rows:
        status_value = str(row.replay_status)
        status_counts[status_value] = status_counts.get(status_value, 0) + 1
        closure_events = events_by_row.get(row.id, [])
        escalation_events = escalation_events_by_row.get(row.id, [])
        fixture_promotion_events = fixture_promotion_events_by_row.get(row.id, [])
        replay_alert_fixture_corpus_snapshots_by_id: dict[str, dict[str, Any]] = {}
        for event in fixture_promotion_events:
            for snapshot_payload in corpus_snapshots_by_promotion_event.get(event.id, []):
                replay_alert_fixture_corpus_snapshots_by_id[snapshot_payload["snapshot_id"]] = (
                    snapshot_payload
                )
        replay_alert_fixture_corpus_snapshots = [
            replay_alert_fixture_corpus_snapshots_by_id[snapshot_id]
            for snapshot_id in sorted(replay_alert_fixture_corpus_snapshots_by_id)
        ]
        waiver_closure_events = waiver_closure_events_by_row.get(row.id, [])
        waiver_closure_event_payloads = [
            _waiver_closure_event_payload(session, event) for event in waiver_closure_events
        ]
        impact_rows.append(
            {
                "change_impact_id": str(row.id),
                "policy_name": row.policy_name,
                "policy_version": row.policy_version,
                "impact_scope": row.impact_scope,
                "impact_payload_sha256": row.impact_payload_sha256,
                "replay_status": row.replay_status,
                "replay_recommended_count": row.replay_recommended_count,
                "replay_task_ids": list(row.replay_task_ids_json or []),
                "replay_closure_sha256": row.replay_closure_sha256,
                "replay_closed_at": row.replay_closed_at.isoformat()
                if row.replay_closed_at
                else None,
                "closure_governance_events": [
                    {
                        "event_id": str(event.id),
                        "event_hash": event.event_hash,
                        "receipt_sha256": event.receipt_sha256,
                        "agent_task_artifact_id": str(event.agent_task_artifact_id)
                        if event.agent_task_artifact_id
                        else None,
                        "payload_sha256": event.payload_sha256,
                    }
                    for event in closure_events
                ],
                "escalation_governance_events": [
                    {
                        "event_id": str(event.id),
                        "event_hash": event.event_hash,
                        "receipt_sha256": event.receipt_sha256,
                        "agent_task_artifact_id": str(event.agent_task_artifact_id)
                        if event.agent_task_artifact_id
                        else None,
                        "payload_sha256": event.payload_sha256,
                        "alert_kind": (
                            (
                                event.event_payload_json.get(
                                    "claim_support_policy_impact_replay_escalation"
                                )
                                or {}
                            ).get("alert_kind")
                            if event.event_payload_json
                            else None
                        ),
                    }
                    for event in escalation_events
                ],
                "fixture_promotion_governance_events": [
                    _fixture_promotion_event_payload(event) for event in fixture_promotion_events
                ],
                "replay_alert_fixture_corpus_snapshots": (replay_alert_fixture_corpus_snapshots),
                "waiver_closure_governance_events": waiver_closure_event_payloads,
            }
        )

    open_impacts = [
        row
        for row in impact_rows
        if row["replay_status"] in CLAIM_SUPPORT_POLICY_IMPACT_OPEN_REPLAY_STATUSES
    ]
    snapshots_by_id = {
        snapshot["snapshot_id"]: snapshot
        for row in impact_rows
        for snapshot in row.get("replay_alert_fixture_corpus_snapshots") or []
    }
    invalid_snapshot_ids = sorted(
        snapshot_id
        for snapshot_id, snapshot in snapshots_by_id.items()
        if not (snapshot.get("governance_integrity") or {}).get("complete")
    )
    trace_incomplete_snapshot_ids = sorted(
        snapshot_id
        for snapshot_id, snapshot in snapshots_by_id.items()
        if not snapshot.get("trace_complete")
    )
    active_snapshots = [
        snapshot for snapshot in snapshots_by_id.values() if snapshot.get("status") == "active"
    ]
    replay_alert_fixture_corpus = {
        "related_snapshot_count": len(snapshots_by_id),
        "invalid_snapshot_governance_count": len(invalid_snapshot_ids),
        "trace_incomplete_snapshot_count": len(trace_incomplete_snapshot_ids),
        "governance_integrity_verified": not invalid_snapshot_ids,
        "trace_complete": not trace_incomplete_snapshot_ids,
        "active_replay_alert_fixture_corpus_snapshot_id": (
            active_snapshots[-1]["snapshot_id"] if active_snapshots else None
        ),
        "active_replay_alert_fixture_corpus_sha256": (
            active_snapshots[-1]["snapshot_sha256"] if active_snapshots else None
        ),
        "active_replay_alert_fixture_corpus_governance_receipt_sha256": (
            active_snapshots[-1].get("governance_receipt_sha256") if active_snapshots else None
        ),
        "invalid_snapshot_ids": invalid_snapshot_ids,
        "trace_incomplete_snapshot_ids": trace_incomplete_snapshot_ids,
        "snapshots": [snapshots_by_id[snapshot_id] for snapshot_id in sorted(snapshots_by_id)],
    }
    return {
        "related_count": len(impact_rows),
        "open_count": len(open_impacts),
        "closed_count": sum(1 for row in impact_rows if row["replay_status"] == "closed"),
        "blocked_count": sum(1 for row in impact_rows if row["replay_status"] == "blocked"),
        "replay_status_counts": status_counts,
        "waiver_lifecycle": waiver_lifecycle,
        "replay_alert_fixture_corpus": replay_alert_fixture_corpus,
        "clear": (
            not open_impacts
            and waiver_lifecycle["clear"]
            and replay_alert_fixture_corpus["governance_integrity_verified"]
            and replay_alert_fixture_corpus["trace_complete"]
        ),
        "impacts": impact_rows,
    }


def _change_impact_payload(
    session: Session,
    exports: list[EvidencePackageExport],
) -> dict:
    impacts: list[dict[str, Any]] = []
    claim_support_policy_impacts = _claim_support_policy_change_impact_summary(
        session,
        exports,
    )
    if not exports:
        return {
            "impacted": True,
            "impact_count": 1,
            "impacts": [
                {
                    "impact_type": "missing_evidence_export",
                    "reason": "No frozen evidence package export is linked to the report draft.",
                }
            ],
            "claim_support_policy_change_impacts": claim_support_policy_impacts,
        }
    document_ids = {
        UUID(str(document_id))
        for export in exports
        for document_id in (export.document_ids_json or [])
    }
    documents_by_id = _select_by_ids(session, Document, document_ids)
    for export in exports:
        for document_id, exported_run_ids in _export_document_run_map(export).items():
            document = documents_by_id.get(UUID(document_id))
            if document is None:
                impacts.append(
                    {
                        "impact_type": "source_document_missing",
                        "evidence_package_export_id": str(export.id),
                        "document_id": document_id,
                    }
                )
                continue
            active_run_id = str(document.active_run_id) if document.active_run_id else None
            latest_run_id = str(document.latest_run_id) if document.latest_run_id else None
            if active_run_id not in exported_run_ids:
                impacts.append(
                    {
                        "impact_type": "active_run_changed",
                        "evidence_package_export_id": str(export.id),
                        "document_id": document_id,
                        "exported_run_ids": sorted(exported_run_ids),
                        "current_active_run_id": active_run_id,
                    }
                )
            if latest_run_id and latest_run_id not in exported_run_ids:
                impacts.append(
                    {
                        "impact_type": "newer_run_available",
                        "evidence_package_export_id": str(export.id),
                        "document_id": document_id,
                        "exported_run_ids": sorted(exported_run_ids),
                        "current_latest_run_id": latest_run_id,
                    }
                )
    for impact in claim_support_policy_impacts["impacts"]:
        if impact["replay_status"] not in CLAIM_SUPPORT_POLICY_IMPACT_OPEN_REPLAY_STATUSES:
            continue
        impacts.append(
            {
                "impact_type": "claim_support_policy_change_replay_open",
                "change_impact_id": impact["change_impact_id"],
                "policy_name": impact["policy_name"],
                "policy_version": impact["policy_version"],
                "replay_status": impact["replay_status"],
                "replay_recommended_count": impact["replay_recommended_count"],
                "reason": (
                    "A claim-support calibration policy changed after this report's "
                    "support judgments were produced, and managed replay has not closed."
                ),
            }
        )
    waiver_lifecycle = claim_support_policy_impacts.get("waiver_lifecycle") or {}
    unresolved_waiver_count = int(waiver_lifecycle.get("unresolved_waiver_count") or 0)
    invalid_waiver_closure_count = int(waiver_lifecycle.get("invalid_waiver_closure_count") or 0)
    if unresolved_waiver_count:
        impacts.append(
            {
                "impact_type": "claim_support_replay_alert_fixture_coverage_waiver_unresolved",
                "unresolved_waiver_count": unresolved_waiver_count,
                "reason": (
                    "Replay-alert fixture coverage waivers related to this report still "
                    "lack complete promoted fixture coverage."
                ),
            }
        )
    if invalid_waiver_closure_count:
        impacts.append(
            {
                "impact_type": (
                    "claim_support_replay_alert_fixture_coverage_waiver_closure_invalid"
                ),
                "invalid_waiver_closure_count": invalid_waiver_closure_count,
                "reason": (
                    "Replay-alert fixture coverage waiver closure receipts related to "
                    "this report failed integrity checks."
                ),
            }
        )
    replay_alert_fixture_corpus = (
        claim_support_policy_impacts.get("replay_alert_fixture_corpus") or {}
    )
    invalid_corpus_snapshot_count = int(
        replay_alert_fixture_corpus.get("invalid_snapshot_governance_count") or 0
    )
    trace_incomplete_corpus_snapshot_count = int(
        replay_alert_fixture_corpus.get("trace_incomplete_snapshot_count") or 0
    )
    if invalid_corpus_snapshot_count:
        impacts.append(
            {
                "impact_type": (
                    "claim_support_replay_alert_fixture_corpus_snapshot_governance_invalid"
                ),
                "invalid_snapshot_governance_count": invalid_corpus_snapshot_count,
                "invalid_snapshot_ids": list(
                    replay_alert_fixture_corpus.get("invalid_snapshot_ids") or []
                ),
                "reason": (
                    "Replay-alert fixture corpus snapshots related to this report "
                    "failed governance receipt integrity checks."
                ),
            }
        )
    if trace_incomplete_corpus_snapshot_count:
        impacts.append(
            {
                "impact_type": (
                    "claim_support_replay_alert_fixture_corpus_snapshot_trace_incomplete"
                ),
                "trace_incomplete_snapshot_count": (trace_incomplete_corpus_snapshot_count),
                "trace_incomplete_snapshot_ids": list(
                    replay_alert_fixture_corpus.get("trace_incomplete_snapshot_ids") or []
                ),
                "reason": (
                    "Replay-alert fixture corpus snapshots related to this report "
                    "do not have complete row-to-promotion evidence trace coverage."
                ),
            }
        )
    return {
        "impacted": bool(impacts),
        "impact_count": len(impacts),
        "impacts": impacts,
        "claim_support_policy_change_impacts": claim_support_policy_impacts,
    }


empty_claim_support_policy_change_impact_summary = (
    _empty_claim_support_policy_change_impact_summary
)
claim_support_policy_change_impact_refs = _claim_support_policy_change_impact_refs
claim_support_policy_change_impact_events_by_row = (
    _claim_support_policy_change_impact_events_by_row
)
claim_support_policy_fixture_promotion_events_by_impact = (
    _claim_support_policy_fixture_promotion_events_by_impact
)
fixture_promotion_event_payload = _fixture_promotion_event_payload
claim_support_policy_change_impact_summary = _claim_support_policy_change_impact_summary
change_impact_payload = _change_impact_payload
