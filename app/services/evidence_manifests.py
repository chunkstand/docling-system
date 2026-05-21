# ruff: noqa: E501, F401, I001
from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTask
from app.db.public.audit_and_evidence import EvidenceManifest, TechnicalReportReleaseReadinessDbGate
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import trace_edge_row_payload as _trace_edge_row_payload
from app.services.evidence_common import trace_node_row_payload as _trace_node_row_payload
from app.services.evidence_constants import TECHNICAL_REPORT_EVIDENCE_MANIFEST_KIND
from app.services.evidence_manifest_payloads import (
    build_technical_report_evidence_manifest_payload as _build_technical_report_evidence_manifest_payload,
)
from app.services.evidence_manifest_traces import (
    evidence_trace_integrity_payload as _evidence_trace_integrity_payload,
    evidence_trace_rows as _evidence_trace_rows,
    persist_evidence_trace_graph as _persist_evidence_trace_graph,
)
from app.services.evidence_technical_report_context import verification_task_id_for_manifest as _verification_task_id_for_manifest
from app.services.evidence_claim_feedback import (
    persist_technical_report_claim_retrieval_feedback_ledger,
)
from app.services.evidence_audit_views import (
    persist_technical_report_release_readiness_db_gate,
)
from app.services.evidence_common import uuid_or_none_safe as _uuid_or_none_safe
from app.core.coercion import uuid_or_none as _uuid_or_none
from app.services.evidence_semantic_trace import technical_report_integrity_payload as _technical_report_integrity_payload

def _existing_evidence_manifest(
    session: Session,
    verification_task_id: UUID,
) -> EvidenceManifest | None:
    return session.scalar(
        select(EvidenceManifest)
        .where(
            EvidenceManifest.verification_task_id == verification_task_id,
            EvidenceManifest.manifest_kind == TECHNICAL_REPORT_EVIDENCE_MANIFEST_KIND,
        )
        .order_by(EvidenceManifest.created_at.desc())
    )

def build_technical_report_evidence_manifest_payload(
    session: Session,
    task_id: UUID,
) -> dict[str, Any]:
    return _build_technical_report_evidence_manifest_payload(session, task_id)


def _evidence_manifest_integrity_payload(
    session: Session,
    row: EvidenceManifest,
) -> dict[str, Any]:
    stored_payload = row.manifest_payload_json or {}
    stored_payload_sha256 = payload_sha256(stored_payload)
    recomputed_manifest_sha256 = None
    recomputation_error = None
    try:
        recomputed_payload = build_technical_report_evidence_manifest_payload(
            session,
            row.verification_task_id,
        )
        recomputed_manifest_sha256 = payload_sha256(recomputed_payload)
    except ValueError as exc:
        recomputation_error = str(exc)

    stored_payload_hash_matches = stored_payload_sha256 == row.manifest_sha256
    recomputed_manifest_hash_matches = recomputed_manifest_sha256 == row.manifest_sha256
    stored_payload_matches_recomputed = (
        stored_payload_sha256 == recomputed_manifest_sha256
        if recomputed_manifest_sha256 is not None
        else False
    )
    return {
        "stored_manifest_sha256": row.manifest_sha256,
        "stored_payload_sha256": stored_payload_sha256,
        "recomputed_manifest_sha256": recomputed_manifest_sha256,
        "stored_payload_hash_matches": stored_payload_hash_matches,
        "recomputed_manifest_hash_matches": recomputed_manifest_hash_matches,
        "stored_payload_matches_recomputed": stored_payload_matches_recomputed,
        "recomputation_error": recomputation_error,
        "manifest_status": row.manifest_status,
        "complete": (
            row.manifest_status == "completed"
            and stored_payload_hash_matches
            and recomputed_manifest_hash_matches
            and stored_payload_matches_recomputed
        ),
    }


def _evidence_manifest_response(session: Session, row: EvidenceManifest) -> dict[str, Any]:
    return {
        **(row.manifest_payload_json or {}),
        "evidence_manifest_id": str(row.id),
        "manifest_sha256": row.manifest_sha256,
        "trace_sha256": row.trace_sha256,
        "manifest_status": row.manifest_status,
        "created_at": row.created_at,
        "manifest_integrity": _evidence_manifest_integrity_payload(session, row),
    }


