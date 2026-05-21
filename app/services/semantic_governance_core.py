from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import uuid_or_none as _uuid_or_none
from app.core.coercion import uuid_text as _uuid_text
from app.core.hashes import payload_sha256 as _payload_sha256
from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import coerce_utc_datetime, utcnow
from app.db.public.semantic_memory import SemanticGovernanceEvent

WORKSPACE_SEMANTIC_SCOPE = "workspace:default"
WORKSPACE_SEMANTIC_STATE_KEY = "default"
WORKSPACE_SEMANTIC_GRAPH_STATE_KEY = "default"
SEMANTIC_GOVERNANCE_EVENT_SCHEMA = "semantic_governance_event"
SEMANTIC_GOVERNANCE_CHAIN_SCHEMA = "semantic_governance_chain"
SEARCH_HARNESS_RELEASE_SEMANTIC_POLICY_SCHEMA = (
    "search_harness_release_semantic_governance_policy"
)
SEARCH_HARNESS_RELEASE_SEMANTIC_POLICY_PROFILE = "release_semantic_governance_v1"


def _created_at_text(value: Any) -> str | None:
    if value is None:
        return None
    if (coerced := coerce_utc_datetime(value)) is not None:
        return coerced.isoformat()
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


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

