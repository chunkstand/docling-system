from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy.orm import Session

import app.services.search_ranking as _search_ranking
from app.core.time import utcnow
from app.db.public.retrieval import (
    SearchRequestRecord,
    SearchRequestResult,
    SearchRequestResultSpan,
)
from app.schemas.search import SearchRequest
from app.services.evidence_operator_runs import record_knowledge_operator_run

SEARCH_RESULT_SPAN_LIMIT = 5

RankedResult = _search_ranking.RankedResult
RerankedResult = _search_ranking.RerankedResult
_result_label = _search_ranking.result_label
_result_preview = _search_ranking.result_preview
_unique_uuid = _search_ranking.unique_uuid


def _evidence_spans_payload(item: RankedResult) -> list[dict]:
    return [
        {
            "retrieval_evidence_span_id": str(span.retrieval_evidence_span_id),
            "source_type": span.source_type,
            "source_id": str(span.source_id),
            "span_index": span.span_index,
            "score_kind": span.score_kind,
            "score": span.score,
            "page_from": span.page_from,
            "page_to": span.page_to,
            "text_excerpt": span.text_excerpt,
            "content_sha256": span.content_sha256,
            "source_snapshot_sha256": span.source_snapshot_sha256,
            "metadata": span.metadata,
        }
        for span in item.evidence_spans
    ]


def _ranked_result_evidence_payload(item: RankedResult, index: int) -> dict:
    return {
        "candidate_index": index,
        "result_type": item.result_type,
        "result_id": str(item.result_id),
        "document_id": str(item.document_id),
        "run_id": str(item.run_id),
        "source_filename": item.source_filename,
        "page_from": item.page_from,
        "page_to": item.page_to,
        "keyword_score": item.keyword_score,
        "semantic_score": item.semantic_score,
        "hybrid_score": item.hybrid_score,
        "retrieval_sources": list(item.retrieval_sources),
        "evidence_spans": _evidence_spans_payload(item),
        "label": _result_label(item),
    }


def _reranked_result_evidence_payload(
    candidate: RerankedResult,
    result_row: SearchRequestResult,
) -> dict:
    return {
        "search_request_result_id": str(result_row.id),
        "rank": candidate.rank,
        "base_rank": candidate.base_rank,
        "score": candidate.score,
        "result_type": candidate.item.result_type,
        "result_id": str(candidate.item.result_id),
        "document_id": str(candidate.item.document_id),
        "run_id": str(candidate.item.run_id),
        "page_from": candidate.item.page_from,
        "page_to": candidate.item.page_to,
        "source_filename": candidate.item.source_filename,
        "label": _result_label(candidate.item),
        "preview_text": _result_preview(candidate.item),
        "evidence_spans": _evidence_spans_payload(candidate.item),
        "features": candidate.features,
    }