def _evidence_manifest_row_from_payload(
    *,
    verification_task_id: UUID,
    payload: dict[str, Any],
    manifest_sha256: str,
) -> EvidenceManifest:
    evidence_exports = payload["report_trace"]["evidence_package_exports"]
    return EvidenceManifest(
        id=uuid.uuid4(),
        manifest_kind=TECHNICAL_REPORT_EVIDENCE_MANIFEST_KIND,
        agent_task_id=verification_task_id,
        draft_task_id=_uuid_or_none(payload["draft_task"].get("task_id")),
        verification_task_id=verification_task_id,
        evidence_package_export_id=(
            _uuid_or_none(evidence_exports[0].get("evidence_package_export_id"))
            if evidence_exports
            else None
        ),
        manifest_sha256=manifest_sha256,
        manifest_payload_json=_json_payload(payload),
        source_snapshot_sha256s_json=list(payload["source_snapshot_sha256s"]),
        document_ids_json=list(payload["document_ids"]),
        run_ids_json=list(payload["run_ids"]),
        claim_ids_json=list(payload["claim_ids"]),
        search_request_ids_json=list(payload["search_request_ids"]),
        operator_run_ids_json=list(payload["operator_run_ids"]),
        manifest_status="completed",
        created_at=utcnow(),
    )


def _update_evidence_manifest_row_from_payload(
    row: EvidenceManifest,
    *,
    payload: dict[str, Any],
    manifest_sha256: str,
) -> EvidenceManifest:
    evidence_exports = payload["report_trace"]["evidence_package_exports"]
    row.draft_task_id = _uuid_or_none(payload["draft_task"].get("task_id"))
    row.evidence_package_export_id = (
        _uuid_or_none(evidence_exports[0].get("evidence_package_export_id"))
        if evidence_exports
        else None
    )
    row.manifest_sha256 = manifest_sha256
    row.manifest_payload_json = _json_payload(payload)
    row.source_snapshot_sha256s_json = list(payload["source_snapshot_sha256s"])
    row.document_ids_json = list(payload["document_ids"])
    row.run_ids_json = list(payload["run_ids"])
    row.claim_ids_json = list(payload["claim_ids"])
    row.search_request_ids_json = list(payload["search_request_ids"])
    row.operator_run_ids_json = list(payload["operator_run_ids"])
    row.manifest_status = "completed"
    return row


def _evidence_manifest_has_release_readiness_db_gate_record(
    row: EvidenceManifest,
    gate_row: TechnicalReportReleaseReadinessDbGate | None,
) -> bool:
    if gate_row is None:
        return False
    context_pack_audit = (
        ((row.manifest_payload_json or {}).get("report_trace") or {}).get(
            "context_pack_audit"
        )
        or {}
    )
    gate_record = context_pack_audit.get("release_readiness_db_gate_record")
    if not isinstance(gate_record, dict):
        return False
    gate_record_integrity = context_pack_audit.get("release_readiness_db_gate_record_integrity")
    return (
        gate_record.get("gate_id") == str(gate_row.id)
        and gate_record.get("gate_payload_sha256") == gate_row.gate_payload_sha256
        and isinstance(gate_record_integrity, dict)
        and gate_record_integrity.get("complete") is True
    )


def _evidence_manifest_matches_current_payload(
    session: Session,
    row: EvidenceManifest,
) -> bool:
    try:
        current_payload = build_technical_report_evidence_manifest_payload(
            session,
            row.verification_task_id,
        )
    except ValueError:
        return False
    return payload_sha256(current_payload) == row.manifest_sha256


def persist_technical_report_evidence_manifest(
    session: Session,
    *,
    task_id: UUID,
) -> EvidenceManifest:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise ValueError(f"Agent task '{task_id}' was not found.")
    verification_task_id = _verification_task_id_for_manifest(session, task)
    existing = _existing_evidence_manifest(session, verification_task_id)
    if existing is not None:
        gate_row = persist_technical_report_release_readiness_db_gate(
            session,
            verification_task_id=verification_task_id,
            evidence_manifest=existing,
        )
        persist_technical_report_claim_retrieval_feedback_ledger(
            session,
            verification_task_id=verification_task_id,
            evidence_manifest=existing,
        )
        if (
            not _evidence_manifest_has_release_readiness_db_gate_record(existing, gate_row)
            or not _evidence_manifest_matches_current_payload(session, existing)
        ):
            return refresh_technical_report_evidence_manifest(session, task_id=verification_task_id)
        return existing
    persist_technical_report_release_readiness_db_gate(
        session,
        verification_task_id=verification_task_id,
    )
    persist_technical_report_claim_retrieval_feedback_ledger(
        session,
        verification_task_id=verification_task_id,
    )
    payload = build_technical_report_evidence_manifest_payload(session, verification_task_id)
    manifest_sha256 = str(payload_sha256(payload))
    row = _evidence_manifest_row_from_payload(
        verification_task_id=verification_task_id,
        payload=payload,
        manifest_sha256=manifest_sha256,
    )
    session.add(row)
    session.flush()
    _persist_evidence_trace_graph(session, manifest_row=row, manifest_payload=payload)
    persist_technical_report_release_readiness_db_gate(
        session,
        verification_task_id=verification_task_id,
        evidence_manifest=row,
    )
    persist_technical_report_claim_retrieval_feedback_ledger(
        session,
        verification_task_id=verification_task_id,
        evidence_manifest=row,
    )
    return row


