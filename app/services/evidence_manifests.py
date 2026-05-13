# ruff: noqa: E501, F401, I001
from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    Document,
    DocumentRun,
    EvidenceManifest,
    TechnicalReportReleaseReadinessDbGate,
)
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import trace_edge_row_payload as _trace_edge_row_payload
from app.services.evidence_common import trace_node_row_payload as _trace_node_row_payload
from app.services.evidence_constants import TECHNICAL_REPORT_EVIDENCE_MANIFEST_KIND
from app.services.evidence_manifest_traces import (
    evidence_trace_integrity_payload as _evidence_trace_integrity_payload,
    evidence_trace_rows as _evidence_trace_rows,
    persist_evidence_trace_graph as _persist_evidence_trace_graph,
)
from app.services.evidence_semantic_trace import (
    report_evidence_card_source_records as _report_evidence_card_source_records,
    semantic_trace_payload as _semantic_trace_payload,
    source_record_payloads_from_semantic_trace as _source_record_payloads_from_semantic_trace,
    technical_report_provenance_edges as _technical_report_provenance_edges,
)
from app.services.evidence_technical_report_context import verification_task_id_for_manifest as _verification_task_id_for_manifest
from app.services.evidence_claim_feedback import (
    persist_technical_report_claim_retrieval_feedback_ledger,
)
from app.services.evidence_audit_views import (
    get_agent_task_audit_bundle,
    persist_technical_report_release_readiness_db_gate,
)
from app.services.evidence_common import string_values as _string_values
from app.services.evidence_common import uuid_or_none_safe as _uuid_or_none_safe
from app.services.evidence_common import uuid_values as _uuid_values
from app.services.evidence_semantic_trace import technical_report_integrity_payload as _technical_report_integrity_payload
from app.core.coercion import uuid_or_none as _uuid_or_none
from app.services.evidence_records import (
    document_payload as _document_payload,
    manifest_run_payload as _manifest_run_payload,
    select_by_ids as _select_by_ids,
)

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
    task = session.get(AgentTask, task_id)
    if task is None:
        raise ValueError(f"Agent task '{task_id}' was not found.")
    verification_task_id = _verification_task_id_for_manifest(session, task)
    audit_bundle = get_agent_task_audit_bundle(
        session,
        verification_task_id,
        include_live_release_readiness_db_gate_links=False,
        include_live_claim_retrieval_feedback_links=False,
    )
    draft_payload = audit_bundle["draft"]
    evidence_cards = list(draft_payload.get("evidence_cards") or [])
    claims = list(draft_payload.get("claims") or [])
    evidence_exports = list(audit_bundle.get("evidence_package_exports") or [])
    source_evidence_closure = dict(audit_bundle.get("source_evidence_closure") or {})
    claim_derivations = list(audit_bundle.get("claim_derivations") or [])
    claim_retrieval_feedback = list(audit_bundle.get("claim_retrieval_feedback") or [])
    claim_retrieval_feedback_integrity = dict(
        audit_bundle.get("claim_retrieval_feedback_integrity") or {}
    )
    operator_runs = list(audit_bundle.get("operator_runs") or [])
    context_pack_audit = dict(audit_bundle.get("context_pack_audit") or {})
    document_ids = _uuid_values(
        [
            *[row.get("document_id") for row in draft_payload.get("document_refs") or []],
            *[card.get("document_id") for card in evidence_cards],
            *[
                document_id
                for claim in claims
                for document_id in (claim.get("source_document_ids") or [])
            ],
            *[
                document_id
                for export in evidence_exports
                for document_id in (export.get("document_ids") or [])
            ],
        ]
    )
    run_ids = _uuid_values(
        [
            *[row.get("run_id") for row in draft_payload.get("document_refs") or []],
            *[card.get("run_id") for card in evidence_cards],
            *[run_id for export in evidence_exports for run_id in (export.get("run_ids") or [])],
        ]
    )
    assertion_ids = _uuid_values(
        [
            *[
                assertion_id
                for card in evidence_cards
                for assertion_id in (card.get("assertion_ids") or [])
            ],
            *[
                assertion_id
                for claim in claims
                for assertion_id in (claim.get("assertion_ids") or [])
            ],
        ]
    )
    fact_ids = _uuid_values(
        [
            *[fact_id for card in evidence_cards for fact_id in (card.get("fact_ids") or [])],
            *[fact_id for claim in claims for fact_id in (claim.get("fact_ids") or [])],
        ]
    )
    evidence_ids = _uuid_values(
        evidence_id for card in evidence_cards for evidence_id in (card.get("evidence_ids") or [])
    )
    documents_by_id = _select_by_ids(session, Document, document_ids)
    runs_by_id = _select_by_ids(session, DocumentRun, run_ids)
    semantic_trace = _semantic_trace_payload(
        session,
        assertion_ids=assertion_ids,
        fact_ids=fact_ids,
        evidence_ids=evidence_ids,
    )
    source_documents = [
        _document_payload(row)
        for row in sorted(documents_by_id.values(), key=lambda item: str(item.id))
    ]
    document_runs = [
        _manifest_run_payload(row)
        for row in sorted(runs_by_id.values(), key=lambda item: str(item.id))
    ]
    source_records = [
        *_report_evidence_card_source_records(evidence_cards),
        *_source_record_payloads_from_semantic_trace(
            session,
            semantic_trace["assertion_evidence"],
        ),
    ]
    search_request_ids = _string_values(
        [
            *[row.get("search_request_id") for row in operator_runs],
            *[row.get("search_request_id") for row in evidence_exports],
        ]
    )
    operator_run_ids = _string_values(
        [
            *(row.get("operator_run_id") for row in operator_runs),
            *[
                operator_run_id
                for export in evidence_exports
                for operator_run_id in (export.get("operator_run_ids") or [])
            ],
        ]
    )
    source_snapshot_sha256s = _string_values(
        [
            *(draft_payload.get("source_snapshot_sha256s") or []),
            *[value for claim in claims for value in (claim.get("source_snapshot_sha256s") or [])],
            *[
                value
                for export in evidence_exports
                for value in (export.get("source_snapshot_sha256s") or [])
            ],
        ]
    )
    provenance_edges = _technical_report_provenance_edges(
        source_documents=source_documents,
        document_runs=document_runs,
        evidence_exports=evidence_exports,
        evidence_cards=evidence_cards,
        claims=claims,
        claim_derivations=claim_derivations,
        claim_retrieval_feedback=claim_retrieval_feedback,
        semantic_trace=semantic_trace,
        context_pack_audit=context_pack_audit,
    )
    checklist = {
        "has_source_documents": bool(source_documents),
        "all_source_documents_hashed": bool(source_documents)
        and all(document.get("sha256") for document in source_documents),
        "has_document_runs": bool(document_runs),
        "all_document_runs_validation_passed": bool(document_runs)
        and all(run.get("validation_status") == "passed" for run in document_runs),
        "has_evidence_cards": bool(evidence_cards),
        "has_claims": bool(claims),
        "has_claim_derivations": len(claim_derivations) == len(claims) and bool(claims),
        "has_claim_provenance_locks": bool(claims)
        and all(claim.get("provenance_lock_sha256") for claim in claims)
        and audit_bundle["audit_checklist"].get("all_claims_have_provenance_locks", False),
        "has_claim_support_judgments": bool(claims)
        and all(
            claim.get("support_verdict") == "supported"
            and claim.get("support_score") is not None
            and claim.get("support_judge_run_id")
            and claim.get("support_judgment_sha256")
            for claim in claims
        )
        and audit_bundle["audit_checklist"].get("all_claims_have_support_judgments", False)
        and audit_bundle["audit_checklist"].get(
            "claim_support_judgment_integrity_verified",
            False,
        ),
        "has_claim_source_search_results": bool(claims)
        and all(claim.get("source_search_request_result_ids") for claim in claims)
        and audit_bundle["audit_checklist"].get("all_claims_have_source_search_results", False),
        "has_claim_retrieval_feedback_ledger": audit_bundle["audit_checklist"].get(
            "has_claim_retrieval_feedback_ledger",
            False,
        ),
        "claim_retrieval_feedback_coverage_complete": audit_bundle["audit_checklist"].get(
            "claim_retrieval_feedback_coverage_complete",
            False,
        ),
        "claim_retrieval_feedback_integrity_verified": audit_bundle["audit_checklist"].get(
            "claim_retrieval_feedback_integrity_verified",
            False,
        ),
        "has_semantic_trace": bool(
            semantic_trace["assertions"]
            or semantic_trace["facts"]
            or draft_payload.get("graph_context")
        ),
        "has_generation_operator_run": audit_bundle["audit_checklist"].get(
            "has_generation_operator_run",
            False,
        ),
        "has_support_judge_operator_run": audit_bundle["audit_checklist"].get(
            "has_support_judge_operator_run",
            False,
        ),
        "has_verification_operator_run": audit_bundle["audit_checklist"].get(
            "has_verification_operator_run",
            False,
        ),
        "has_context_pack_artifact": audit_bundle["audit_checklist"].get(
            "has_context_pack_artifact",
            False,
        ),
        "has_context_pack_evaluation_artifact": audit_bundle["audit_checklist"].get(
            "has_context_pack_evaluation_artifact",
            False,
        ),
        "has_context_pack_verifier_record": audit_bundle["audit_checklist"].get(
            "has_context_pack_verifier_record",
            False,
        ),
        "has_context_pack_evaluation_operator_run": audit_bundle["audit_checklist"].get(
            "has_context_pack_evaluation_operator_run",
            False,
        ),
        "context_pack_evaluation_passed": audit_bundle["audit_checklist"].get(
            "context_pack_evaluation_passed",
            False,
        ),
        "context_pack_hash_verified": audit_bundle["audit_checklist"].get(
            "context_pack_hash_verified",
            False,
        ),
        "has_release_readiness_assessments": audit_bundle["audit_checklist"].get(
            "has_release_readiness_assessments",
            False,
        ),
        "release_readiness_assessments_cover_source_requests": audit_bundle["audit_checklist"].get(
            "release_readiness_assessments_cover_source_requests", False
        ),
        "release_readiness_assessments_ready": audit_bundle["audit_checklist"].get(
            "release_readiness_assessments_ready",
            False,
        ),
        "release_readiness_assessment_integrity_verified": audit_bundle["audit_checklist"].get(
            "release_readiness_assessment_integrity_verified", False
        ),
        "release_readiness_db_gate_verified": audit_bundle["audit_checklist"].get(
            "release_readiness_db_gate_verified",
            False,
        ),
        "release_readiness_db_gate_complete": audit_bundle["audit_checklist"].get(
            "release_readiness_db_gate_complete",
            False,
        ),
        "release_readiness_db_covers_source_requests": audit_bundle["audit_checklist"].get(
            "release_readiness_db_covers_source_requests", False
        ),
        "has_persisted_release_readiness_db_gate": audit_bundle["audit_checklist"].get(
            "has_persisted_release_readiness_db_gate",
            False,
        ),
        "persisted_release_readiness_db_gate_integrity_verified": audit_bundle[
            "audit_checklist"
        ].get("persisted_release_readiness_db_gate_integrity_verified", False),
        "verification_passed": audit_bundle["audit_checklist"].get(
            "verification_passed",
            False,
        ),
        "hash_integrity_verified": audit_bundle["audit_checklist"].get(
            "hash_integrity_verified",
            False,
        ),
        "has_frozen_source_evidence_packages": audit_bundle["audit_checklist"].get(
            "has_frozen_source_evidence_packages",
            False,
        ),
        "source_evidence_trace_integrity_verified": audit_bundle["audit_checklist"].get(
            "source_evidence_trace_integrity_verified",
            False,
        ),
        "generation_evidence_closed": audit_bundle["audit_checklist"].get(
            "generation_evidence_closed",
            False,
        ),
        "change_impact_clear": audit_bundle["audit_checklist"].get(
            "change_impact_clear",
            False,
        ),
        "replay_alert_waiver_closure_integrity_verified": audit_bundle["audit_checklist"].get(
            "replay_alert_waiver_closure_integrity_verified", False
        ),
        "replay_alert_waiver_lifecycle_clear": audit_bundle["audit_checklist"].get(
            "replay_alert_waiver_lifecycle_clear",
            False,
        ),
        "active_replay_alert_fixture_corpus_snapshot_id": audit_bundle["audit_checklist"].get(
            "active_replay_alert_fixture_corpus_snapshot_id"
        ),
        "active_replay_alert_fixture_corpus_sha256": audit_bundle["audit_checklist"].get(
            "active_replay_alert_fixture_corpus_sha256"
        ),
        "replay_alert_fixture_corpus_snapshot_governed": audit_bundle["audit_checklist"].get(
            "replay_alert_fixture_corpus_snapshot_governed", True
        ),
        "replay_alert_fixture_corpus_trace_complete": audit_bundle["audit_checklist"].get(
            "replay_alert_fixture_corpus_trace_complete", True
        ),
        "invalid_replay_alert_fixture_corpus_snapshot_governance_count": audit_bundle[
            "audit_checklist"
        ].get("invalid_replay_alert_fixture_corpus_snapshot_governance_count", 0),
        "incomplete_replay_alert_fixture_corpus_trace_count": audit_bundle["audit_checklist"].get(
            "incomplete_replay_alert_fixture_corpus_trace_count", 0
        ),
        "has_provenance_edges": bool(provenance_edges),
    }
    checklist["complete"] = all(value for value in checklist.values() if isinstance(value, bool))
    return {
        "schema_name": "technical_report_evidence_manifest",
        "schema_version": "1.0",
        "manifest_kind": TECHNICAL_REPORT_EVIDENCE_MANIFEST_KIND,
        "task": audit_bundle["task"],
        "draft_task": audit_bundle["draft_task"],
        "verification_task": audit_bundle["verification_task"],
        "source_documents": source_documents,
        "document_runs": document_runs,
        "source_records": source_records,
        "semantic_trace": semantic_trace,
        "retrieval_trace": {
            "search_request_ids": search_request_ids,
            "ranking_operator_runs": [
                row
                for row in operator_runs
                if row.get("operator_kind") in {"retrieve", "rerank", "judge"}
            ],
            "search_evidence_package_exports": [
                row for row in evidence_exports if row.get("package_kind") == "search_request"
            ],
            "search_evidence_package_trace_summaries": list(
                audit_bundle.get("search_evidence_package_traces") or []
            ),
            "source_evidence_closure": source_evidence_closure,
        },
        "report_trace": {
            "evidence_cards": evidence_cards,
            "claims": claims,
            "claim_derivations": claim_derivations,
            "claim_retrieval_feedback": claim_retrieval_feedback,
            "claim_retrieval_feedback_integrity": claim_retrieval_feedback_integrity,
            "evidence_package_exports": evidence_exports,
            "evidence_package_integrity": audit_bundle["integrity"],
            "verification": audit_bundle["verification_record"],
            "context_pack_audit": context_pack_audit,
            "operator_runs": operator_runs,
        },
        "provenance_edges": provenance_edges,
        "change_impact": audit_bundle["change_impact"],
        "audit_checklist": checklist,
        "source_snapshot_sha256s": source_snapshot_sha256s,
        "document_ids": _string_values(document_ids),
        "run_ids": _string_values(run_ids),
        "claim_ids": _string_values(claim.get("claim_id") for claim in claims),
        "search_request_ids": search_request_ids,
        "operator_run_ids": operator_run_ids,
    }


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