def _persist_search_operator_runs(
    session: Session,
    *,
    search_request: SearchRequestRecord,
    request: SearchRequest,
    candidate_items: list[RankedResult],
    reranked_results: list[RerankedResult],
    result_rows: list[SearchRequestResult],
    details: dict,
    harness_config: dict,
    reranker_name: str,
    reranker_version: str,
    retrieval_profile_name: str,
    duration_ms: float,
) -> list[UUID]:
    candidate_payloads = [
        _ranked_result_evidence_payload(item, index)
        for index, item in enumerate(candidate_items, start=1)
    ]
    result_payloads = [
        _reranked_result_evidence_payload(candidate, result_row)
        for candidate, result_row in zip(reranked_results, result_rows, strict=True)
    ]
    document_id = _unique_uuid(item.document_id for item in candidate_items)
    run_id = _unique_uuid(item.run_id for item in candidate_items)
    request_payload = {
        "query": request.query,
        "mode": request.mode,
        "filters": (
            request.filters.model_dump(mode="json", exclude_none=True) if request.filters else {}
        ),
        "limit": request.limit,
        "harness_name": search_request.harness_name,
    }
    operator_run_ids: list[UUID] = []
    retrieve_run = record_knowledge_operator_run(
        session,
        operator_kind="retrieve",
        operator_name="search_candidate_generation",
        operator_version=retrieval_profile_name,
        document_id=document_id,
        run_id=run_id,
        search_request_id=search_request.id,
        config={
            "harness_name": search_request.harness_name,
            "retrieval_profile": harness_config.get("retrieval_profile", {}),
            "execution_details": {
                key: details.get(key)
                for key in (
                    "keyword_strategy",
                    "requested_mode",
                    "served_mode",
                    "query_intent",
                    "fallback_reason",
                )
                if key in details
            },
        },
        input_payload=request_payload,
        output_payload={"candidates": candidate_payloads},
        metrics={
            "candidate_count": len(candidate_payloads),
            "keyword_candidate_count": details.get("keyword_candidate_count", 0),
            "semantic_candidate_count": details.get("semantic_candidate_count", 0),
            "metadata_candidate_count": details.get("metadata_candidate_count", 0),
            "span_candidate_count": details.get("span_candidate_count", 0),
            "context_expansion_count": details.get("context_expansion_count", 0),
        },
        metadata={
            "candidate_source_breakdown": details.get("candidate_source_breakdown", {}),
            "search_request_id": str(search_request.id),
        },
        inputs=[
            {
                "input_kind": "search_request",
                "source_table": "search_requests",
                "source_id": search_request.id,
                "payload": request_payload,
            }
        ],
        outputs=[
            {
                "output_kind": "candidate_set",
                "payload": {
                    "candidate_count": len(candidate_payloads),
                    "candidates": candidate_payloads,
                },
            }
        ],
        duration_ms=duration_ms,
    )
    if retrieve_run is not None:
        operator_run_ids.append(retrieve_run.id)

    rerank_run = record_knowledge_operator_run(
        session,
        operator_kind="rerank",
        operator_name=reranker_name,
        operator_version=reranker_version,
        parent_operator_run_id=getattr(retrieve_run, "id", None),
        document_id=document_id,
        run_id=run_id,
        search_request_id=search_request.id,
        config=harness_config.get("reranker", {}),
        input_payload={"candidates": candidate_payloads},
        output_payload={"ranked_results": result_payloads},
        metrics={
            "candidate_count": len(candidate_payloads),
            "result_count": len(result_payloads),
            "table_hit_count": search_request.table_hit_count,
        },
        metadata={
            "harness_name": search_request.harness_name,
            "retrieval_profile_name": retrieval_profile_name,
        },
        inputs=[
            {
                "input_kind": "candidate_set",
                "source_table": "knowledge_operator_runs",
                "source_id": getattr(retrieve_run, "id", None),
                "payload": {
                    "candidate_count": len(candidate_payloads),
                },
            }
        ],
        outputs=[
            {
                "output_kind": "ranked_result",
                "target_table": "search_request_results",
                "target_id": result_row.id,
                "payload": payload,
            }
            for payload, result_row in zip(result_payloads, result_rows, strict=True)
        ],
        duration_ms=duration_ms,
    )
    if rerank_run is not None:
        operator_run_ids.append(rerank_run.id)

    judge_run = record_knowledge_operator_run(
        session,
        operator_kind="judge",
        operator_name="deterministic_evidence_selection",
        operator_version="v1",
        parent_operator_run_id=getattr(rerank_run, "id", None),
        document_id=document_id,
        run_id=run_id,
        search_request_id=search_request.id,
        config={
            "selection_policy": "top_k_after_rerank",
            "limit": request.limit,
            "harness_name": search_request.harness_name,
        },
        input_payload={"ranked_results": result_payloads},
        output_payload={"selected_results": result_payloads},
        metrics={
            "selected_result_count": len(result_payloads),
            "table_hit_count": search_request.table_hit_count,
        },
        metadata={
            "audit_role": "records which ranked evidence was selected for downstream use",
        },
        inputs=[
            {
                "input_kind": "ranked_results",
                "source_table": "knowledge_operator_runs",
                "source_id": getattr(rerank_run, "id", None),
                "payload": {"result_count": len(result_payloads)},
            }
        ],
        outputs=[
            {
                "output_kind": "selected_evidence",
                "target_table": "search_request_results",
                "target_id": result_row.id,
                "payload": payload,
            }
            for payload, result_row in zip(result_payloads, result_rows, strict=True)
        ],
        duration_ms=duration_ms,
    )
    if judge_run is not None:
        operator_run_ids.append(judge_run.id)
    return operator_run_ids