def refresh_technical_report_evidence_manifest(
    session: Session,
    *,
    task_id: UUID,
) -> EvidenceManifest:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise ValueError(f"Agent task '{task_id}' was not found.")
    verification_task_id = _verification_task_id_for_manifest(session, task)
    persist_technical_report_release_readiness_db_gate(
        session,
        verification_task_id=verification_task_id,
    )
    persist_technical_report_claim_retrieval_feedback_ledger(
        session,
        verification_task_id=verification_task_id,
    )
    payload = build_technical_report_evidence_manifest_payload(session, verification_task_id)
    manifest_sha256 = str(payload_sha256(payload))
    row = _existing_evidence_manifest(session, verification_task_id)
    if row is None:
        row = _evidence_manifest_row_from_payload(
            verification_task_id=verification_task_id,
            payload=payload,
            manifest_sha256=manifest_sha256,
        )
        session.add(row)
    else:
        _update_evidence_manifest_row_from_payload(
            row,
            payload=payload,
            manifest_sha256=manifest_sha256,
        )
    _persist_evidence_trace_graph(session, manifest_row=row, manifest_payload=payload)
    session.flush()
    persist_technical_report_release_readiness_db_gate(
        session,
        verification_task_id=verification_task_id,
        evidence_manifest=row,
    )
    persist_technical_report_claim_retrieval_feedback_ledger(
        session,
        verification_task_id=verification_task_id,
        evidence_manifest=row,
    )
    return row


def _ensure_evidence_trace_graph(
    session: Session,
    row: EvidenceManifest,
) -> EvidenceManifest:
    if row.trace_sha256:
        return row
    _persist_evidence_trace_graph(
        session,
        manifest_row=row,
        manifest_payload=row.manifest_payload_json or {},
    )
    session.flush()
    return row


def get_agent_task_evidence_manifest(session: Session, task_id: UUID) -> dict[str, Any]:
    row = persist_technical_report_evidence_manifest(session, task_id=task_id)
    _ensure_evidence_trace_graph(session, row)
    return _evidence_manifest_response(session, row)


def get_agent_task_evidence_trace(session: Session, task_id: UUID) -> dict[str, Any]:
    row = persist_technical_report_evidence_manifest(session, task_id=task_id)
    _ensure_evidence_trace_graph(session, row)
    nodes, edges = _evidence_trace_rows(session, row.id)
    return {
        "schema_name": "technical_report_evidence_trace",
        "schema_version": "1.0",
        "evidence_manifest_id": str(row.id),
        "manifest_kind": row.manifest_kind,
        "manifest_sha256": row.manifest_sha256,
        "trace_sha256": row.trace_sha256,
        "manifest_status": row.manifest_status,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "manifest_provenance_edge_count": sum(
            1
            for edge in edges
            if (edge.payload_json or {}).get("source") == "manifest_provenance_edges"
        ),
        "nodes": [_trace_node_row_payload(node) for node in nodes],
        "edges": [_trace_edge_row_payload(edge) for edge in edges],
        "trace_integrity": _evidence_trace_integrity_payload(session, row, nodes, edges),
    }


existing_evidence_manifest = _existing_evidence_manifest
evidence_manifest_integrity_payload = _evidence_manifest_integrity_payload
evidence_manifest_response = _evidence_manifest_response
evidence_manifest_row_from_payload = _evidence_manifest_row_from_payload
update_evidence_manifest_row_from_payload = _update_evidence_manifest_row_from_payload
evidence_manifest_has_release_readiness_db_gate_record = (
    _evidence_manifest_has_release_readiness_db_gate_record
)
evidence_manifest_matches_current_payload = _evidence_manifest_matches_current_payload
ensure_evidence_trace_graph = _ensure_evidence_trace_graph
