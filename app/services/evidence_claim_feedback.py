# ruff: noqa: E501, F401, I001
from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    ClaimEvidenceDerivation,
    EvidenceManifest,
    EvidencePackageExport,
    SearchRequestRecord,
    SearchRequestResult,
    SearchRequestResultSpan,
    SemanticGovernanceEvent,
    TechnicalReportClaimRetrievalFeedback,
    TechnicalReportReleaseReadinessDbGate,
)
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import string_values as _string_values
from app.services.evidence_common import uuid_values as _uuid_values
from app.services.evidence_constants import (
    TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_SCHEMA,
    TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
)
from app.services.evidence_provenance import (
    TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
)
from app.services.evidence_records import select_by_ids as _select_by_ids
from app.services.evidence_release_readiness import (
    technical_report_readiness_db_gate_for_verification_task as _technical_report_readiness_db_gate_for_verification_task,
)
from app.services.evidence_technical_report_context import (
    draft_task_id_for_audit as _draft_task_id_for_audit,
    passed_technical_report_verification as _passed_technical_report_verification,
    technical_report_upstream_task_ids as _technical_report_upstream_task_ids,
)
from app.services.semantic_governance import (
    record_technical_report_claim_retrieval_feedback_event,
)

def _technical_report_claim_feedback_status(
    claim: dict[str, Any],
) -> tuple[str, str, str | None]:
    verdict = str(claim.get("support_verdict") or "")
    support_score = claim.get("support_score")
    judgment = claim.get("support_judgment") or {}
    unsupported_reasons = {
        str(reason) for reason in judgment.get("unsupported_reasons") or []
    }
    if verdict == "supported":
        try:
            score = float(support_score)
        except (TypeError, ValueError):
            score = 0.0
        status = "weak" if score < 0.5 else "supported"
        return status, "positive", None
    if verdict == "insufficient_evidence":
        return "missing", "missing", "missing_expected"
    if "evidence_contains_contradiction_cue" in unsupported_reasons:
        return "contradicted", "negative", "explicit_irrelevant"
    return "rejected", "negative", "explicit_irrelevant"