def _persist_search_result_spans(
    session: Session,
    *,
    search_request_id: UUID,
    reranked_results: list[RerankedResult],
    result_rows: list[SearchRequestResult],
    created_at,
) -> None:
    for candidate, result_row in zip(reranked_results, result_rows, strict=True):
        for span_rank, span in enumerate(
            candidate.item.evidence_spans[:SEARCH_RESULT_SPAN_LIMIT],
            start=1,
        ):
            session.add(
                SearchRequestResultSpan(
                    id=uuid.uuid4(),
                    search_request_id=search_request_id,
                    search_request_result_id=result_row.id,
                    retrieval_evidence_span_id=span.retrieval_evidence_span_id,
                    span_rank=span_rank,
                    score_kind=span.score_kind,
                    score=span.score,
                    source_type=span.source_type,
                    source_id=span.source_id,
                    span_index=span.span_index,
                    page_from=span.page_from,
                    page_to=span.page_to,
                    text_excerpt=span.text_excerpt,
                    content_sha256=span.content_sha256,
                    source_snapshot_sha256=span.source_snapshot_sha256,
                    metadata_json={
                        "retrieval_source_count": len(candidate.item.retrieval_sources),
                        "retrieval_sources": list(candidate.item.retrieval_sources),
                        **(span.metadata or {}),
                    },
                    created_at=created_at,
                )
            )
    session.flush()


def _persist_search_execution(
    session: Session | None,
    *,
    request: SearchRequest,
    origin: str,
    run_id: UUID | None,
    evaluation_id: UUID | None,
    parent_request_id: UUID | None,
    tabular_query: bool,
    harness_name: str,
    reranker_name: str,
    reranker_version: str,
    retrieval_profile_name: str,
    harness_config: dict,
    embedding_status: str,
    embedding_error: str | None,
    candidate_count: int,
    duration_ms: float,
    details: dict,
    candidate_items: list[RankedResult],
    reranked_results: list[RerankedResult],
) -> tuple[UUID | None, list[UUID]]:
    if session is None or not hasattr(session, "add"):
        return None, []

    created_at = utcnow()
    filters_payload = (
        request.filters.model_dump(mode="json", exclude_none=True) if request.filters else {}
    )
    search_request = SearchRequestRecord(
        id=uuid.uuid4(),
        parent_request_id=parent_request_id,
        evaluation_id=evaluation_id,
        run_id=run_id,
        origin=origin,
        query_text=request.query,
        mode=request.mode,
        filters_json=filters_payload,
        details_json=details,
        limit=request.limit,
        tabular_query=tabular_query,
        harness_name=harness_name,
        reranker_name=reranker_name,
        reranker_version=reranker_version,
        retrieval_profile_name=retrieval_profile_name,
        harness_config_json=harness_config,
        embedding_status=embedding_status,
        embedding_error=embedding_error,
        candidate_count=candidate_count,
        result_count=len(reranked_results),
        table_hit_count=sum(1 for item in reranked_results if item.item.result_type == "table"),
        duration_ms=duration_ms,
        created_at=created_at,
    )
    session.add(search_request)
    session.flush()

    result_rows: list[SearchRequestResult] = []
    for candidate in reranked_results:
        item = candidate.item
        result_row = SearchRequestResult(
            id=uuid.uuid4(),
            search_request_id=search_request.id,
            rank=candidate.rank,
            base_rank=candidate.base_rank,
            result_type=item.result_type,
            document_id=item.document_id,
            run_id=item.run_id,
            chunk_id=item.result_id if item.result_type == "chunk" else None,
            table_id=item.result_id if item.result_type == "table" else None,
            score=candidate.score,
            keyword_score=item.keyword_score,
            semantic_score=item.semantic_score,
            hybrid_score=item.hybrid_score,
            rerank_features_json=candidate.features,
            page_from=item.page_from,
            page_to=item.page_to,
            source_filename=item.source_filename,
            label=_result_label(item),
            preview_text=_result_preview(item),
            created_at=created_at,
        )
        result_rows.append(result_row)
        session.add(result_row)

    session.flush()
    _persist_search_result_spans(
        session,
        search_request_id=search_request.id,
        reranked_results=reranked_results,
        result_rows=result_rows,
        created_at=created_at,
    )
    operator_run_ids = _persist_search_operator_runs(
        session,
        search_request=search_request,
        request=request,
        candidate_items=candidate_items,
        reranked_results=reranked_results,
        result_rows=result_rows,
        details=details,
        harness_config=harness_config,
        reranker_name=reranker_name,
        reranker_version=reranker_version,
        retrieval_profile_name=retrieval_profile_name,
        duration_ms=duration_ms,
    )
    return search_request.id, operator_run_ids
