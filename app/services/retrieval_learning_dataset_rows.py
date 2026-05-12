from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import uuid_text as _uuid_text
from app.core.hashes import payload_sha256 as _payload_sha256
from app.core.json_utils import canonical_json_value as _json_payload
from app.db.models import (
    RetrievalJudgmentKind,
    SearchReplayQuery,
    SearchReplayRun,
    SearchRequestRecord,
    SearchRequestResult,
    SearchRequestResultSpan,
)


def result_source_id(row: SearchRequestResult | None) -> UUID | None:
    if row is None:
        return None
    return row.table_id if row.result_type == "table" else row.chunk_id


def result_fields(row: SearchRequestResult | None) -> dict[str, Any]:
    if row is None:
        return {
            "search_request_result_id": None,
            "result_rank": None,
            "result_type": None,
            "result_id": None,
            "document_id": None,
            "run_id": None,
            "score": None,
            "rerank_features": {},
        }
    return {
        "search_request_result_id": row.id,
        "result_rank": row.rank,
        "result_type": row.result_type,
        "result_id": result_source_id(row),
        "document_id": row.document_id,
        "run_id": row.run_id,
        "score": row.score,
        "keyword_score": row.keyword_score,
        "semantic_score": row.semantic_score,
        "hybrid_score": row.hybrid_score,
        "rerank_features": row.rerank_features_json or {},
        "source_filename": row.source_filename,
        "label": row.label,
        "preview_text": row.preview_text,
        "page_from": row.page_from,
        "page_to": row.page_to,
    }


def request_fields(row: SearchRequestRecord | None) -> dict[str, Any]:
    if row is None:
        return {
            "query_text": "",
            "mode": "hybrid",
            "filters": {},
            "harness_name": None,
            "reranker_name": None,
            "reranker_version": None,
            "retrieval_profile_name": None,
            "harness_config": {},
        }
    return {
        "query_text": row.query_text,
        "mode": row.mode,
        "filters": row.filters_json or {},
        "harness_name": row.harness_name,
        "reranker_name": row.reranker_name,
        "reranker_version": row.reranker_version,
        "retrieval_profile_name": row.retrieval_profile_name,
        "harness_config": row.harness_config_json or {},
    }


def replay_run_source_type(row: SearchReplayRun | None) -> str | None:
    if row is None:
        return None
    return (row.summary_json or {}).get("source_type") or row.source_type


def _result_matches_key(
    row: SearchRequestResult,
    result_type: str | None,
    result_id: UUID,
) -> bool:
    return row.result_type == result_type and result_source_id(row) == result_id


def target_result_from_details(
    replay_query: SearchReplayQuery,
    results: list[SearchRequestResult],
) -> SearchRequestResult | None:
    details = replay_query.details_json or {}
    matching_rank = details.get("matching_rank")
    if matching_rank is not None:
        try:
            rank = int(matching_rank)
        except (TypeError, ValueError):
            rank = 0
        if 0 < rank <= len(results):
            return results[rank - 1]

    target_key = details.get("target_key")
    if isinstance(target_key, list | tuple) and len(target_key) == 2:
        target_type, raw_target_id = target_key
        try:
            target_id = UUID(str(raw_target_id))
        except (TypeError, ValueError):
            return None
        for result in results:
            if _result_matches_key(result, target_type, target_id):
                return result
    return None


def group_results_by_request(
    session: Session,
    request_ids: set[UUID],
) -> dict[UUID, list[SearchRequestResult]]:
    if not request_ids:
        return {}
    grouped: dict[UUID, list[SearchRequestResult]] = defaultdict(list)
    rows = (
        session.execute(
            select(SearchRequestResult)
            .where(SearchRequestResult.search_request_id.in_(request_ids))
            .order_by(SearchRequestResult.search_request_id, SearchRequestResult.rank)
        )
        .scalars()
        .all()
    )
    for row in rows:
        grouped[row.search_request_id].append(row)
    return grouped


