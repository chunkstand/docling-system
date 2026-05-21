# ruff: noqa: E501
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.public.agent_tasks import AgentTaskArtifact
from app.db.public.audit_and_evidence import (
    EvidenceManifest,
    TechnicalReportClaimRetrievalFeedback,
    TechnicalReportReleaseReadinessDbGate,
)
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import string_values as _string_values
from app.services.evidence_constants import (
    TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
)
from app.services.evidence_provenance import (
    TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
)


def _claim_retrieval_feedback_payload(
    row: TechnicalReportClaimRetrievalFeedback,
    *,
    include_live_links: bool = True,
) -> dict[str, Any]:
    payload = {
        "feedback_id": row.id,
        "technical_report_verification_task_id": row.technical_report_verification_task_id,
        "claim_evidence_derivation_id": row.claim_evidence_derivation_id,
        "release_readiness_db_gate_id": row.release_readiness_db_gate_id,
        "claim_id": row.claim_id,
        "claim_text": row.claim_text,
        "support_verdict": row.support_verdict,
        "support_score": row.support_score,
        "feedback_status": row.feedback_status,
        "learning_label": row.learning_label,
        "hard_negative_kind": row.hard_negative_kind,
        "source_search_request_id": row.source_search_request_id,
        "search_request_result_id": row.search_request_result_id,
        "source_search_request_ids": row.source_search_request_ids_json or [],
        "source_search_request_result_ids": (
            row.source_search_request_result_ids_json or []
        ),
        "search_request_result_span_ids": row.search_request_result_span_ids_json or [],
        "retrieval_evidence_span_ids": row.retrieval_evidence_span_ids_json or [],
        "semantic_ontology_snapshot_ids": row.semantic_ontology_snapshot_ids_json or [],
        "semantic_graph_snapshot_ids": row.semantic_graph_snapshot_ids_json or [],
        "retrieval_reranker_artifact_ids": row.retrieval_reranker_artifact_ids_json or [],
        "search_harness_release_ids": row.search_harness_release_ids_json or [],
        "release_audit_bundle_ids": row.release_audit_bundle_ids_json or [],
        "release_validation_receipt_ids": row.release_validation_receipt_ids_json or [],
        "evidence_refs": row.evidence_refs_json or [],
        "retrieval_context": row.retrieval_context_json or {},
        "feedback_payload": row.feedback_payload_json or {},
        "feedback_payload_sha256": row.feedback_payload_sha256,
        "source_payload": row.source_payload_json or {},
        "source_payload_sha256": row.source_payload_sha256,
        "created_at": row.created_at,
    }
    if include_live_links:
        payload.update(
            {
                "evidence_manifest_id": row.evidence_manifest_id,
                "prov_export_artifact_id": row.prov_export_artifact_id,
                "semantic_governance_event_id": row.semantic_governance_event_id,
                "updated_at": row.updated_at,
            }
        )
    return payload


