from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

import app.services.semantic_governance_context as _semantic_governance_context
import app.services.semantic_governance_core as _semantic_governance_core
from app.db.public.retrieval import SearchHarnessRelease
from app.db.public.semantic_memory import SemanticGovernanceEvent, SemanticGovernanceEventKind


def semantic_governance_event_integrity(row: SemanticGovernanceEvent) -> dict[str, Any]:
    payload_hash = _semantic_governance_core._payload_sha256(
        _semantic_governance_core._json_payload(row.event_payload_json or {})
    )
    event_hash = _semantic_governance_core._payload_sha256(
        _semantic_governance_core._event_hash_basis(
            event_id=row.id,
            event_kind=row.event_kind,
            governance_scope=row.governance_scope,
            subject_table=row.subject_table,
            subject_id=row.subject_id,
            task_id=row.task_id,
            ontology_snapshot_id=row.ontology_snapshot_id,
            semantic_graph_snapshot_id=row.semantic_graph_snapshot_id,
            search_harness_evaluation_id=row.search_harness_evaluation_id,
            search_harness_release_id=row.search_harness_release_id,
            evidence_manifest_id=row.evidence_manifest_id,
            evidence_package_export_id=row.evidence_package_export_id,
            agent_task_artifact_id=row.agent_task_artifact_id,
            previous_event_id=row.previous_event_id,
            previous_event_hash=row.previous_event_hash,
            receipt_sha256=row.receipt_sha256,
            payload_sha256=row.payload_sha256,
            deduplication_key=row.deduplication_key,
            created_by=row.created_by,
            created_at=row.created_at,
        )
    )
    return {
        "payload_hash_matches": payload_hash == row.payload_sha256,
        "expected_payload_sha256": payload_hash,
        "stored_payload_sha256": row.payload_sha256,
        "event_hash_matches": event_hash == row.event_hash,
        "expected_event_hash": event_hash,
        "stored_event_hash": row.event_hash,
        "previous_event_hash": row.previous_event_hash,
        "complete": payload_hash == row.payload_sha256 and event_hash == row.event_hash,
    }


def semantic_governance_event_payload(row: SemanticGovernanceEvent) -> dict[str, Any]:
    return {
        "event_id": str(row.id),
        "event_sequence": row.event_sequence,
        "event_kind": row.event_kind,
        "governance_scope": row.governance_scope,
        "subject_table": row.subject_table,
        "subject_id": _semantic_governance_core._uuid_text(row.subject_id),
        "task_id": _semantic_governance_core._uuid_text(row.task_id),
        "ontology_snapshot_id": _semantic_governance_core._uuid_text(row.ontology_snapshot_id),
        "semantic_graph_snapshot_id": _semantic_governance_core._uuid_text(
            row.semantic_graph_snapshot_id
        ),
        "search_harness_evaluation_id": _semantic_governance_core._uuid_text(
            row.search_harness_evaluation_id
        ),
        "search_harness_release_id": _semantic_governance_core._uuid_text(
            row.search_harness_release_id
        ),
        "evidence_manifest_id": _semantic_governance_core._uuid_text(row.evidence_manifest_id),
        "evidence_package_export_id": _semantic_governance_core._uuid_text(
            row.evidence_package_export_id
        ),
        "agent_task_artifact_id": _semantic_governance_core._uuid_text(row.agent_task_artifact_id),
        "previous_event_id": _semantic_governance_core._uuid_text(row.previous_event_id),
        "previous_event_hash": row.previous_event_hash,
        "receipt_sha256": row.receipt_sha256,
        "payload_sha256": row.payload_sha256,
        "event_hash": row.event_hash,
        "deduplication_key": row.deduplication_key,
        "created_by": row.created_by,
        "created_at": _semantic_governance_core._created_at_text(row.created_at),
        "event_payload": _semantic_governance_core._json_payload(row.event_payload_json or {}),
        "integrity": semantic_governance_event_integrity(row),
    }