def evidence_refs_by_result_id(
    session: Session,
    result_ids: set[UUID],
) -> dict[UUID, list[dict[str, Any]]]:
    if not result_ids:
        return {}
    grouped: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
    rows = (
        session.execute(
            select(SearchRequestResultSpan)
            .where(SearchRequestResultSpan.search_request_result_id.in_(result_ids))
            .order_by(
                SearchRequestResultSpan.search_request_result_id,
                SearchRequestResultSpan.span_rank,
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        grouped[row.search_request_result_id].append(
            _json_payload(
                {
                    "search_request_result_span_id": row.id,
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
        )
    return grouped


def judgment_payload(row: dict[str, Any]) -> dict[str, Any]:
    return _json_payload(
        {
            "judgment_id": row["id"],
            "source_payload_sha256": row.get("source_payload_sha256"),
            "judgment_kind": row["judgment_kind"],
            "judgment_label": row["judgment_label"],
            "source": {
                "source_type": row["source_type"],
                "source_ref_id": row["source_ref_id"],
                "search_feedback_id": row.get("search_feedback_id"),
                "search_replay_query_id": row.get("search_replay_query_id"),
                "search_replay_run_id": row.get("search_replay_run_id"),
                "evaluation_query_id": row.get("evaluation_query_id"),
                "source_search_request_id": row.get("source_search_request_id"),
                "search_request_id": row.get("search_request_id"),
                "search_request_result_id": row.get("search_request_result_id"),
            },
            "query": {
                "query_text": row["query_text"],
                "mode": row["mode"],
                "filters": row["filters_json"],
                "expected_result_type": row.get("expected_result_type"),
                "expected_top_n": row.get("expected_top_n"),
            },
            "retrieval_context": {
                "harness_name": row.get("harness_name"),
                "reranker_name": row.get("reranker_name"),
                "reranker_version": row.get("reranker_version"),
                "retrieval_profile_name": row.get("retrieval_profile_name"),
            },
            "result": {
                "rank": row.get("result_rank"),
                "result_type": row.get("result_type"),
                "result_id": row.get("result_id"),
                "document_id": row.get("document_id"),
                "run_id": row.get("run_id"),
                "score": row.get("score"),
                "rerank_features": row.get("rerank_features_json") or {},
                "evidence_refs": row.get("evidence_refs_json") or [],
            },
            "rationale": row.get("rationale"),
            "details": row.get("payload_json") or {},
            "deduplication_key": row["deduplication_key"],
        }
    )


def hard_negative_payload(row: dict[str, Any]) -> dict[str, Any]:
    return _json_payload(
        {
            "hard_negative_id": row["id"],
            "source_payload_sha256": row.get("source_payload_sha256"),
            "judgment_id": row["judgment_id"],
            "positive_judgment_id": row.get("positive_judgment_id"),
            "hard_negative_kind": row["hard_negative_kind"],
            "source": {
                "source_type": row["source_type"],
                "source_ref_id": row.get("source_ref_id"),
                "search_feedback_id": row.get("search_feedback_id"),
                "search_replay_query_id": row.get("search_replay_query_id"),
                "search_replay_run_id": row.get("search_replay_run_id"),
                "evaluation_query_id": row.get("evaluation_query_id"),
                "source_search_request_id": row.get("source_search_request_id"),
                "search_request_id": row.get("search_request_id"),
                "search_request_result_id": row.get("search_request_result_id"),
            },
            "query": {
                "query_text": row["query_text"],
                "mode": row["mode"],
                "filters": row["filters_json"],
                "expected_result_type": row.get("expected_result_type"),
                "expected_top_n": row.get("expected_top_n"),
            },
            "result": {
                "rank": row.get("result_rank"),
                "result_type": row.get("result_type"),
                "result_id": row.get("result_id"),
                "document_id": row.get("document_id"),
                "run_id": row.get("run_id"),
                "score": row.get("score"),
                "rerank_features": row.get("rerank_features_json") or {},
                "evidence_refs": row.get("evidence_refs_json") or [],
            },
            "reason": row["reason"],
            "details": row.get("details_json") or {},
            "deduplication_key": row["deduplication_key"],
        }
    )


def _judgment_source_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload = judgment_payload(row)
    payload.pop("judgment_id", None)
    payload.pop("source_payload_sha256", None)
    payload.pop("deduplication_key", None)
    if isinstance(payload.get("details"), dict):
        payload["details"].pop("source_payload_sha256", None)
    return payload


def _hard_negative_source_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload = hard_negative_payload(row)
    payload.pop("hard_negative_id", None)
    payload.pop("source_payload_sha256", None)
    payload.pop("judgment_id", None)
    payload.pop("positive_judgment_id", None)
    payload.pop("deduplication_key", None)
    if isinstance(payload.get("details"), dict):
        payload["details"].pop("source_payload_sha256", None)
    return payload


def _query_signature(row: dict[str, Any]) -> str:
    return json.dumps(
        _json_payload(
            {
                "query_text": row["query_text"],
                "mode": row["mode"],
                "filters": row.get("filters_json") or {},
            }
        ),
        sort_keys=True,
        separators=(",", ":"),
    )


def finalize_judgment_source_hashes(judgments: list[dict[str, Any]]) -> None:
    for row in judgments:
        row["source_payload_sha256"] = _payload_sha256(_judgment_source_payload(row))
        row["payload_json"] = {
            **(row.get("payload_json") or {}),
            "source_payload_sha256": row["source_payload_sha256"],
        }


def pair_hard_negatives_with_positive_judgments(
    judgments: list[dict[str, Any]],
    hard_negatives: list[dict[str, Any]],
) -> None:
    positives_by_query: dict[str, dict[str, Any]] = {}
    for judgment in judgments:
        if judgment["judgment_kind"] != RetrievalJudgmentKind.POSITIVE.value:
            continue
        positives_by_query.setdefault(_query_signature(judgment), judgment)

    for hard_negative in hard_negatives:
        positive = positives_by_query.get(_query_signature(hard_negative))
        if positive is None:
            continue
        hard_negative["positive_judgment_id"] = positive["id"]
        hard_negative["details_json"] = {
            **(hard_negative.get("details_json") or {}),
            "positive_source_payload_sha256": positive.get("source_payload_sha256"),
            "positive_result_type": positive.get("result_type"),
            "positive_result_id": _uuid_text(positive.get("result_id")),
        }


def finalize_hard_negative_source_hashes(hard_negatives: list[dict[str, Any]]) -> None:
    for row in hard_negatives:
        row["source_payload_sha256"] = _payload_sha256(_hard_negative_source_payload(row))
        row["details_json"] = {
            **(row.get("details_json") or {}),
            "source_payload_sha256": row["source_payload_sha256"],
        }


def make_judgment_row(
    *,
    judgment_set_id: UUID,
    source_type: str,
    source_ref_id: UUID,
    judgment_kind: str,
    judgment_label: str,
    query: dict[str, Any],
    result: SearchRequestResult | None,
    evidence_refs: list[dict[str, Any]],
    created_at: datetime,
    rationale: str,
    search_feedback_id: UUID | None = None,
    search_replay_query_id: UUID | None = None,
    search_replay_run_id: UUID | None = None,
    evaluation_query_id: UUID | None = None,
    source_search_request_id: UUID | None = None,
    search_request_id: UUID | None = None,
    expected_result_type: str | None = None,
    expected_top_n: int | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row_id = uuid.uuid4()
    result_data = result_fields(result)
    request_result_id = result_data["search_request_result_id"]
    effective_search_request_id = search_request_id
    if effective_search_request_id is None and result is not None:
        effective_search_request_id = result.search_request_id
    deduplication_key = ":".join(
        [
            str(judgment_set_id),
            "judgment",
            source_type,
            str(source_ref_id),
            judgment_kind,
            judgment_label,
            str(request_result_id or "no-result"),
        ]
    )
    return {
        "id": row_id,
        "judgment_set_id": judgment_set_id,
        "judgment_kind": judgment_kind,
        "judgment_label": judgment_label,
        "source_type": source_type,
        "source_ref_id": source_ref_id,
        "search_feedback_id": search_feedback_id,
        "search_replay_query_id": search_replay_query_id,
        "search_replay_run_id": search_replay_run_id,
        "evaluation_query_id": evaluation_query_id,
        "source_search_request_id": source_search_request_id,
        "search_request_id": effective_search_request_id,
        "search_request_result_id": request_result_id,
        "result_rank": result_data["result_rank"],
        "result_type": result_data["result_type"],
        "result_id": result_data["result_id"],
        "document_id": result_data["document_id"],
        "run_id": result_data["run_id"],
        "score": result_data["score"],
        "query_text": query["query_text"],
        "mode": query["mode"],
        "filters_json": query["filters"],
        "expected_result_type": expected_result_type,
        "expected_top_n": expected_top_n,
        "harness_name": query.get("harness_name"),
        "reranker_name": query.get("reranker_name"),
        "reranker_version": query.get("reranker_version"),
        "retrieval_profile_name": query.get("retrieval_profile_name"),
        "rerank_features_json": result_data["rerank_features"],
        "evidence_refs_json": evidence_refs,
        "rationale": rationale,
        "payload_json": _json_payload(
            {
                "source_details": details or {},
                "result_details": {
                    key: value
                    for key, value in result_data.items()
                    if key
                    not in {
                        "search_request_result_id",
                        "result_rank",
                        "result_type",
                        "result_id",
                        "document_id",
                        "run_id",
                        "score",
                        "rerank_features",
                    }
                },
                "harness_config": query.get("harness_config") or {},
            }
        ),
        "source_payload_sha256": None,
        "deduplication_key": deduplication_key,
        "created_at": created_at,
    }


def make_hard_negative_row(
    *,
    judgment_set_id: UUID,
    judgment_id: UUID,
    hard_negative_kind: str,
    source_type: str,
    source_ref_id: UUID,
    query: dict[str, Any],
    result: SearchRequestResult,
    created_at: datetime,
    reason: str,
    search_feedback_id: UUID | None = None,
    search_replay_query_id: UUID | None = None,
    search_replay_run_id: UUID | None = None,
    evaluation_query_id: UUID | None = None,
    source_search_request_id: UUID | None = None,
    expected_result_type: str | None = None,
    expected_top_n: int | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
    details: dict[str, Any] | None = None,
    positive_judgment_id: UUID | None = None,
) -> dict[str, Any]:
    row_id = uuid.uuid4()
    result_data = result_fields(result)
    deduplication_key = ":".join(
        [
            str(judgment_set_id),
            "hard-negative",
            source_type,
            str(source_ref_id),
            hard_negative_kind,
            str(result_data["search_request_result_id"]),
        ]
    )
    return {
        "id": row_id,
        "judgment_set_id": judgment_set_id,
        "judgment_id": judgment_id,
        "positive_judgment_id": positive_judgment_id,
        "hard_negative_kind": hard_negative_kind,
        "source_type": source_type,
        "source_ref_id": source_ref_id,
        "search_feedback_id": search_feedback_id,
        "search_replay_query_id": search_replay_query_id,
        "search_replay_run_id": search_replay_run_id,
        "evaluation_query_id": evaluation_query_id,
        "source_search_request_id": source_search_request_id,
        "search_request_id": result.search_request_id,
        "search_request_result_id": result_data["search_request_result_id"],
        "result_rank": result_data["result_rank"],
        "result_type": result_data["result_type"],
        "result_id": result_data["result_id"],
        "document_id": result_data["document_id"],
        "run_id": result_data["run_id"],
        "score": result_data["score"],
        "query_text": query["query_text"],
        "mode": query["mode"],
        "filters_json": query["filters"],
        "rerank_features_json": result_data["rerank_features"],
        "expected_result_type": expected_result_type,
        "expected_top_n": expected_top_n,
        "evidence_refs_json": evidence_refs or [],
        "reason": reason,
        "details_json": _json_payload(
            {
                "source_details": details or {},
                "result_details": {
                    key: value
                    for key, value in result_data.items()
                    if key
                    not in {
                        "search_request_result_id",
                        "result_rank",
                        "result_type",
                        "result_id",
                        "document_id",
                        "run_id",
                        "score",
                        "rerank_features",
                    }
                },
                "harness_config": query.get("harness_config") or {},
            }
        ),
        "source_payload_sha256": None,
        "deduplication_key": deduplication_key,
        "created_at": created_at,
    }
