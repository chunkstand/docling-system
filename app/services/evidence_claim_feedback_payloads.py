# ruff: noqa: E501, I001
from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.json_utils import json_object_payload as _json_payload
from app.db.public.audit_and_evidence import (
    ClaimEvidenceDerivation, TechnicalReportReleaseReadinessDbGate,
)
from app.db.public.retrieval import (
    SearchRequestRecord, SearchRequestResult, SearchRequestResultSpan,
)
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import string_values as _string_values
from app.services.evidence_common import uuid_values as _uuid_values
from app.services.evidence_constants import (
    TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_SCHEMA,
)
from app.services.evidence_records import select_by_ids as _select_by_ids


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
        claim_result_ids = _uuid_values(
            claim.get("source_search_request_result_ids") or []
        )
        claim_results = [
            results_by_id[result_id]
            for result_id in claim_result_ids
            if result_id in results_by_id
        ]
        claim_request_ids = _uuid_values(claim.get("source_search_request_ids") or [])
        claim_request_ids = list(
            dict.fromkeys(
                [*claim_request_ids, *[row.search_request_id for row in claim_results]]
            )
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
                "search_request_result_span_ids_json": _string_values(
                    row.id for row in spans
                ),
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


technical_report_claim_feedback_status = _technical_report_claim_feedback_status
search_request_result_spans_by_result_id = _search_request_result_spans_by_result_id
claim_feedback_evidence_refs = _claim_feedback_evidence_refs
claim_feedback_retrieval_context = _claim_feedback_retrieval_context
technical_report_claim_feedback_payloads = _technical_report_claim_feedback_payloads
