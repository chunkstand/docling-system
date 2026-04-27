from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import (
    RetrievalHardNegative,
    RetrievalHardNegativeKind,
    RetrievalJudgment,
    RetrievalJudgmentKind,
    RetrievalJudgmentSet,
    RetrievalTrainingRun,
    RetrievalTrainingRunStatus,
    SearchFeedback,
    SearchReplayQuery,
    SearchReplayRun,
    SearchRequestRecord,
    SearchRequestResult,
    SearchRequestResultSpan,
    SemanticGovernanceEventKind,
)
from app.services.semantic_governance import record_semantic_governance_event

RETRIEVAL_LEARNING_DATASET_SCHEMA = "retrieval_learning_dataset"
RETRIEVAL_LEARNING_DATASET_SCHEMA_VERSION = "1.0"
RETRIEVAL_LEARNING_SOURCES = {"feedback", "replay"}


def _json_default(value: Any) -> str:
    if isinstance(value, UUID | datetime | date):
        return value.isoformat() if hasattr(value, "isoformat") else str(value)
    return str(value)


def _json_payload(payload: Any) -> Any:
    return json.loads(json.dumps(payload, default=_json_default, sort_keys=True))


def _payload_sha256(payload: Any) -> str:
    raw = json.dumps(
        _json_payload(payload),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _uuid_text(value: UUID | None) -> str | None:
    return str(value) if value is not None else None


def _normalize_source_types(source_types: list[str] | tuple[str, ...] | None) -> list[str]:
    if source_types is None:
        return ["feedback", "replay"]
    normalized = []
    for source_type in source_types:
        if source_type not in RETRIEVAL_LEARNING_SOURCES:
            raise ValueError(f"Unsupported retrieval learning source_type: {source_type}.")
        if source_type not in normalized:
            normalized.append(source_type)
    if not normalized:
        raise ValueError("At least one retrieval learning source_type is required.")
    return normalized


def _set_kind(source_types: list[str]) -> str:
    if len(source_types) == 1:
        return source_types[0]
    return "mixed"


def _load_by_ids(session: Session, model, ids: set[UUID]) -> dict[UUID, Any]:
    if not ids:
        return {}
    return {
        row.id: row
        for row in session.execute(select(model).where(model.id.in_(ids))).scalars().all()
    }


def _result_source_id(row: SearchRequestResult | None) -> UUID | None:
    if row is None:
        return None
    return row.table_id if row.result_type == "table" else row.chunk_id


def _result_fields(row: SearchRequestResult | None) -> dict[str, Any]:
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
        "result_id": _result_source_id(row),
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


def _request_fields(row: SearchRequestRecord | None) -> dict[str, Any]:
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


def _replay_run_source_type(row: SearchReplayRun | None) -> str | None:
    if row is None:
        return None
    return (row.summary_json or {}).get("source_type") or row.source_type


def _result_matches_key(row: SearchRequestResult, result_type: str | None, result_id: UUID) -> bool:
    return row.result_type == result_type and _result_source_id(row) == result_id


def _target_result_from_details(
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


def _group_results_by_request(
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


def _evidence_refs_by_result_id(
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


def _judgment_payload(row: dict[str, Any]) -> dict[str, Any]:
    return _json_payload(
        {
            "judgment_id": row["id"],
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


def _hard_negative_payload(row: dict[str, Any]) -> dict[str, Any]:
    return _json_payload(
        {
            "hard_negative_id": row["id"],
            "judgment_id": row["judgment_id"],
            "positive_judgment_id": row.get("positive_judgment_id"),
            "hard_negative_kind": row["hard_negative_kind"],
            "source": {
                "source_type": row["source_type"],
                "source_ref_id": row.get("source_ref_id"),
                "search_feedback_id": row.get("search_feedback_id"),
                "search_replay_query_id": row.get("search_replay_query_id"),
                "search_request_id": row.get("search_request_id"),
                "search_request_result_id": row.get("search_request_result_id"),
            },
            "query": {
                "query_text": row["query_text"],
                "mode": row["mode"],
                "filters": row["filters_json"],
            },
            "result": {
                "rank": row.get("result_rank"),
                "result_type": row.get("result_type"),
                "result_id": row.get("result_id"),
                "document_id": row.get("document_id"),
                "run_id": row.get("run_id"),
                "score": row.get("score"),
                "rerank_features": row.get("rerank_features_json") or {},
            },
            "reason": row["reason"],
            "details": row.get("details_json") or {},
            "deduplication_key": row["deduplication_key"],
        }
    )


def _make_judgment_row(
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
    result_data = _result_fields(result)
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
    row = {
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
        "deduplication_key": deduplication_key,
        "created_at": created_at,
    }
    row["payload_json"] = {
        **row["payload_json"],
        "judgment_payload_sha256": _payload_sha256(_judgment_payload(row)),
    }
    return row


def _make_hard_negative_row(
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
    details: dict[str, Any] | None = None,
    positive_judgment_id: UUID | None = None,
) -> dict[str, Any]:
    row_id = uuid.uuid4()
    result_data = _result_fields(result)
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
        "deduplication_key": deduplication_key,
        "created_at": created_at,
    }


def _collect_feedback_sources(
    session: Session,
    *,
    judgment_set_id: UUID,
    limit: int,
    created_at: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    feedback_rows = (
        session.execute(
            select(SearchFeedback).order_by(SearchFeedback.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )
    request_ids = {row.search_request_id for row in feedback_rows}
    result_ids = {
        row.search_request_result_id
        for row in feedback_rows
        if row.search_request_result_id is not None
    }
    requests_by_id = _load_by_ids(session, SearchRequestRecord, request_ids)
    results_by_id = _load_by_ids(session, SearchRequestResult, result_ids)
    results_by_request_id = _group_results_by_request(session, request_ids)
    evidence_by_result_id = _evidence_refs_by_result_id(session, result_ids)

    judgments: list[dict[str, Any]] = []
    hard_negatives: list[dict[str, Any]] = []

    for feedback in feedback_rows:
        request = requests_by_id.get(feedback.search_request_id)
        query = _request_fields(request)
        result = results_by_id.get(feedback.search_request_result_id)
        evidence_refs = evidence_by_result_id.get(feedback.search_request_result_id, [])
        if feedback.feedback_type == "relevant":
            kind = RetrievalJudgmentKind.POSITIVE.value
            label = "operator_relevant"
            rationale = "Operator marked this retrieved result as relevant."
        elif feedback.feedback_type == "irrelevant":
            kind = RetrievalJudgmentKind.NEGATIVE.value
            label = "operator_irrelevant"
            rationale = "Operator marked this retrieved result as irrelevant."
        else:
            kind = RetrievalJudgmentKind.MISSING.value
            label = f"operator_{feedback.feedback_type}"
            rationale = "Operator marked the search as missing expected retrieval evidence."

        judgment = _make_judgment_row(
            judgment_set_id=judgment_set_id,
            source_type="feedback",
            source_ref_id=feedback.id,
            judgment_kind=kind,
            judgment_label=label,
            query=query,
            result=result,
            evidence_refs=evidence_refs,
            created_at=created_at,
            rationale=rationale,
            search_feedback_id=feedback.id,
            source_search_request_id=feedback.search_request_id,
            search_request_id=feedback.search_request_id,
            expected_result_type=(
                "table"
                if feedback.feedback_type == "missing_table"
                else "chunk"
                if feedback.feedback_type == "missing_chunk"
                else None
            ),
            details={
                "feedback_type": feedback.feedback_type,
                "note": feedback.note,
                "result_rank": feedback.result_rank,
                "feedback_created_at": feedback.created_at,
            },
        )
        judgments.append(judgment)

        if feedback.feedback_type == "irrelevant" and result is not None:
            hard_negatives.append(
                _make_hard_negative_row(
                    judgment_set_id=judgment_set_id,
                    judgment_id=judgment["id"],
                    hard_negative_kind=RetrievalHardNegativeKind.EXPLICIT_IRRELEVANT.value,
                    source_type="feedback",
                    source_ref_id=feedback.id,
                    query=query,
                    result=result,
                    created_at=created_at,
                    reason="Operator explicitly marked the result irrelevant.",
                    search_feedback_id=feedback.id,
                    details={"feedback_type": feedback.feedback_type, "note": feedback.note},
                )
            )
            continue

        top_results = results_by_request_id.get(feedback.search_request_id, [])[:3]
        if feedback.feedback_type in {"missing_table", "missing_chunk"}:
            expected_type = "table" if feedback.feedback_type == "missing_table" else "chunk"
            for candidate in top_results:
                if candidate.result_type == expected_type:
                    continue
                hard_negatives.append(
                    _make_hard_negative_row(
                        judgment_set_id=judgment_set_id,
                        judgment_id=judgment["id"],
                        hard_negative_kind=RetrievalHardNegativeKind.WRONG_RESULT_TYPE.value,
                        source_type="feedback",
                        source_ref_id=feedback.id,
                        query=query,
                        result=candidate,
                        created_at=created_at,
                        reason=f"Expected {expected_type} evidence was missing before this result.",
                        search_feedback_id=feedback.id,
                        details={
                            "feedback_type": feedback.feedback_type,
                            "note": feedback.note,
                            "expected_result_type": expected_type,
                        },
                    )
                )
        elif feedback.feedback_type == "no_answer":
            for candidate in top_results:
                hard_negatives.append(
                    _make_hard_negative_row(
                        judgment_set_id=judgment_set_id,
                        judgment_id=judgment["id"],
                        hard_negative_kind=RetrievalHardNegativeKind.NO_ANSWER_RETURNED.value,
                        source_type="feedback",
                        source_ref_id=feedback.id,
                        query=query,
                        result=candidate,
                        created_at=created_at,
                        reason="Operator indicated the query should not have returned an answer.",
                        search_feedback_id=feedback.id,
                        details={"feedback_type": feedback.feedback_type, "note": feedback.note},
                    )
                )

    return judgments, hard_negatives


def _collect_replay_sources(
    session: Session,
    *,
    judgment_set_id: UUID,
    limit: int,
    created_at: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    replay_queries = (
        session.execute(
            select(SearchReplayQuery).order_by(SearchReplayQuery.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )
    replay_run_ids = {row.replay_run_id for row in replay_queries}
    replay_request_ids = {
        row.replay_search_request_id
        for row in replay_queries
        if row.replay_search_request_id is not None
    }
    source_request_ids = {
        row.source_search_request_id
        for row in replay_queries
        if row.source_search_request_id is not None
    }
    replay_runs_by_id = _load_by_ids(session, SearchReplayRun, replay_run_ids)
    replay_requests_by_id = _load_by_ids(session, SearchRequestRecord, replay_request_ids)
    source_requests_by_id = _load_by_ids(session, SearchRequestRecord, source_request_ids)
    results_by_request_id = _group_results_by_request(session, replay_request_ids)
    result_ids = {
        result.id
        for results in results_by_request_id.values()
        for result in results
    }
    evidence_by_result_id = _evidence_refs_by_result_id(session, result_ids)

    judgments: list[dict[str, Any]] = []
    hard_negatives: list[dict[str, Any]] = []

    for replay_query in replay_queries:
        replay_run = replay_runs_by_id.get(replay_query.replay_run_id)
        replay_request = replay_requests_by_id.get(replay_query.replay_search_request_id)
        source_request = source_requests_by_id.get(replay_query.source_search_request_id)
        query = _request_fields(replay_request or source_request)
        if not query["query_text"]:
            query = {
                **query,
                "query_text": replay_query.query_text,
                "mode": replay_query.mode,
                "filters": replay_query.filters_json or {},
            }
        if replay_run is not None:
            query = {
                **query,
                "harness_name": replay_run.harness_name,
                "reranker_name": replay_run.reranker_name,
                "reranker_version": replay_run.reranker_version,
                "retrieval_profile_name": replay_run.retrieval_profile_name,
                "harness_config": replay_run.harness_config_json or {},
            }

        replay_results = results_by_request_id.get(replay_query.replay_search_request_id, [])
        details = replay_query.details_json or {}
        feedback_type = details.get("feedback_type")
        source_details = {
            "replay_source_type": _replay_run_source_type(replay_run),
            "passed": replay_query.passed,
            "result_count": replay_query.result_count,
            "table_hit_count": replay_query.table_hit_count,
            "overlap_count": replay_query.overlap_count,
            "added_count": replay_query.added_count,
            "removed_count": replay_query.removed_count,
            "top_result_changed": replay_query.top_result_changed,
            "max_rank_shift": replay_query.max_rank_shift,
            "details": details,
        }

        if replay_query.passed:
            result = _target_result_from_details(replay_query, replay_results)
            if result is None and replay_query.result_count == 0 and feedback_type == "no_answer":
                kind = RetrievalJudgmentKind.NEGATIVE.value
                label = "replay_expected_no_answer"
                rationale = "Replay passed because the query correctly returned no answer."
            elif result is None:
                kind = RetrievalJudgmentKind.MISSING.value
                label = "replay_passed_without_result_reference"
                rationale = "Replay passed but did not expose a specific matching result."
            else:
                kind = RetrievalJudgmentKind.POSITIVE.value
                label = "replay_passed_expected_result"
                rationale = "Replay found the expected result within the evaluation target."
            evidence_refs = evidence_by_result_id.get(getattr(result, "id", None), [])
            judgments.append(
                _make_judgment_row(
                    judgment_set_id=judgment_set_id,
                    source_type="replay",
                    source_ref_id=replay_query.id,
                    judgment_kind=kind,
                    judgment_label=label,
                    query=query,
                    result=result,
                    evidence_refs=evidence_refs,
                    created_at=created_at,
                    rationale=rationale,
                    search_feedback_id=replay_query.feedback_id,
                    search_replay_query_id=replay_query.id,
                    search_replay_run_id=replay_query.replay_run_id,
                    evaluation_query_id=replay_query.evaluation_query_id,
                    source_search_request_id=replay_query.source_search_request_id,
                    search_request_id=replay_query.replay_search_request_id,
                    expected_result_type=replay_query.expected_result_type,
                    expected_top_n=replay_query.expected_top_n,
                    details=source_details,
                )
            )
            continue

        result = replay_results[0] if replay_results else None
        if result is None:
            judgment = _make_judgment_row(
                judgment_set_id=judgment_set_id,
                source_type="replay",
                source_ref_id=replay_query.id,
                judgment_kind=RetrievalJudgmentKind.MISSING.value,
                judgment_label="replay_no_results",
                query=query,
                result=None,
                evidence_refs=[],
                created_at=created_at,
                rationale="Replay failed because no results were returned.",
                search_feedback_id=replay_query.feedback_id,
                search_replay_query_id=replay_query.id,
                search_replay_run_id=replay_query.replay_run_id,
                evaluation_query_id=replay_query.evaluation_query_id,
                source_search_request_id=replay_query.source_search_request_id,
                search_request_id=replay_query.replay_search_request_id,
                expected_result_type=replay_query.expected_result_type,
                expected_top_n=replay_query.expected_top_n,
                details=source_details,
            )
            judgments.append(judgment)
            continue

        if feedback_type == "no_answer":
            negative_kind = RetrievalHardNegativeKind.NO_ANSWER_RETURNED.value
        elif (
            replay_query.expected_result_type
            and result.result_type != replay_query.expected_result_type
        ):
            negative_kind = RetrievalHardNegativeKind.WRONG_RESULT_TYPE.value
        else:
            negative_kind = RetrievalHardNegativeKind.FAILED_REPLAY_TOP_RESULT.value
        judgment = _make_judgment_row(
            judgment_set_id=judgment_set_id,
            source_type="replay",
            source_ref_id=replay_query.id,
            judgment_kind=RetrievalJudgmentKind.NEGATIVE.value,
            judgment_label="replay_failed_top_result",
            query=query,
            result=result,
            evidence_refs=evidence_by_result_id.get(result.id, []),
            created_at=created_at,
            rationale="Replay failed; the top result is a mined hard negative.",
            search_feedback_id=replay_query.feedback_id,
            search_replay_query_id=replay_query.id,
            search_replay_run_id=replay_query.replay_run_id,
            evaluation_query_id=replay_query.evaluation_query_id,
            source_search_request_id=replay_query.source_search_request_id,
            search_request_id=replay_query.replay_search_request_id,
            expected_result_type=replay_query.expected_result_type,
            expected_top_n=replay_query.expected_top_n,
            details=source_details,
        )
        judgments.append(judgment)
        hard_negatives.append(
            _make_hard_negative_row(
                judgment_set_id=judgment_set_id,
                judgment_id=judgment["id"],
                hard_negative_kind=negative_kind,
                source_type="replay",
                source_ref_id=replay_query.id,
                query=query,
                result=result,
                created_at=created_at,
                reason="Replay failure selected the top ranked result as a hard negative.",
                search_feedback_id=replay_query.feedback_id,
                search_replay_query_id=replay_query.id,
                details=source_details,
            )
        )

    return judgments, hard_negatives


def _summary(
    *,
    source_types: list[str],
    limit: int,
    judgments: list[dict[str, Any]],
    hard_negatives: list[dict[str, Any]],
) -> dict[str, Any]:
    judgment_counts = Counter(row["judgment_kind"] for row in judgments)
    hard_negative_counts = Counter(row["hard_negative_kind"] for row in hard_negatives)
    source_counts = Counter(row["source_type"] for row in judgments)
    return {
        "schema_name": RETRIEVAL_LEARNING_DATASET_SCHEMA,
        "schema_version": RETRIEVAL_LEARNING_DATASET_SCHEMA_VERSION,
        "source_types": source_types,
        "source_limit": limit,
        "judgment_count": len(judgments),
        "positive_count": judgment_counts[RetrievalJudgmentKind.POSITIVE.value],
        "negative_count": judgment_counts[RetrievalJudgmentKind.NEGATIVE.value],
        "missing_count": judgment_counts[RetrievalJudgmentKind.MISSING.value],
        "hard_negative_count": len(hard_negatives),
        "judgment_counts_by_source_type": dict(sorted(source_counts.items())),
        "hard_negative_counts_by_kind": dict(sorted(hard_negative_counts.items())),
    }


def materialize_retrieval_learning_dataset(
    session: Session,
    *,
    limit: int = 200,
    source_types: list[str] | tuple[str, ...] | None = None,
    set_name: str | None = None,
    created_by: str | None = None,
    search_harness_evaluation_id: UUID | None = None,
    search_harness_release_id: UUID | None = None,
) -> dict[str, Any]:
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    normalized_source_types = _normalize_source_types(source_types)
    created_at = utcnow()
    judgment_set_id = uuid.uuid4()
    training_run_id = uuid.uuid4()
    effective_set_name = (
        set_name
        or f"retrieval-learning-{created_at.strftime('%Y%m%dT%H%M%SZ')}-{judgment_set_id.hex[:8]}"
    )

    judgments: list[dict[str, Any]] = []
    hard_negatives: list[dict[str, Any]] = []
    if "feedback" in normalized_source_types:
        feedback_judgments, feedback_hard_negatives = _collect_feedback_sources(
            session,
            judgment_set_id=judgment_set_id,
            limit=limit,
            created_at=created_at,
        )
        judgments.extend(feedback_judgments)
        hard_negatives.extend(feedback_hard_negatives)
    if "replay" in normalized_source_types:
        replay_judgments, replay_hard_negatives = _collect_replay_sources(
            session,
            judgment_set_id=judgment_set_id,
            limit=limit,
            created_at=created_at,
        )
        judgments.extend(replay_judgments)
        hard_negatives.extend(replay_hard_negatives)

    judgments.sort(key=lambda row: row["deduplication_key"])
    hard_negatives.sort(key=lambda row: row["deduplication_key"])
    summary = _summary(
        source_types=normalized_source_types,
        limit=limit,
        judgments=judgments,
        hard_negatives=hard_negatives,
    )
    training_payload = _json_payload(
        {
            "schema_name": RETRIEVAL_LEARNING_DATASET_SCHEMA,
            "schema_version": RETRIEVAL_LEARNING_DATASET_SCHEMA_VERSION,
            "judgment_set": {
                "judgment_set_id": judgment_set_id,
                "set_name": effective_set_name,
                "set_kind": _set_kind(normalized_source_types),
                "source_types": normalized_source_types,
                "source_limit": limit,
                "criteria": {
                    "feedback": {
                        "positive_feedback_types": ["relevant"],
                        "negative_feedback_types": ["irrelevant"],
                        "missing_feedback_types": ["missing_table", "missing_chunk", "no_answer"],
                    },
                    "replay": {
                        "passed_queries": "positive_or_expected_no_answer",
                        "failed_queries": "missing_or_top_result_hard_negative",
                    },
                },
            },
            "summary": summary,
            "judgments": [_judgment_payload(row) for row in judgments],
            "hard_negatives": [_hard_negative_payload(row) for row in hard_negatives],
        }
    )
    dataset_sha256 = _payload_sha256(training_payload)
    summary = {**summary, "training_dataset_sha256": dataset_sha256}

    judgment_set = RetrievalJudgmentSet(
        id=judgment_set_id,
        set_name=effective_set_name,
        set_kind=_set_kind(normalized_source_types),
        source_types_json=normalized_source_types,
        source_limit=limit,
        criteria_json=training_payload["judgment_set"]["criteria"],
        summary_json=summary,
        judgment_count=summary["judgment_count"],
        positive_count=summary["positive_count"],
        negative_count=summary["negative_count"],
        missing_count=summary["missing_count"],
        hard_negative_count=summary["hard_negative_count"],
        payload_sha256=dataset_sha256,
        created_by=created_by,
        created_at=created_at,
    )
    session.add(judgment_set)
    session.flush()
    session.add_all(RetrievalJudgment(**row) for row in judgments)
    session.flush()
    session.add_all(RetrievalHardNegative(**row) for row in hard_negatives)

    training_run = RetrievalTrainingRun(
        id=training_run_id,
        judgment_set_id=judgment_set_id,
        run_kind="materialized_training_dataset",
        status=RetrievalTrainingRunStatus.COMPLETED.value,
        search_harness_evaluation_id=search_harness_evaluation_id,
        search_harness_release_id=search_harness_release_id,
        training_dataset_sha256=dataset_sha256,
        training_payload_json=training_payload,
        summary_json=summary,
        example_count=summary["judgment_count"],
        positive_count=summary["positive_count"],
        negative_count=summary["negative_count"],
        missing_count=summary["missing_count"],
        hard_negative_count=summary["hard_negative_count"],
        created_by=created_by,
        created_at=created_at,
        completed_at=created_at,
    )
    session.add(training_run)
    session.flush()

    governance_scope = (
        f"search_harness_release:{search_harness_release_id}"
        if search_harness_release_id is not None
        else f"retrieval_learning:{judgment_set_id}"
    )
    governance_event = record_semantic_governance_event(
        session,
        event_kind=SemanticGovernanceEventKind.RETRIEVAL_TRAINING_RUN_MATERIALIZED.value,
        governance_scope=governance_scope,
        subject_table="retrieval_training_runs",
        subject_id=training_run_id,
        search_harness_evaluation_id=search_harness_evaluation_id,
        search_harness_release_id=search_harness_release_id,
        event_payload={
            "retrieval_training_run": {
                "retrieval_training_run_id": str(training_run_id),
                "judgment_set_id": str(judgment_set_id),
                "set_name": effective_set_name,
                "source_types": normalized_source_types,
                "source_limit": limit,
                "training_dataset_sha256": dataset_sha256,
                "summary": summary,
            }
        },
        deduplication_key=(
            f"retrieval_training_run_materialized:{training_run_id}:{dataset_sha256}"
        ),
        created_by=created_by,
    )
    training_run.semantic_governance_event_id = governance_event.id
    session.flush()

    return {
        "retrieval_training_run_id": str(training_run_id),
        "judgment_set_id": str(judgment_set_id),
        "semantic_governance_event_id": str(governance_event.id),
        "training_dataset_sha256": dataset_sha256,
        "set_name": effective_set_name,
        "source_types": normalized_source_types,
        "source_limit": limit,
        "summary": summary,
    }
