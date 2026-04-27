from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import (
    AgentTaskArtifact,
    EvidenceManifest,
    SearchHarnessRelease,
    SearchRequestRecord,
    SemanticGovernanceEvent,
    SemanticGovernanceEventKind,
    SemanticGraphSnapshot,
    SemanticOntologySnapshot,
    WorkspaceSemanticGraphState,
    WorkspaceSemanticState,
)

WORKSPACE_SEMANTIC_SCOPE = "workspace:default"
WORKSPACE_SEMANTIC_STATE_KEY = "default"
WORKSPACE_SEMANTIC_GRAPH_STATE_KEY = "default"
SEMANTIC_GOVERNANCE_EVENT_SCHEMA = "semantic_governance_event"
SEMANTIC_GOVERNANCE_CHAIN_SCHEMA = "semantic_governance_chain"


def _json_payload(payload: Any | None) -> dict:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        value = payload
    else:
        value = {"value": payload}
    return json.loads(json.dumps(value, default=str, sort_keys=True))


def _payload_sha256(payload: Any | None) -> str:
    encoded = json.dumps(
        payload if payload is not None else {},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _uuid_text(value: UUID | None) -> str | None:
    return str(value) if value is not None else None


def _created_at_text(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _uuid_or_none(value: Any | None) -> UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _uuids(values: Iterable[Any] | None) -> list[UUID]:
    resolved: list[UUID] = []
    for value in values or []:
        parsed = _uuid_or_none(value)
        if parsed is not None:
            resolved.append(parsed)
    return list(dict.fromkeys(resolved))


def _event_hash_basis(
    *,
    event_id: UUID,
    event_kind: str,
    governance_scope: str,
    subject_table: str,
    subject_id: UUID | None,
    task_id: UUID | None,
    ontology_snapshot_id: UUID | None,
    semantic_graph_snapshot_id: UUID | None,
    search_harness_evaluation_id: UUID | None,
    search_harness_release_id: UUID | None,
    evidence_manifest_id: UUID | None,
    evidence_package_export_id: UUID | None,
    agent_task_artifact_id: UUID | None,
    previous_event_id: UUID | None,
    previous_event_hash: str | None,
    receipt_sha256: str | None,
    payload_sha256: str,
    deduplication_key: str,
    created_by: str | None,
    created_at: Any,
) -> dict:
    return _json_payload(
        {
            "schema_name": "semantic_governance_event_hash_basis",
            "schema_version": "1.0",
            "event_id": str(event_id),
            "event_kind": event_kind,
            "governance_scope": governance_scope,
            "subject_table": subject_table,
            "subject_id": _uuid_text(subject_id),
            "task_id": _uuid_text(task_id),
            "ontology_snapshot_id": _uuid_text(ontology_snapshot_id),
            "semantic_graph_snapshot_id": _uuid_text(semantic_graph_snapshot_id),
            "search_harness_evaluation_id": _uuid_text(search_harness_evaluation_id),
            "search_harness_release_id": _uuid_text(search_harness_release_id),
            "evidence_manifest_id": _uuid_text(evidence_manifest_id),
            "evidence_package_export_id": _uuid_text(evidence_package_export_id),
            "agent_task_artifact_id": _uuid_text(agent_task_artifact_id),
            "previous_event_id": _uuid_text(previous_event_id),
            "previous_event_hash": previous_event_hash,
            "receipt_sha256": receipt_sha256,
            "payload_sha256": payload_sha256,
            "deduplication_key": deduplication_key,
            "created_by": created_by,
            "created_at": _created_at_text(created_at),
        }
    )


def _latest_scope_event(session: Session, governance_scope: str) -> SemanticGovernanceEvent | None:
    return session.scalar(
        select(SemanticGovernanceEvent)
        .where(SemanticGovernanceEvent.governance_scope == governance_scope)
        .order_by(
            SemanticGovernanceEvent.event_sequence.desc(),
            SemanticGovernanceEvent.created_at.desc(),
        )
        .limit(1)
    )


def record_semantic_governance_event(
    session: Session,
    *,
    event_kind: str,
    governance_scope: str,
    subject_table: str,
    subject_id: UUID | None,
    event_payload: dict[str, Any],
    deduplication_key: str,
    task_id: UUID | None = None,
    ontology_snapshot_id: UUID | None = None,
    semantic_graph_snapshot_id: UUID | None = None,
    search_harness_evaluation_id: UUID | None = None,
    search_harness_release_id: UUID | None = None,
    evidence_manifest_id: UUID | None = None,
    evidence_package_export_id: UUID | None = None,
    agent_task_artifact_id: UUID | None = None,
    receipt_sha256: str | None = None,
    created_by: str | None = None,
) -> SemanticGovernanceEvent:
    existing = session.scalar(
        select(SemanticGovernanceEvent)
        .where(SemanticGovernanceEvent.deduplication_key == deduplication_key)
        .limit(1)
    )
    if existing is not None:
        return existing

    previous = _latest_scope_event(session, governance_scope)
    event_id = uuid.uuid4()
    created_at = utcnow()
    normalized_payload = _json_payload(
        {
            "schema_name": SEMANTIC_GOVERNANCE_EVENT_SCHEMA,
            "schema_version": "1.0",
            **_json_payload(event_payload),
        }
    )
    payload_hash = _payload_sha256(normalized_payload)
    previous_event_id = previous.id if previous is not None else None
    previous_event_hash = previous.event_hash if previous is not None else None
    event_hash = _payload_sha256(
        _event_hash_basis(
            event_id=event_id,
            event_kind=event_kind,
            governance_scope=governance_scope,
            subject_table=subject_table,
            subject_id=subject_id,
            task_id=task_id,
            ontology_snapshot_id=ontology_snapshot_id,
            semantic_graph_snapshot_id=semantic_graph_snapshot_id,
            search_harness_evaluation_id=search_harness_evaluation_id,
            search_harness_release_id=search_harness_release_id,
            evidence_manifest_id=evidence_manifest_id,
            evidence_package_export_id=evidence_package_export_id,
            agent_task_artifact_id=agent_task_artifact_id,
            previous_event_id=previous_event_id,
            previous_event_hash=previous_event_hash,
            receipt_sha256=receipt_sha256,
            payload_sha256=payload_hash,
            deduplication_key=deduplication_key,
            created_by=created_by,
            created_at=created_at,
        )
    )
    event = SemanticGovernanceEvent(
        id=event_id,
        event_kind=event_kind,
        governance_scope=governance_scope,
        subject_table=subject_table,
        subject_id=subject_id,
        task_id=task_id,
        ontology_snapshot_id=ontology_snapshot_id,
        semantic_graph_snapshot_id=semantic_graph_snapshot_id,
        search_harness_evaluation_id=search_harness_evaluation_id,
        search_harness_release_id=search_harness_release_id,
        evidence_manifest_id=evidence_manifest_id,
        evidence_package_export_id=evidence_package_export_id,
        agent_task_artifact_id=agent_task_artifact_id,
        previous_event_id=previous_event_id,
        previous_event_hash=previous_event_hash,
        receipt_sha256=receipt_sha256,
        payload_sha256=payload_hash,
        event_hash=event_hash,
        deduplication_key=deduplication_key,
        event_payload_json=normalized_payload,
        created_by=created_by,
        created_at=created_at,
    )
    session.add(event)
    session.flush()
    return event


def record_ontology_snapshot_governance_events(
    session: Session,
    snapshot: SemanticOntologySnapshot,
    *,
    activated: bool,
) -> list[SemanticGovernanceEvent]:
    payload = {
        "ontology_snapshot": {
            "ontology_snapshot_id": str(snapshot.id),
            "ontology_name": snapshot.ontology_name,
            "ontology_version": snapshot.ontology_version,
            "upper_ontology_version": snapshot.upper_ontology_version,
            "source_kind": snapshot.source_kind,
            "source_task_id": _uuid_text(snapshot.source_task_id),
            "source_task_type": snapshot.source_task_type,
            "parent_snapshot_id": _uuid_text(snapshot.parent_snapshot_id),
            "sha256": snapshot.sha256,
            "activated_at": _created_at_text(snapshot.activated_at),
        }
    }
    events = [
        record_semantic_governance_event(
            session,
            event_kind=SemanticGovernanceEventKind.ONTOLOGY_SNAPSHOT_RECORDED.value,
            governance_scope=WORKSPACE_SEMANTIC_SCOPE,
            subject_table="semantic_ontology_snapshots",
            subject_id=snapshot.id,
            task_id=snapshot.source_task_id,
            ontology_snapshot_id=snapshot.id,
            event_payload=payload,
            deduplication_key=f"ontology_snapshot_recorded:{snapshot.id}:{snapshot.sha256}",
            created_by=snapshot.source_task_type,
        )
    ]
    if activated:
        events.append(
            record_semantic_governance_event(
                session,
                event_kind=SemanticGovernanceEventKind.ONTOLOGY_SNAPSHOT_ACTIVATED.value,
                governance_scope=WORKSPACE_SEMANTIC_SCOPE,
                subject_table="semantic_ontology_snapshots",
                subject_id=snapshot.id,
                task_id=snapshot.source_task_id,
                ontology_snapshot_id=snapshot.id,
                event_payload={
                    **payload,
                    "workspace_state": {
                        "workspace_key": WORKSPACE_SEMANTIC_STATE_KEY,
                        "active_ontology_snapshot_id": str(snapshot.id),
                    },
                },
                deduplication_key=f"ontology_snapshot_activated:{snapshot.id}:{snapshot.sha256}",
                created_by=snapshot.source_task_type,
            )
        )
    return events


def record_semantic_graph_snapshot_governance_events(
    session: Session,
    snapshot: SemanticGraphSnapshot,
    *,
    activated: bool,
) -> list[SemanticGovernanceEvent]:
    payload = {
        "semantic_graph_snapshot": {
            "semantic_graph_snapshot_id": str(snapshot.id),
            "graph_name": snapshot.graph_name,
            "graph_version": snapshot.graph_version,
            "ontology_snapshot_id": _uuid_text(snapshot.ontology_snapshot_id),
            "source_kind": snapshot.source_kind,
            "source_task_id": _uuid_text(snapshot.source_task_id),
            "source_task_type": snapshot.source_task_type,
            "parent_snapshot_id": _uuid_text(snapshot.parent_snapshot_id),
            "sha256": snapshot.sha256,
            "activated_at": _created_at_text(snapshot.activated_at),
        }
    }
    events = [
        record_semantic_governance_event(
            session,
            event_kind=SemanticGovernanceEventKind.SEMANTIC_GRAPH_SNAPSHOT_RECORDED.value,
            governance_scope=WORKSPACE_SEMANTIC_SCOPE,
            subject_table="semantic_graph_snapshots",
            subject_id=snapshot.id,
            task_id=snapshot.source_task_id,
            ontology_snapshot_id=snapshot.ontology_snapshot_id,
            semantic_graph_snapshot_id=snapshot.id,
            event_payload=payload,
            deduplication_key=f"semantic_graph_snapshot_recorded:{snapshot.id}:{snapshot.sha256}",
            created_by=snapshot.source_task_type,
        )
    ]
    if activated:
        events.append(
            record_semantic_governance_event(
                session,
                event_kind=SemanticGovernanceEventKind.SEMANTIC_GRAPH_SNAPSHOT_ACTIVATED.value,
                governance_scope=WORKSPACE_SEMANTIC_SCOPE,
                subject_table="semantic_graph_snapshots",
                subject_id=snapshot.id,
                task_id=snapshot.source_task_id,
                ontology_snapshot_id=snapshot.ontology_snapshot_id,
                semantic_graph_snapshot_id=snapshot.id,
                event_payload={
                    **payload,
                    "workspace_graph_state": {
                        "workspace_key": WORKSPACE_SEMANTIC_GRAPH_STATE_KEY,
                        "active_graph_snapshot_id": str(snapshot.id),
                    },
                },
                deduplication_key=f"semantic_graph_snapshot_activated:{snapshot.id}:{snapshot.sha256}",
                created_by=snapshot.source_task_type,
            )
        )
    return events


def record_search_harness_release_governance_event(
    session: Session,
    release: SearchHarnessRelease,
) -> SemanticGovernanceEvent:
    return record_semantic_governance_event(
        session,
        event_kind=SemanticGovernanceEventKind.SEARCH_HARNESS_RELEASE_RECORDED.value,
        governance_scope=f"search_harness:{release.candidate_harness_name}",
        subject_table="search_harness_releases",
        subject_id=release.id,
        search_harness_evaluation_id=release.search_harness_evaluation_id,
        search_harness_release_id=release.id,
        event_payload={
            "search_harness_release": {
                "search_harness_release_id": str(release.id),
                "search_harness_evaluation_id": str(release.search_harness_evaluation_id),
                "outcome": release.outcome,
                "baseline_harness_name": release.baseline_harness_name,
                "candidate_harness_name": release.candidate_harness_name,
                "source_types": list(release.source_types_json or []),
                "metrics": release.metrics_json or {},
                "thresholds": release.thresholds_json or {},
                "release_package_sha256": release.release_package_sha256,
                "created_by": release.requested_by,
                "review_note": release.review_note,
            }
        },
        deduplication_key=f"search_harness_release_recorded:{release.id}",
        created_by=release.requested_by,
    )


def _active_semantic_basis(session: Session) -> dict[str, Any]:
    ontology_state = session.get(WorkspaceSemanticState, WORKSPACE_SEMANTIC_STATE_KEY)
    graph_state = session.get(WorkspaceSemanticGraphState, WORKSPACE_SEMANTIC_GRAPH_STATE_KEY)
    ontology_snapshot = (
        session.get(SemanticOntologySnapshot, ontology_state.active_ontology_snapshot_id)
        if ontology_state is not None and ontology_state.active_ontology_snapshot_id is not None
        else None
    )
    graph_snapshot = (
        session.get(SemanticGraphSnapshot, graph_state.active_graph_snapshot_id)
        if graph_state is not None and graph_state.active_graph_snapshot_id is not None
        else None
    )
    return {
        "workspace_key": WORKSPACE_SEMANTIC_STATE_KEY,
        "active_ontology_snapshot_id": (
            str(ontology_snapshot.id) if ontology_snapshot is not None else None
        ),
        "active_ontology_version": (
            ontology_snapshot.ontology_version if ontology_snapshot is not None else None
        ),
        "active_ontology_sha256": (
            ontology_snapshot.sha256 if ontology_snapshot is not None else None
        ),
        "active_semantic_graph_snapshot_id": (
            str(graph_snapshot.id) if graph_snapshot is not None else None
        ),
        "active_semantic_graph_version": (
            graph_snapshot.graph_version if graph_snapshot is not None else None
        ),
        "active_semantic_graph_sha256": (
            graph_snapshot.sha256 if graph_snapshot is not None else None
        ),
    }


def _search_requests_for_manifest(
    session: Session,
    manifest: EvidenceManifest | None,
) -> list[SearchRequestRecord]:
    search_request_ids = _uuids(manifest.search_request_ids_json if manifest is not None else [])
    if not search_request_ids:
        return []
    return list(
        session.scalars(
            select(SearchRequestRecord)
            .where(SearchRequestRecord.id.in_(search_request_ids))
            .order_by(SearchRequestRecord.created_at.asc())
        )
    )


def _latest_passed_releases_by_harness(
    session: Session,
    harness_names: Iterable[str],
) -> dict[str, str]:
    releases: dict[str, str] = {}
    for harness_name in sorted({name for name in harness_names if name}):
        release = session.scalar(
            select(SearchHarnessRelease)
            .where(
                SearchHarnessRelease.candidate_harness_name == harness_name,
                SearchHarnessRelease.outcome == "passed",
            )
            .order_by(SearchHarnessRelease.created_at.desc())
            .limit(1)
        )
        if release is not None:
            releases[harness_name] = str(release.id)
    return releases


def record_technical_report_prov_export_governance_event(
    session: Session,
    *,
    artifact: AgentTaskArtifact,
    evidence_manifest: EvidenceManifest | None,
    change_impact: dict[str, Any] | None = None,
) -> SemanticGovernanceEvent:
    artifact_payload = _json_payload(artifact.payload_json or {})
    frozen_export = artifact_payload.get("frozen_export") or {}
    receipt = frozen_export.get("export_receipt") or {}
    semantic_basis = _active_semantic_basis(session)
    search_requests = _search_requests_for_manifest(session, evidence_manifest)
    harness_names = sorted({row.harness_name for row in search_requests})
    latest_release_ids_by_harness = _latest_passed_releases_by_harness(session, harness_names)
    ontology_snapshot_id = _uuid_or_none(semantic_basis.get("active_ontology_snapshot_id"))
    graph_snapshot_id = _uuid_or_none(semantic_basis.get("active_semantic_graph_snapshot_id"))
    evidence_manifest_id = evidence_manifest.id if evidence_manifest is not None else None
    evidence_package_export_id = (
        evidence_manifest.evidence_package_export_id if evidence_manifest is not None else None
    )
    return record_semantic_governance_event(
        session,
        event_kind=SemanticGovernanceEventKind.TECHNICAL_REPORT_PROV_EXPORT_FROZEN.value,
        governance_scope=f"agent_task:{artifact.task_id}",
        subject_table="agent_task_artifacts",
        subject_id=artifact.id,
        task_id=artifact.task_id,
        ontology_snapshot_id=ontology_snapshot_id,
        semantic_graph_snapshot_id=graph_snapshot_id,
        evidence_manifest_id=evidence_manifest_id,
        evidence_package_export_id=evidence_package_export_id,
        agent_task_artifact_id=artifact.id,
        receipt_sha256=receipt.get("receipt_sha256"),
        event_payload={
            "technical_report_prov_export": {
                "artifact_id": str(artifact.id),
                "artifact_kind": artifact.artifact_kind,
                "task_id": str(artifact.task_id),
                "storage_path": artifact.storage_path,
                "export_payload_sha256": frozen_export.get("export_payload_sha256"),
                "prov_hash_basis_sha256": frozen_export.get("prov_hash_basis_sha256"),
                "receipt_sha256": receipt.get("receipt_sha256"),
                "receipt_signature_status": receipt.get("signature_status"),
                "receipt_signing_key_id": receipt.get("signing_key_id"),
            },
            "evidence_manifest": {
                "evidence_manifest_id": (
                    str(evidence_manifest.id) if evidence_manifest is not None else None
                ),
                "manifest_sha256": (
                    evidence_manifest.manifest_sha256 if evidence_manifest is not None else None
                ),
                "trace_sha256": (
                    evidence_manifest.trace_sha256 if evidence_manifest is not None else None
                ),
                "evidence_package_export_id": (
                    str(evidence_package_export_id)
                    if evidence_package_export_id is not None
                    else None
                ),
                "search_request_ids": (
                    list(evidence_manifest.search_request_ids_json or [])
                    if evidence_manifest is not None
                    else []
                ),
            },
            "semantic_basis": semantic_basis,
            "retrieval_basis": {
                "search_request_count": len(search_requests),
                "search_request_ids": [str(row.id) for row in search_requests],
                "harness_names": harness_names,
                "retrieval_profile_names": sorted(
                    {row.retrieval_profile_name for row in search_requests}
                ),
                "rerankers": sorted(
                    {
                        f"{row.reranker_name}:{row.reranker_version}"
                        for row in search_requests
                    }
                ),
                "latest_passed_search_harness_release_ids_by_harness": (
                    latest_release_ids_by_harness
                ),
            },
            "change_impact": change_impact or {"status": "not_evaluated_at_freeze"},
        },
        deduplication_key=(
            f"technical_report_prov_export_frozen:{artifact.id}:"
            f"{receipt.get('receipt_sha256') or frozen_export.get('export_payload_sha256')}"
        ),
        created_by="technical_report_verification",
    )


def semantic_governance_event_integrity(row: SemanticGovernanceEvent) -> dict[str, Any]:
    payload_hash = _payload_sha256(_json_payload(row.event_payload_json or {}))
    event_hash = _payload_sha256(
        _event_hash_basis(
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
        "subject_id": _uuid_text(row.subject_id),
        "task_id": _uuid_text(row.task_id),
        "ontology_snapshot_id": _uuid_text(row.ontology_snapshot_id),
        "semantic_graph_snapshot_id": _uuid_text(row.semantic_graph_snapshot_id),
        "search_harness_evaluation_id": _uuid_text(row.search_harness_evaluation_id),
        "search_harness_release_id": _uuid_text(row.search_harness_release_id),
        "evidence_manifest_id": _uuid_text(row.evidence_manifest_id),
        "evidence_package_export_id": _uuid_text(row.evidence_package_export_id),
        "agent_task_artifact_id": _uuid_text(row.agent_task_artifact_id),
        "previous_event_id": _uuid_text(row.previous_event_id),
        "previous_event_hash": row.previous_event_hash,
        "receipt_sha256": row.receipt_sha256,
        "payload_sha256": row.payload_sha256,
        "event_hash": row.event_hash,
        "deduplication_key": row.deduplication_key,
        "created_by": row.created_by,
        "created_at": _created_at_text(row.created_at),
        "event_payload": _json_payload(row.event_payload_json or {}),
        "integrity": semantic_governance_event_integrity(row),
    }


def _event_sort_key(row: SemanticGovernanceEvent) -> tuple[str, int, str]:
    return (
        _created_at_text(row.created_at) or "",
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
                select(SemanticGovernanceEvent).where(
                    SemanticGovernanceEvent.id.in_(pending_ids)
                )
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
    release_ids = {
        row.search_harness_release_id for row in events if row.search_harness_release_id
    }
    for row in events:
        payload = row.event_payload_json or {}
        semantic_basis = payload.get("semantic_basis") or {}
        retrieval_basis = payload.get("retrieval_basis") or {}
        for key, target in (
            ("active_ontology_snapshot_id", ontology_ids),
            ("active_semantic_graph_snapshot_id", graph_ids),
        ):
            parsed = _uuid_or_none(semantic_basis.get(key))
            if parsed is not None:
                target.add(parsed)
        for release_id in (
            retrieval_basis.get("latest_passed_search_harness_release_ids_by_harness")
            or {}
        ).values():
            parsed = _uuid_or_none(release_id)
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
            SemanticGovernanceEvent.ontology_snapshot_id.in_(
                referenced["ontology_snapshot_ids"]
            )
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
            has_report_prov_event
            and evaluated_change_impact_count == len(report_change_impacts)
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
        "schema_name": SEMANTIC_GOVERNANCE_CHAIN_SCHEMA,
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
