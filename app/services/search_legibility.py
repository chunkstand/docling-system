from __future__ import annotations

import hashlib
import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.search import (
    SearchHarnessDescriptorResponse,
    SearchRequestDiagnosis,
    SearchRequestExplanationResponse,
    SearchRequestExplanationResult,
)
from app.services.search import (
    DEFAULT_SEARCH_HARNESS_NAME,
    SEARCH_HARNESS_RERANKER_OVERRIDE_FIELDS,
    SEARCH_HARNESS_RETRIEVAL_OVERRIDE_FIELDS,
    get_search_harness,
)
from app.services.search_history import get_search_request_detail


def _payload_fingerprint(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _top_result_snapshot(results) -> list[SearchRequestExplanationResult]:
    snapshot: list[SearchRequestExplanationResult] = []
    for result in results[:5]:
        label = result.table_title if result.result_type == "table" else result.heading
        snapshot.append(
            SearchRequestExplanationResult(
                rank=result.rank,
                result_type=result.result_type,
                score=result.score,
                source_filename=result.source_filename,
                document_id=result.document_id,
                run_id=result.run_id,
                chunk_id=result.chunk_id,
                table_id=result.table_id,
                label=label,
                page_from=result.page_from,
                page_to=result.page_to,
                base_rank=result.base_rank,
                rerank_features=result.rerank_features,
            )
        )
    return snapshot


def _diagnose_search_request(
    *,
    requested_mode: str,
    served_mode: str,
    fallback_reason: str | None,
    embedding_status: str,
    filters: dict,
    tabular_query: bool,
    result_count: int,
    candidate_count: int,
    table_hit_count: int,
    keyword_candidate_count: int,
    semantic_candidate_count: int,
    metadata_candidate_count: int,
    span_candidate_count: int,
    top_results: list[SearchRequestExplanationResult],
) -> SearchRequestDiagnosis:
    evidence = {
        "requested_mode": requested_mode,
        "served_mode": served_mode,
        "embedding_status": embedding_status,
        "fallback_reason": fallback_reason,
        "candidate_count": candidate_count,
        "result_count": result_count,
        "table_hit_count": table_hit_count,
        "keyword_candidate_count": keyword_candidate_count,
        "semantic_candidate_count": semantic_candidate_count,
        "metadata_candidate_count": metadata_candidate_count,
        "span_candidate_count": span_candidate_count,
        "filters": filters,
    }

    if fallback_reason or (
        requested_mode in {"semantic", "hybrid"}
        and served_mode == "keyword"
        and embedding_status != "completed"
    ):
        return SearchRequestDiagnosis(
            category="fallback_only",
            summary=(
                "The request was served through a fallback path rather than the requested "
                "semantic-capable mode."
            ),
            contributing_factors=[
                "Semantic execution was unavailable or intentionally bypassed.",
                "Ranking quality is limited to keyword-backed evidence for this request.",
            ],
            evidence=evidence,
        )

    if filters and candidate_count == 0 and result_count == 0:
        return SearchRequestDiagnosis(
            category="filter_overconstraint",
            summary="The request produced no candidates after filters were applied.",
            contributing_factors=[
                "The request has filters and no persisted candidates.",
                "A page, document, or result-type constraint may be excluding expected evidence.",
            ],
            evidence=evidence,
        )

    if tabular_query and table_hit_count == 0:
        return SearchRequestDiagnosis(
            category="table_recall_gap",
            summary="The query looks table-oriented but no table results were returned.",
            contributing_factors=[
                "The persisted request is marked as tabular.",
                "No table hits survived candidate generation and reranking.",
            ],
            evidence=evidence,
        )

    if candidate_count == 0 or result_count == 0:
        return SearchRequestDiagnosis(
            category="low_recall",
            summary="The request produced too little candidate evidence to answer reliably.",
            contributing_factors=[
                "The candidate or final result count is zero.",
                "Recall should be investigated before tuning final ranking.",
            ],
            evidence=evidence,
        )

    if metadata_candidate_count > 0 and metadata_candidate_count >= max(
        keyword_candidate_count, semantic_candidate_count
    ):
        return SearchRequestDiagnosis(
            category="metadata_bias",
            summary="Metadata supplement candidates dominate the observed candidate mix.",
            contributing_factors=[
                (
                    "Metadata-sourced candidates are a large share of the persisted "
                    "candidate evidence."
                ),
                (
                    "The request may be relying on filename, title, or heading matches "
                    "more than body evidence."
                ),
            ],
            evidence=evidence,
        )

    if tabular_query and top_results and top_results[0].result_type != "table" and table_hit_count:
        return SearchRequestDiagnosis(
            category="bad_ranking",
            summary="The request found table evidence but ranked non-table evidence first.",
            contributing_factors=[
                "The query is tabular and at least one table result exists.",
                "The top result is not a table, so reranking may be suppressing the expected type.",
            ],
            evidence=evidence,
        )

    return SearchRequestDiagnosis(
        category="healthy",
        summary="The persisted telemetry does not expose an obvious recall or fallback failure.",
        contributing_factors=[
            "The request returned results.",
            "Candidate generation and serving mode look consistent with the request.",
        ],
        evidence=evidence,
    )


def _recommended_next_action(category: str) -> str:
    if category == "fallback_only":
        return "Inspect embedding availability, quota, and fallback policy before changing ranking."
    if category == "filter_overconstraint":
        return "Replay with relaxed filters or inspect the filter contract for this query."
    if category == "table_recall_gap":
        return "Inspect table candidate generation and table-aware reranker knobs."
    if category == "low_recall":
        return "Increase recall evidence first; avoid ranking-only changes until candidates exist."
    if category == "metadata_bias":
        return "Compare metadata supplement behavior against body-text and table evidence."
    if category == "bad_ranking":
        return "Verify whether reranker weights should promote the expected result type."
    return "No repair action is implied by this request alone; use replay or evaluation evidence."


def get_search_request_explanation(
    session: Session,
    search_request_id: UUID,
) -> SearchRequestExplanationResponse:
    detail = get_search_request_detail(session, search_request_id)
    details = detail.details or {}
    requested_mode = str(details.get("requested_mode") or detail.mode)
    served_mode = str(details.get("served_mode") or detail.mode)
    fallback_reason = details.get("fallback_reason")
    top_results = _top_result_snapshot(detail.results)
    diagnosis = _diagnose_search_request(
        requested_mode=requested_mode,
        served_mode=served_mode,
        fallback_reason=str(fallback_reason) if fallback_reason is not None else None,
        embedding_status=detail.embedding_status,
        filters=detail.filters,
        tabular_query=detail.tabular_query,
        result_count=detail.result_count,
        candidate_count=detail.candidate_count,
        table_hit_count=detail.table_hit_count,
        keyword_candidate_count=int(details.get("keyword_candidate_count") or 0),
        semantic_candidate_count=int(details.get("semantic_candidate_count") or 0),
        metadata_candidate_count=int(details.get("metadata_candidate_count") or 0),
        span_candidate_count=int(details.get("span_candidate_count") or 0),
        top_results=top_results,
    )
    return SearchRequestExplanationResponse(
        search_request_id=detail.search_request_id,
        parent_search_request_id=detail.parent_search_request_id,
        evaluation_id=detail.evaluation_id,
        run_id=detail.run_id,
        origin=detail.origin,
        query=detail.query,
        mode=detail.mode,
        filters=detail.filters,
        requested_mode=requested_mode,
        served_mode=served_mode,
        limit=detail.limit,
        tabular_query=detail.tabular_query,
        harness_name=detail.harness_name,
        reranker_name=detail.reranker_name,
        reranker_version=detail.reranker_version,
        retrieval_profile_name=detail.retrieval_profile_name,
        harness_config=detail.harness_config,
        embedding_status=detail.embedding_status,
        embedding_error=detail.embedding_error,
        fallback_reason=str(fallback_reason) if fallback_reason is not None else None,
        keyword_candidate_count=int(details.get("keyword_candidate_count") or 0),
        keyword_strict_candidate_count=int(details.get("keyword_strict_candidate_count") or 0),
        semantic_candidate_count=int(details.get("semantic_candidate_count") or 0),
        metadata_candidate_count=int(details.get("metadata_candidate_count") or 0),
        span_candidate_count=int(details.get("span_candidate_count") or 0),
        context_expansion_count=int(details.get("context_expansion_count") or 0),
        candidate_count=detail.candidate_count,
        result_count=detail.result_count,
        table_hit_count=detail.table_hit_count,
        candidate_source_breakdown=details.get("candidate_source_breakdown") or {},
        query_understanding={
            "query_intent": details.get("query_intent"),
            "keyword_strategy": details.get("keyword_strategy"),
            "tabular_query": detail.tabular_query,
            "semantic_augmented_with_keyword_context": bool(
                details.get("semantic_augmented_with_keyword_context")
            ),
            "span_candidate_count": int(details.get("span_candidate_count") or 0),
        },
        top_result_snapshot=top_results,
        diagnosis=diagnosis,
        recommended_next_action=_recommended_next_action(diagnosis.category),
        evidence_refs=[
            {
                "ref_kind": "search_request",
                "search_request_id": str(detail.search_request_id),
                "summary": "Persisted search request telemetry and logged result rows.",
            },
            {
                "ref_kind": "harness_config",
                "harness_name": detail.harness_name,
                "config_fingerprint": _payload_fingerprint(detail.harness_config),
                "summary": "Harness snapshot captured when the request executed.",
            },
        ],
        created_at=detail.created_at,
    )


def get_search_harness_descriptor(
    harness_name: str | None = None,
    *,
    harness_overrides: dict[str, dict] | None = None,
) -> SearchHarnessDescriptorResponse:
    harness = get_search_harness(harness_name, harness_overrides)
    config = harness.config_snapshot
    return SearchHarnessDescriptorResponse(
        harness_name=harness.name,
        base_harness_name=harness.base_harness_name,
        is_default=harness.name == DEFAULT_SEARCH_HARNESS_NAME,
        config_fingerprint=_payload_fingerprint(config),
        reranker_name=harness.reranker_name,
        reranker_version=harness.reranker_version,
        retrieval_profile_name=harness.retrieval_profile_name,
        retrieval_stages=[
            "keyword_candidates",
            "span_level_keyword_candidates",
            "semantic_candidates_when_embedding_available",
            "span_level_semantic_candidates_when_embedding_available",
            "metadata_supplement_for_selected_prose_queries",
            "adjacent_context_expansion",
            "linear_feature_reranking",
        ],
        tunable_knobs={
            "retrieval_profile_overrides": sorted(SEARCH_HARNESS_RETRIEVAL_OVERRIDE_FIELDS),
            "reranker_overrides": sorted(SEARCH_HARNESS_RERANKER_OVERRIDE_FIELDS),
        },
        constraints=[
            "Harness names are immutable after publication.",
            "Overrides must derive from an existing base harness.",
            "Draft overrides must pass replay verification before approval-gated apply.",
            "Evaluation corpus weakening is not a valid repair.",
        ],
        intended_query_families=[
            "evaluation_queries",
            "feedback",
            "live_search_gaps",
            "cross_document_prose_regressions",
        ],
        known_tradeoffs=[
            "Increasing candidate multipliers improves recall but raises latency.",
            "Table bonuses can improve tabular retrieval while risking prose-result demotion.",
            (
                "Metadata supplements can recover document-level prose lookups but may bias "
                "toward titles or filenames."
            ),
        ],
        harness_config=config,
        metadata=harness.metadata,
    )