def _search_request_result_spans_by_result_id(
    session: Session,
    result_ids: Iterable[UUID],
) -> dict[UUID, list[SearchRequestResultSpan]]:
    ids = list(dict.fromkeys(result_ids))
    if not ids:
        return {}
    grouped: dict[UUID, list[SearchRequestResultSpan]] = {}
    rows = (
        session.execute(
            select(SearchRequestResultSpan)
            .where(SearchRequestResultSpan.search_request_result_id.in_(ids))
            .order_by(
                SearchRequestResultSpan.search_request_result_id.asc(),
                SearchRequestResultSpan.span_rank.asc(),
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        grouped.setdefault(row.search_request_result_id, []).append(row)
    return grouped


def _claim_feedback_evidence_refs(
    spans: Iterable[SearchRequestResultSpan],
) -> list[dict[str, Any]]:
    return [
        _json_payload(
            {
                "search_request_result_span_id": row.id,
                "search_request_id": row.search_request_id,
                "search_request_result_id": row.search_request_result_id,
                "retrieval_evidence_span_id": row.retrieval_evidence_span_id,
                "span_rank": row.span_rank,
                "score_kind": row.score_kind,
                "score": row.score,
                "source_type": row.source_type,
                "source_id": row.source_id,
                "span_index": row.span_index,
                "page_from": row.page_from,
                "page_to": row.page_to,
                "text_excerpt": row.text_excerpt,
                "content_sha256": row.content_sha256,
                "source_snapshot_sha256": row.source_snapshot_sha256,
                "metadata": row.metadata_json or {},
            }
        )
        for row in spans
    ]


def _claim_feedback_retrieval_context(
    request_rows: Iterable[SearchRequestRecord],
    result_rows: Iterable[SearchRequestResult],
) -> dict[str, Any]:
    requests = [
        {
            "search_request_id": str(row.id),
            "origin": row.origin,
            "query_text": row.query_text,
            "mode": row.mode,
            "filters": row.filters_json or {},
            "harness_name": row.harness_name,
            "reranker_name": row.reranker_name,
            "reranker_version": row.reranker_version,
            "retrieval_profile_name": row.retrieval_profile_name,
            "harness_config": row.harness_config_json or {},
            "embedding_status": row.embedding_status,
            "candidate_count": row.candidate_count,
            "result_count": row.result_count,
            "table_hit_count": row.table_hit_count,
            "created_at": row.created_at,
        }
        for row in request_rows
    ]
    results = [
        {
            "search_request_result_id": str(row.id),
            "search_request_id": str(row.search_request_id),
            "rank": row.rank,
            "base_rank": row.base_rank,
            "result_type": row.result_type,
            "document_id": str(row.document_id),
            "run_id": str(row.run_id),
            "chunk_id": str(row.chunk_id) if row.chunk_id else None,
            "table_id": str(row.table_id) if row.table_id else None,
            "score": row.score,
            "keyword_score": row.keyword_score,
            "semantic_score": row.semantic_score,
            "hybrid_score": row.hybrid_score,
            "rerank_features": row.rerank_features_json or {},
            "page_from": row.page_from,
            "page_to": row.page_to,
            "source_filename": row.source_filename,
            "label": row.label,
            "preview_text": row.preview_text,
        }
        for row in result_rows
    ]
    primary_request = requests[0] if requests else {}
    return _json_payload(
        {
            "schema_name": "technical_report_claim_retrieval_context",
            "schema_version": "1.0",
            "request_count": len(requests),
            "result_count": len(results),
            "primary_query_text": primary_request.get("query_text"),
            "primary_mode": primary_request.get("mode") or "hybrid",
            "primary_harness_name": primary_request.get("harness_name"),
            "primary_reranker_name": primary_request.get("reranker_name"),
            "primary_reranker_version": primary_request.get("reranker_version"),
            "primary_retrieval_profile_name": primary_request.get("retrieval_profile_name"),
            "primary_harness_config": primary_request.get("harness_config") or {},
            "requests": requests,
            "results": results,
        }
    )


def _technical_report_claim_feedback_payloads(
    session: Session,
    *,
    verification_task_id: UUID,
    draft_payload: dict[str, Any],
    derivations: list[ClaimEvidenceDerivation],
    release_readiness_db_gate: TechnicalReportReleaseReadinessDbGate | None,
) -> list[dict[str, Any]]:
    claims = [
        claim for claim in draft_payload.get("claims") or [] if isinstance(claim, dict)
    ]
    derivations_by_claim_id = {row.claim_id: row for row in derivations}
    result_ids = _uuid_values(
        value
        for claim in claims
        for value in (claim.get("source_search_request_result_ids") or [])
    )
    results_by_id = _select_by_ids(session, SearchRequestResult, result_ids)
    request_ids = _uuid_values(
        [
            *[
                value
                for claim in claims
                for value in (claim.get("source_search_request_ids") or [])
            ],
            *[row.search_request_id for row in results_by_id.values()],
        ]
    )
    requests_by_id = _select_by_ids(session, SearchRequestRecord, request_ids)
    spans_by_result_id = _search_request_result_spans_by_result_id(session, result_ids)
    rows: list[dict[str, Any]] = []

    for claim in claims:
        claim_id = str(claim.get("claim_id") or "")
        if not claim_id:
            continue
        claim_result_ids = _uuid_values(claim.get("source_search_request_result_ids") or [])
        claim_results = [
            results_by_id[result_id]
            for result_id in claim_result_ids
            if result_id in results_by_id
        ]
        claim_request_ids = _uuid_values(claim.get("source_search_request_ids") or [])
        claim_request_ids = list(
            dict.fromkeys([*claim_request_ids, *[row.search_request_id for row in claim_results]])
        )
        claim_requests = [
            requests_by_id[request_id]
            for request_id in claim_request_ids
            if request_id in requests_by_id
        ]
        spans = [
            span
            for result_id in claim_result_ids
            for span in spans_by_result_id.get(result_id, [])
        ]
        evidence_refs = _claim_feedback_evidence_refs(spans)
        retrieval_context = _claim_feedback_retrieval_context(
            claim_requests,
            claim_results,
        )
        status, learning_label, hard_negative_kind = _technical_report_claim_feedback_status(
            claim
        )
        primary_request_id = claim_request_ids[0] if claim_request_ids else None
        primary_result_id = claim_results[0].id if claim_results else None
        derivation = derivations_by_claim_id.get(claim_id)
        source_payload = _json_payload(
            {
                "schema_name": "technical_report_claim_retrieval_feedback_source",
                "schema_version": "1.0",
                "technical_report_verification_task_id": str(verification_task_id),
                "claim_id": claim_id,
                "claim_text": claim.get("rendered_text"),
                "claim_evidence_derivation_id": (
                    str(derivation.id) if derivation is not None else None
                ),
                "derivation_sha256": (
                    derivation.derivation_sha256 if derivation is not None else None
                ),
                "provenance_lock_sha256": claim.get("provenance_lock_sha256"),
                "support_judgment_sha256": claim.get("support_judgment_sha256"),
                "support_judgment": claim.get("support_judgment") or {},
                "support_verdict": claim.get("support_verdict"),
                "support_score": claim.get("support_score"),
                "feedback_status": status,
                "learning_label": learning_label,
                "hard_negative_kind": hard_negative_kind,
                "source_search_request_ids": _string_values(claim_request_ids),
                "source_search_request_result_ids": _string_values(claim_result_ids),
                "search_request_result_span_ids": _string_values(row.id for row in spans),
                "retrieval_evidence_span_ids": _string_values(
                    row.retrieval_evidence_span_id
                    for row in spans
                    if row.retrieval_evidence_span_id
                ),
                "semantic_ontology_snapshot_ids": _string_values(
                    claim.get("semantic_ontology_snapshot_ids") or []
                ),
                "semantic_graph_snapshot_ids": _string_values(
                    claim.get("semantic_graph_snapshot_ids") or []
                ),
                "retrieval_reranker_artifact_ids": _string_values(
                    claim.get("retrieval_reranker_artifact_ids") or []
                ),
                "search_harness_release_ids": _string_values(
                    claim.get("search_harness_release_ids") or []
                ),
                "release_audit_bundle_ids": _string_values(
                    claim.get("release_audit_bundle_ids") or []
                ),
                "release_validation_receipt_ids": _string_values(
                    claim.get("release_validation_receipt_ids") or []
                ),
                "release_readiness_db_gate_id": (
                    str(release_readiness_db_gate.id)
                    if release_readiness_db_gate is not None
                    else None
                ),
                "release_readiness_db_gate_payload_sha256": (
                    release_readiness_db_gate.gate_payload_sha256
                    if release_readiness_db_gate is not None
                    else None
                ),
                "retrieval_context": retrieval_context,
                "evidence_refs": evidence_refs,
            }
        )
        source_payload_sha256 = str(payload_sha256(source_payload))
        feedback_payload = _json_payload(
            {
                "schema_name": TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_SCHEMA,
                "schema_version": "1.0",
                "feedback_kind": "generation_claim_retrieval_feedback",
                "technical_report_verification_task_id": str(verification_task_id),
                "claim_id": claim_id,
                "feedback_status": status,
                "learning_label": learning_label,
                "hard_negative_kind": hard_negative_kind,
                "source_payload_sha256": source_payload_sha256,
                "source": source_payload,
            }
        )
        rows.append(
            {
                "claim_id": claim_id,
                "claim_text": claim.get("rendered_text"),
                "claim_evidence_derivation_id": (
                    derivation.id if derivation is not None else None
                ),
                "support_verdict": str(claim.get("support_verdict") or ""),
                "support_score": claim.get("support_score"),
                "feedback_status": status,
                "learning_label": learning_label,
                "hard_negative_kind": hard_negative_kind,
                "source_search_request_id": primary_request_id,
                "search_request_result_id": primary_result_id,
                "source_search_request_ids_json": _string_values(claim_request_ids),
                "source_search_request_result_ids_json": _string_values(claim_result_ids),
                "search_request_result_span_ids_json": _string_values(row.id for row in spans),
                "retrieval_evidence_span_ids_json": _string_values(
                    row.retrieval_evidence_span_id
                    for row in spans
                    if row.retrieval_evidence_span_id
                ),
                "semantic_ontology_snapshot_ids_json": _string_values(
                    claim.get("semantic_ontology_snapshot_ids") or []
                ),
                "semantic_graph_snapshot_ids_json": _string_values(
                    claim.get("semantic_graph_snapshot_ids") or []
                ),
                "retrieval_reranker_artifact_ids_json": _string_values(
                    claim.get("retrieval_reranker_artifact_ids") or []
                ),
                "search_harness_release_ids_json": _string_values(
                    claim.get("search_harness_release_ids") or []
                ),
                "release_audit_bundle_ids_json": _string_values(
                    claim.get("release_audit_bundle_ids") or []
                ),
                "release_validation_receipt_ids_json": _string_values(
                    claim.get("release_validation_receipt_ids") or []
                ),
                "evidence_refs_json": evidence_refs,
                "retrieval_context_json": retrieval_context,
                "feedback_payload_json": feedback_payload,
                "feedback_payload_sha256": str(payload_sha256(feedback_payload)),
                "source_payload_json": source_payload,
                "source_payload_sha256": source_payload_sha256,
            }
        )
    return rows


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
        "support_verdict_matches": source_payload.get("support_verdict") == row.support_verdict,
        "feedback_status_matches": source_payload.get("feedback_status") == row.feedback_status,
        "learning_label_matches": source_payload.get("learning_label") == row.learning_label,
        "hard_negative_kind_matches": (
            source_payload.get("hard_negative_kind") == row.hard_negative_kind
        ),
        "release_readiness_db_gate_id_matches": (
            source_payload.get("release_readiness_db_gate_id")
            == (str(row.release_readiness_db_gate_id) if row.release_readiness_db_gate_id else None)
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
            "has_release_readiness_db_gate_link": row.release_readiness_db_gate_id is not None,
            "has_semantic_governance_event_link": row.semantic_governance_event_id is not None,
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
            feedback_payload = event_payload.get("technical_report_claim_retrieval_feedback") or {}
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


def _claim_retrieval_feedback_rows_for_verification_task(
    session: Session,
    verification_task_id: UUID,
) -> list[TechnicalReportClaimRetrievalFeedback]:
    return list(
        session.scalars(
            select(TechnicalReportClaimRetrievalFeedback)
            .where(
                TechnicalReportClaimRetrievalFeedback.technical_report_verification_task_id
                == verification_task_id
            )
            .order_by(TechnicalReportClaimRetrievalFeedback.claim_id.asc())
        )
    )


def _set_claim_feedback_append_only_link(
    row: TechnicalReportClaimRetrievalFeedback,
    *,
    field_name: str,
    value: UUID | None,
) -> bool:
    if value is None:
        return False
    current_value = getattr(row, field_name)
    if current_value is not None and current_value != value:
        raise ValueError(
            "Technical report claim retrieval feedback live links are append-only: "
            f"{field_name} for feedback row '{row.id}' is already set."
        )
    if current_value == value:
        return False
    setattr(row, field_name, value)
    return True


def persist_technical_report_claim_retrieval_feedback_ledger(
    session: Session,
    *,
    verification_task_id: UUID,
    evidence_manifest: EvidenceManifest | None = None,
    prov_export_artifact: AgentTaskArtifact | None = None,
    ensure_governance: bool = False,
) -> list[TechnicalReportClaimRetrievalFeedback]:
    verification_task = session.get(AgentTask, verification_task_id)
    if verification_task is None:
        raise ValueError(f"Agent task '{verification_task_id}' was not found.")
    if _passed_technical_report_verification(session, verification_task_id) is None:
        raise ValueError(
            "Claim retrieval feedback requires a passed technical report verification task."
        )

    draft_task_id = _draft_task_id_for_audit(verification_task)
    draft_task = session.get(AgentTask, draft_task_id)
    if draft_task is None:
        raise ValueError(f"Draft task '{draft_task_id}' was not found.")
    draft_payload = ((draft_task.result_json or {}).get("payload") or {}).get("draft") or {}
    related_task_ids = [
        draft_task.id,
        *_technical_report_upstream_task_ids(session, draft_payload),
        verification_task_id,
    ]
    related_task_ids = list(dict.fromkeys(related_task_ids))
    report_exports = list(
        session.scalars(
            select(EvidencePackageExport)
            .where(
                EvidencePackageExport.agent_task_id.in_(related_task_ids),
                EvidencePackageExport.package_kind == "technical_report_claims",
            )
            .order_by(EvidencePackageExport.created_at.asc())
        )
    )
    report_export_ids = [row.id for row in report_exports]
    derivations = (
        list(
            session.scalars(
                select(ClaimEvidenceDerivation)
                .where(ClaimEvidenceDerivation.evidence_package_export_id.in_(report_export_ids))
                .order_by(ClaimEvidenceDerivation.claim_id.asc())
            )
        )
        if report_export_ids
        else []
    )
    release_gate = _technical_report_readiness_db_gate_for_verification_task(
        session,
        verification_task_id,
    )
    desired_rows = _technical_report_claim_feedback_payloads(
        session,
        verification_task_id=verification_task_id,
        draft_payload=draft_payload,
        derivations=derivations,
        release_readiness_db_gate=release_gate,
    )
    existing_by_claim_id = {
        row.claim_id: row
        for row in _claim_retrieval_feedback_rows_for_verification_task(
            session,
            verification_task_id,
        )
    }
    now = utcnow()
    for desired in desired_rows:
        existing = existing_by_claim_id.get(desired["claim_id"])
        if existing is not None:
            if (
                existing.feedback_payload_sha256 != desired["feedback_payload_sha256"]
                or existing.source_payload_sha256 != desired["source_payload_sha256"]
            ):
                raise ValueError(
                    "Existing claim retrieval feedback row does not match the "
                    f"current verified claim payload: {desired['claim_id']}"
                )
            changed_links = [
                _set_claim_feedback_append_only_link(
                    existing,
                    field_name="evidence_manifest_id",
                    value=evidence_manifest.id if evidence_manifest is not None else None,
                ),
                _set_claim_feedback_append_only_link(
                    existing,
                    field_name="prov_export_artifact_id",
                    value=prov_export_artifact.id if prov_export_artifact is not None else None,
                ),
                _set_claim_feedback_append_only_link(
                    existing,
                    field_name="release_readiness_db_gate_id",
                    value=release_gate.id if release_gate is not None else None,
                ),
            ]
            changed = any(changed_links)
            if changed:
                existing.updated_at = now
            continue

        row = TechnicalReportClaimRetrievalFeedback(
            id=uuid.uuid4(),
            technical_report_verification_task_id=verification_task_id,
            evidence_manifest_id=(
                evidence_manifest.id if evidence_manifest is not None else None
            ),
            prov_export_artifact_id=(
                prov_export_artifact.id if prov_export_artifact is not None else None
            ),
            release_readiness_db_gate_id=release_gate.id if release_gate is not None else None,
            created_at=now,
            updated_at=now,
            **desired,
        )
        session.add(row)
        existing_by_claim_id[row.claim_id] = row
    session.flush()

    rows = _claim_retrieval_feedback_rows_for_verification_task(
        session,
        verification_task_id,
    )
    if ensure_governance:
        for row in rows:
            if row.semantic_governance_event_id is not None:
                continue
            event = record_technical_report_claim_retrieval_feedback_event(
                session,
                feedback=row,
            )
            row.semantic_governance_event_id = event.id
            row.updated_at = utcnow()
        session.flush()
    return rows


technical_report_claim_feedback_status = _technical_report_claim_feedback_status
technical_report_claim_feedback_payloads = _technical_report_claim_feedback_payloads
claim_retrieval_feedback_payload = _claim_retrieval_feedback_payload
technical_report_claim_feedback_row_integrity = _technical_report_claim_feedback_row_integrity
technical_report_claim_feedback_integrity_payload = (
    _technical_report_claim_feedback_integrity_payload
)
claim_retrieval_feedback_rows_for_verification_task = (
    _claim_retrieval_feedback_rows_for_verification_task
)
set_claim_feedback_append_only_link = _set_claim_feedback_append_only_link