def semantic_governance_chain_integrity(
    events: Iterable[SemanticGovernanceEvent],
) -> dict[str, Any]:
    rows = list(events)
    event_ids = {row.id for row in rows}
    event_hashes_by_id = {row.id: row.event_hash for row in rows}
    hash_link_mismatch_count = 0
    external_previous_event_count = 0
    for row in rows:
        if row.previous_event_id is None:
            continue
        if row.previous_event_id not in event_ids:
            external_previous_event_count += 1
            continue
        if row.previous_event_hash != event_hashes_by_id.get(row.previous_event_id):
            hash_link_mismatch_count += 1

    integrity_rows = [semantic_governance_event_integrity(row) for row in rows]
    payload_hash_mismatch_count = sum(
        1 for row in integrity_rows if not row["payload_hash_matches"]
    )
    event_hash_mismatch_count = sum(1 for row in integrity_rows if not row["event_hash_matches"])
    return {
        "has_events": bool(rows),
        "event_count": len(rows),
        "payload_hash_mismatch_count": payload_hash_mismatch_count,
        "event_hash_mismatch_count": event_hash_mismatch_count,
        "hash_link_mismatch_count": hash_link_mismatch_count,
        "external_previous_event_count": external_previous_event_count,
        "payload_hashes_verified": payload_hash_mismatch_count == 0,
        "event_hashes_verified": event_hash_mismatch_count == 0,
        "hash_links_verified": (
            hash_link_mismatch_count == 0 and external_previous_event_count == 0
        ),
        "complete": (
            bool(rows)
            and payload_hash_mismatch_count == 0
            and event_hash_mismatch_count == 0
            and hash_link_mismatch_count == 0
            and external_previous_event_count == 0
        ),
    }


def search_harness_release_semantic_governance_context(
    session: Session,
    release: SearchHarnessRelease,
) -> dict[str, Any]:
    seed_events = list(
        session.scalars(
            select(SemanticGovernanceEvent)
            .where(
                or_(
                    SemanticGovernanceEvent.search_harness_release_id == release.id,
                    (
                        (SemanticGovernanceEvent.subject_table == "search_harness_releases")
                        & (SemanticGovernanceEvent.subject_id == release.id)
                    ),
                )
            )
            .order_by(
                SemanticGovernanceEvent.event_sequence.asc(),
                SemanticGovernanceEvent.created_at.asc(),
            )
        )
    )
    events = _expand_with_previous_events(session, seed_events)
    referenced = _referenced_ids(events)
    chain_integrity = semantic_governance_chain_integrity(events)
    active_basis = _semantic_governance_context._active_semantic_basis(session)
    has_release_governance_event = any(
        row.event_kind == SemanticGovernanceEventKind.SEARCH_HARNESS_RELEASE_RECORDED.value
        and row.search_harness_release_id == release.id
        for row in events
    )
    semantic_coverage_claimed = bool(
        referenced["ontology_snapshot_ids"] or referenced["semantic_graph_snapshot_ids"]
    )
    has_ontology_snapshot_reference = bool(referenced["ontology_snapshot_ids"])
    has_semantic_graph_snapshot_reference = bool(referenced["semantic_graph_snapshot_ids"])
    checks = {
        "has_release_governance_event": has_release_governance_event,
        "payload_hashes_verified": chain_integrity["payload_hashes_verified"],
        "event_hashes_verified": chain_integrity["event_hashes_verified"],
        "hash_links_verified": chain_integrity["hash_links_verified"],
        "semantic_coverage_claimed": semantic_coverage_claimed,
        "has_ontology_snapshot_reference": has_ontology_snapshot_reference,
        "has_semantic_graph_snapshot_reference": has_semantic_graph_snapshot_reference,
    }
    checks["complete"] = (
        checks["has_release_governance_event"]
        and checks["payload_hashes_verified"]
        and checks["event_hashes_verified"]
        and checks["hash_links_verified"]
        and (
            not semantic_coverage_claimed
            or (
                checks["has_ontology_snapshot_reference"]
                and checks["has_semantic_graph_snapshot_reference"]
            )
        )
    )
    policy = {
        "schema_name": _semantic_governance_core.SEARCH_HARNESS_RELEASE_SEMANTIC_POLICY_SCHEMA,
        "schema_version": "1.0",
        "policy_profile": _semantic_governance_core.SEARCH_HARNESS_RELEASE_SEMANTIC_POLICY_PROFILE,
        "release_id": str(release.id),
        "candidate_harness_name": release.candidate_harness_name,
        "semantic_coverage_claimed": semantic_coverage_claimed,
        "requirements": {
            "release_governance_event_required": True,
            "governance_event_hash_chain_required": True,
            "ontology_snapshot_required_when_claimed": True,
            "semantic_graph_snapshot_required_when_claimed": True,
        },
        "active_semantic_basis": active_basis,
        "referenced_ids": {
            "ontology_snapshot_ids": [
                str(value) for value in sorted(referenced["ontology_snapshot_ids"], key=str)
            ],
            "semantic_graph_snapshot_ids": [
                str(value) for value in sorted(referenced["semantic_graph_snapshot_ids"], key=str)
            ],
            "search_harness_release_ids": [
                str(value) for value in sorted(referenced["search_harness_release_ids"], key=str)
            ],
        },
        "event_ids": [str(row.id) for row in events],
        "event_kinds": [row.event_kind for row in events],
        "event_count": len(events),
        "chain_integrity": chain_integrity,
        "checks": checks,
        "complete": checks["complete"],
    }
    return {
        "events": events,
        "event_payloads": [semantic_governance_event_payload(row) for row in events],
        "policy": policy,
    }