def _technical_report_claim_feedback_row_integrity(
    row: TechnicalReportClaimRetrievalFeedback,
    *,
    session: Session | None = None,
    require_live_links: bool = False,
) -> dict[str, Any]:
    stored_feedback_hash = str(payload_sha256(row.feedback_payload_json or {}))
    stored_source_hash = str(payload_sha256(row.source_payload_json or {}))
    source_payload_hash_matches = stored_source_hash == row.source_payload_sha256
    feedback_payload_hash_matches = stored_feedback_hash == row.feedback_payload_sha256
    feedback_source_hash = (row.feedback_payload_json or {}).get("source_payload_sha256")
    feedback_source_hash_matches = feedback_source_hash == row.source_payload_sha256
    source_payload = row.source_payload_json or {}
    source_payload_column_checks = {
        "claim_id_matches": source_payload.get("claim_id") == row.claim_id,
        "support_verdict_matches": source_payload.get("support_verdict")
        == row.support_verdict,
        "feedback_status_matches": source_payload.get("feedback_status")
        == row.feedback_status,
        "learning_label_matches": source_payload.get("learning_label")
        == row.learning_label,
        "hard_negative_kind_matches": (
            source_payload.get("hard_negative_kind") == row.hard_negative_kind
        ),
        "release_readiness_db_gate_id_matches": (
            source_payload.get("release_readiness_db_gate_id")
            == (
                str(row.release_readiness_db_gate_id)
                if row.release_readiness_db_gate_id
                else None
            )
        ),
        "source_search_request_ids_match": (
            _string_values(source_payload.get("source_search_request_ids") or [])
            == _string_values(row.source_search_request_ids_json or [])
        ),
        "source_search_request_result_ids_match": (
            _string_values(source_payload.get("source_search_request_result_ids") or [])
            == _string_values(row.source_search_request_result_ids_json or [])
        ),
        "search_request_result_span_ids_match": (
            _string_values(source_payload.get("search_request_result_span_ids") or [])
            == _string_values(row.search_request_result_span_ids_json or [])
        ),
        "retrieval_evidence_span_ids_match": (
            _string_values(source_payload.get("retrieval_evidence_span_ids") or [])
            == _string_values(row.retrieval_evidence_span_ids_json or [])
        ),
    }
    source_payload_columns_match = all(source_payload_column_checks.values())
    live_link_checks: dict[str, bool] = {}
    if require_live_links:
        live_link_checks = {
            "has_evidence_manifest_link": row.evidence_manifest_id is not None,
            "has_prov_export_artifact_link": row.prov_export_artifact_id is not None,
            "has_release_readiness_db_gate_link": row.release_readiness_db_gate_id
            is not None,
            "has_semantic_governance_event_link": row.semantic_governance_event_id
            is not None,
            "evidence_manifest_matches_feedback": False,
            "prov_export_artifact_matches_feedback": False,
            "release_readiness_db_gate_matches_feedback": False,
            "semantic_governance_event_matches_feedback": False,
        }
    if require_live_links and session is not None:
        if row.evidence_manifest_id is not None:
            manifest = session.get(EvidenceManifest, row.evidence_manifest_id)
            live_link_checks["evidence_manifest_matches_feedback"] = bool(
                manifest is not None
                and manifest.verification_task_id == row.technical_report_verification_task_id
            )
        if row.prov_export_artifact_id is not None:
            artifact = session.get(AgentTaskArtifact, row.prov_export_artifact_id)
            live_link_checks["prov_export_artifact_matches_feedback"] = bool(
                artifact is not None
                and artifact.task_id == row.technical_report_verification_task_id
                and artifact.artifact_kind == TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND
            )
        if row.release_readiness_db_gate_id is not None:
            gate = session.get(
                TechnicalReportReleaseReadinessDbGate,
                row.release_readiness_db_gate_id,
            )
            live_link_checks["release_readiness_db_gate_matches_feedback"] = bool(
                gate is not None
                and gate.technical_report_verification_task_id
                == row.technical_report_verification_task_id
                and gate.gate_payload_sha256
                == source_payload.get("release_readiness_db_gate_payload_sha256")
            )
        if row.semantic_governance_event_id is not None:
            event = session.get(SemanticGovernanceEvent, row.semantic_governance_event_id)
            event_payload = (event.event_payload_json if event is not None else None) or {}
            feedback_payload = (
                event_payload.get("technical_report_claim_retrieval_feedback") or {}
            )
            live_link_checks["semantic_governance_event_matches_feedback"] = bool(
                event is not None
                and event.event_kind == "technical_report_claim_retrieval_feedback_recorded"
                and event.subject_table == TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE
                and event.subject_id == row.id
                and event.task_id == row.technical_report_verification_task_id
                and event.evidence_manifest_id == row.evidence_manifest_id
                and event.agent_task_artifact_id == row.prov_export_artifact_id
                and event.receipt_sha256 == row.feedback_payload_sha256
                and feedback_payload.get("feedback_id") == str(row.id)
                and feedback_payload.get("claim_id") == row.claim_id
            )
    live_link_integrity_verified = all(live_link_checks.values()) if require_live_links else True
    core_hash_integrity_verified = bool(
        feedback_payload_hash_matches
        and source_payload_hash_matches
        and feedback_source_hash_matches
    )
    return {
        "schema_name": "technical_report_claim_retrieval_feedback_row_integrity",
        "schema_version": "1.0",
        "feedback_id": str(row.id),
        "claim_id": row.claim_id,
        "stored_feedback_payload_sha256": row.feedback_payload_sha256,
        "expected_feedback_payload_sha256": stored_feedback_hash,
        "stored_source_payload_sha256": row.source_payload_sha256,
        "expected_source_payload_sha256": stored_source_hash,
        "feedback_payload_hash_matches": feedback_payload_hash_matches,
        "source_payload_hash_matches": source_payload_hash_matches,
        "feedback_source_hash_matches": feedback_source_hash_matches,
        "source_payload_column_checks": source_payload_column_checks,
        "source_payload_columns_match": source_payload_columns_match,
        "live_link_checks": live_link_checks,
        "live_link_integrity_required": require_live_links,
        "live_link_integrity_verified": live_link_integrity_verified,
        "core_hash_integrity_verified": core_hash_integrity_verified,
        "has_search_request_ids": bool(row.source_search_request_ids_json),
        "has_search_request_result_ids": bool(row.source_search_request_result_ids_json),
        "complete": bool(
            core_hash_integrity_verified
            and source_payload_columns_match
            and live_link_integrity_verified
        ),
    }