def _event_sort_key(row: SemanticGovernanceEvent) -> tuple[str, int, str]:
    return (
        _semantic_governance_core._created_at_text(row.created_at) or "",
        row.event_sequence or 0,
        str(row.id),
    )


def _expand_with_previous_events(
    session: Session,
    events: Iterable[SemanticGovernanceEvent],
) -> list[SemanticGovernanceEvent]:
    events_by_id = {row.id: row for row in events}
    pending_ids = {
        row.previous_event_id
        for row in events_by_id.values()
        if row.previous_event_id is not None and row.previous_event_id not in events_by_id
    }
    while pending_ids:
        previous_events = list(
            session.scalars(
                select(SemanticGovernanceEvent).where(SemanticGovernanceEvent.id.in_(pending_ids))
            )
        )
        fetched_ids = {row.id for row in previous_events}
        for row in previous_events:
            events_by_id.setdefault(row.id, row)
        pending_ids = {
            row.previous_event_id
            for row in previous_events
            if row.previous_event_id is not None and row.previous_event_id not in events_by_id
        }
        if not fetched_ids:
            break
    return sorted(events_by_id.values(), key=_event_sort_key)


def _referenced_ids(events: list[SemanticGovernanceEvent]) -> dict[str, set[UUID]]:
    ontology_ids = {row.ontology_snapshot_id for row in events if row.ontology_snapshot_id}
    graph_ids = {row.semantic_graph_snapshot_id for row in events if row.semantic_graph_snapshot_id}
    release_ids = {row.search_harness_release_id for row in events if row.search_harness_release_id}
    for row in events:
        payload = row.event_payload_json or {}
        semantic_basis = payload.get("semantic_basis") or {}
        retrieval_basis = payload.get("retrieval_basis") or {}
        for key, target in (
            ("active_ontology_snapshot_id", ontology_ids),
            ("active_semantic_graph_snapshot_id", graph_ids),
        ):
            parsed = _semantic_governance_core._uuid_or_none(semantic_basis.get(key))
            if parsed is not None:
                target.add(parsed)
        for release_id in (
            retrieval_basis.get("latest_passed_search_harness_release_ids_by_harness") or {}
        ).values():
            parsed = _semantic_governance_core._uuid_or_none(release_id)
            if parsed is not None:
                release_ids.add(parsed)
    return {
        "ontology_snapshot_ids": ontology_ids,
        "semantic_graph_snapshot_ids": graph_ids,
        "search_harness_release_ids": release_ids,
    }


def semantic_governance_chain_for_audit(
    session: Session,
    *,
    task_ids: Iterable[UUID],
    artifact_ids: Iterable[UUID],
    evidence_manifest_ids: Iterable[UUID],
    receipt_sha256s: Iterable[str],
) -> dict[str, Any]:
    task_id_list = list(dict.fromkeys(task_ids))
    artifact_id_list = list(dict.fromkeys(artifact_ids))
    evidence_manifest_id_list = list(dict.fromkeys(evidence_manifest_ids))
    receipt_sha256_list = [value for value in dict.fromkeys(receipt_sha256s) if value]
    criteria = []
    if task_id_list:
        criteria.append(SemanticGovernanceEvent.task_id.in_(task_id_list))
    if artifact_id_list:
        criteria.append(SemanticGovernanceEvent.agent_task_artifact_id.in_(artifact_id_list))
    if evidence_manifest_id_list:
        criteria.append(SemanticGovernanceEvent.evidence_manifest_id.in_(evidence_manifest_id_list))
    if receipt_sha256_list:
        criteria.append(SemanticGovernanceEvent.receipt_sha256.in_(receipt_sha256_list))
    if not criteria:
        events: list[SemanticGovernanceEvent] = []
    else:
        events = list(
            session.scalars(
                select(SemanticGovernanceEvent)
                .where(or_(*criteria))
                .order_by(
                    SemanticGovernanceEvent.created_at.asc(),
                    SemanticGovernanceEvent.event_sequence.asc(),
                )
            )
        )

    referenced = _referenced_ids(events)
    extra_criteria = []
    if referenced["ontology_snapshot_ids"]:
        extra_criteria.append(
            SemanticGovernanceEvent.ontology_snapshot_id.in_(referenced["ontology_snapshot_ids"])
        )
    if referenced["semantic_graph_snapshot_ids"]:
        extra_criteria.append(
            SemanticGovernanceEvent.semantic_graph_snapshot_id.in_(
                referenced["semantic_graph_snapshot_ids"]
            )
        )
    if referenced["search_harness_release_ids"]:
        extra_criteria.append(
            SemanticGovernanceEvent.search_harness_release_id.in_(
                referenced["search_harness_release_ids"]
            )
        )
    if extra_criteria:
        extra_events = list(
            session.scalars(
                select(SemanticGovernanceEvent)
                .where(or_(*extra_criteria))
                .order_by(
                    SemanticGovernanceEvent.created_at.asc(),
                    SemanticGovernanceEvent.event_sequence.asc(),
                )
            )
        )
        events_by_id = {row.id: row for row in events}
        for row in extra_events:
            events_by_id.setdefault(row.id, row)
        events = sorted(events_by_id.values(), key=_event_sort_key)
    events = _expand_with_previous_events(session, events)

    event_payloads = [semantic_governance_event_payload(row) for row in events]
    event_ids = {row.id for row in events}
    event_hashes_by_id = {row.id: row.event_hash for row in events}
    hash_link_mismatch_count = 0
    external_previous_event_count = 0
    for row in events:
        if row.previous_event_id is None:
            continue
        if row.previous_event_id not in event_ids:
            external_previous_event_count += 1
            continue
        if row.previous_event_hash != event_hashes_by_id.get(row.previous_event_id):
            hash_link_mismatch_count += 1

    integrity_rows = [payload["integrity"] for payload in event_payloads]
    payload_hash_mismatch_count = sum(
        1 for row in integrity_rows if not row["payload_hash_matches"]
    )
    event_hash_mismatch_count = sum(1 for row in integrity_rows if not row["event_hash_matches"])
    has_report_prov_event = any(
        row.event_kind == SemanticGovernanceEventKind.TECHNICAL_REPORT_PROV_EXPORT_FROZEN.value
        for row in events
    )
    report_change_impacts = [
        (row.event_payload_json or {}).get("change_impact") or {}
        for row in events
        if row.event_kind == SemanticGovernanceEventKind.TECHNICAL_REPORT_PROV_EXPORT_FROZEN.value
    ]
    evaluated_change_impact_count = sum(
        1 for row in report_change_impacts if isinstance(row.get("impacted"), bool)
    )
    impacted_report_event_count = sum(
        1 for row in report_change_impacts if row.get("impacted") is True
    )
    links_requested_receipt = bool(receipt_sha256_list) and any(
        row.receipt_sha256 in receipt_sha256_list for row in events
    )
    integrity = {
        "has_events": bool(events),
        "has_technical_report_prov_export_event": has_report_prov_event,
        "links_requested_prov_receipt": links_requested_receipt,
        "change_impact_evaluated": (
            has_report_prov_event and evaluated_change_impact_count == len(report_change_impacts)
        ),
        "change_impact_clear": (
            has_report_prov_event
            and evaluated_change_impact_count == len(report_change_impacts)
            and impacted_report_event_count == 0
        ),
        "report_event_count": len(report_change_impacts),
        "evaluated_change_impact_count": evaluated_change_impact_count,
        "impacted_report_event_count": impacted_report_event_count,
        "payload_hash_mismatch_count": payload_hash_mismatch_count,
        "event_hash_mismatch_count": event_hash_mismatch_count,
        "hash_link_mismatch_count": hash_link_mismatch_count,
        "external_previous_event_count": external_previous_event_count,
        "payload_hashes_verified": payload_hash_mismatch_count == 0,
        "event_hashes_verified": event_hash_mismatch_count == 0,
        "hash_links_verified": (
            hash_link_mismatch_count == 0 and external_previous_event_count == 0
        ),
    }
    integrity["complete"] = (
        integrity["has_events"]
        and integrity["has_technical_report_prov_export_event"]
        and integrity["links_requested_prov_receipt"]
        and integrity["change_impact_evaluated"]
        and integrity["payload_hashes_verified"]
        and integrity["event_hashes_verified"]
        and integrity["hash_links_verified"]
    )
    return {
        "schema_name": _semantic_governance_core.SEMANTIC_GOVERNANCE_CHAIN_SCHEMA,
        "schema_version": "1.0",
        "event_count": len(event_payloads),
        "events": event_payloads,
        "referenced_ids": {
            "ontology_snapshot_ids": [
                str(value) for value in sorted(referenced["ontology_snapshot_ids"], key=str)
            ],
            "semantic_graph_snapshot_ids": [
                str(value) for value in sorted(referenced["semantic_graph_snapshot_ids"], key=str)
            ],
            "search_harness_release_ids": [
                str(value) for value in sorted(referenced["search_harness_release_ids"], key=str)
            ],
        },
        "integrity": integrity,
    }