def _technical_report_claim_feedback_integrity_payload(
    draft_payload: dict[str, Any],
    rows: list[TechnicalReportClaimRetrievalFeedback],
    *,
    session: Session | None = None,
    require_live_links: bool = False,
) -> dict[str, Any]:
    claim_ids = sorted(
        str(claim.get("claim_id") or "")
        for claim in draft_payload.get("claims") or []
        if claim.get("claim_id")
    )
    row_claim_ids = sorted(row.claim_id for row in rows)
    missing_claim_ids = sorted(set(claim_ids) - set(row_claim_ids))
    unexpected_claim_ids = sorted(set(row_claim_ids) - set(claim_ids))
    row_integrities = [
        _technical_report_claim_feedback_row_integrity(
            row,
            session=session,
            require_live_links=require_live_links,
        )
        for row in rows
    ]
    coverage_complete = bool(claim_ids) and not missing_claim_ids and not unexpected_claim_ids
    core_hash_integrity_verified = bool(rows) and all(
        row["core_hash_integrity_verified"] for row in row_integrities
    )
    source_payload_columns_match = bool(rows) and all(
        row["source_payload_columns_match"] for row in row_integrities
    )
    live_link_integrity_verified = bool(rows) and all(
        row["live_link_integrity_verified"] for row in row_integrities
    )
    integrity_verified = (
        core_hash_integrity_verified
        and source_payload_columns_match
        and live_link_integrity_verified
    )
    return {
        "schema_name": "technical_report_claim_retrieval_feedback_integrity",
        "schema_version": "1.0",
        "claim_count": len(claim_ids),
        "feedback_row_count": len(rows),
        "coverage_complete": coverage_complete,
        "integrity_verified": integrity_verified,
        "core_hash_integrity_verified": core_hash_integrity_verified,
        "source_payload_columns_match": source_payload_columns_match,
        "live_link_integrity_required": require_live_links,
        "live_link_integrity_verified": live_link_integrity_verified,
        "missing_claim_ids": missing_claim_ids,
        "unexpected_claim_ids": unexpected_claim_ids,
        "missing_claim_count": len(missing_claim_ids),
        "unexpected_claim_count": len(unexpected_claim_ids),
        "feedback_payload_hash_mismatch_count": sum(
            1 for row in row_integrities if not row["feedback_payload_hash_matches"]
        ),
        "source_payload_hash_mismatch_count": sum(
            1 for row in row_integrities if not row["source_payload_hash_matches"]
        ),
        "feedback_source_hash_mismatch_count": sum(
            1 for row in row_integrities if not row["feedback_source_hash_matches"]
        ),
        "source_payload_column_mismatch_count": sum(
            1 for row in row_integrities if not row["source_payload_columns_match"]
        ),
        "live_link_mismatch_count": sum(
            1 for row in row_integrities if not row["live_link_integrity_verified"]
        ),
        "status_counts": {
            status: sum(1 for row in rows if row.feedback_status == status)
            for status in sorted({row.feedback_status for row in rows})
        },
        "learning_label_counts": {
            label: sum(1 for row in rows if row.learning_label == label)
            for label in sorted({row.learning_label for row in rows})
        },
        "row_integrities": row_integrities,
        "complete": coverage_complete and integrity_verified,
    }


claim_retrieval_feedback_payload = _claim_retrieval_feedback_payload
technical_report_claim_feedback_row_integrity = (
    _technical_report_claim_feedback_row_integrity
)
technical_report_claim_feedback_integrity_payload = (
    _technical_report_claim_feedback_integrity_payload
)
