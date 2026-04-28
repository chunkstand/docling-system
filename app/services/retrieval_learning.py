from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.time import utcnow
from app.db.models import (
    ClaimEvidenceDerivation,
    EvidenceTraceEdge,
    EvidenceTraceNode,
    RetrievalHardNegative,
    RetrievalHardNegativeKind,
    RetrievalJudgment,
    RetrievalJudgmentKind,
    RetrievalJudgmentSet,
    RetrievalLearningCandidateEvaluation,
    RetrievalLearningCandidateStatus,
    RetrievalRerankerArtifact,
    RetrievalTrainingRun,
    RetrievalTrainingRunStatus,
    SearchFeedback,
    SearchHarnessRelease,
    SearchReplayQuery,
    SearchReplayRun,
    SearchRequestRecord,
    SearchRequestResult,
    SearchRequestResultSpan,
    SemanticGovernanceEventKind,
)
from app.schemas.search import (
    RetrievalLearningCandidateEvaluationRequest,
    RetrievalLearningCandidateEvaluationResponse,
    RetrievalLearningCandidateEvaluationSummaryResponse,
    RetrievalRerankerArtifactRequest,
    RetrievalRerankerArtifactResponse,
    RetrievalRerankerArtifactSummaryResponse,
    SearchHarnessEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessReleaseGateRequest,
    SearchHarnessReleaseResponse,
)
from app.services.search import get_search_harness
from app.services.search_harness_evaluations import evaluate_search_harness
from app.services.search_release_gate import record_search_harness_release_gate
from app.services.semantic_governance import (
    record_semantic_governance_event,
    search_harness_release_semantic_governance_context,
)

RETRIEVAL_LEARNING_DATASET_SCHEMA = "retrieval_learning_dataset"
RETRIEVAL_LEARNING_DATASET_SCHEMA_VERSION = "1.0"
RETRIEVAL_LEARNING_SOURCES = {"feedback", "replay"}
RETRIEVAL_RERANKER_ARTIFACT_SCHEMA = "retrieval_reranker_artifact"
RETRIEVAL_RERANKER_ARTIFACT_SCHEMA_VERSION = "1.0"
RETRIEVAL_RERANKER_ARTIFACT_KIND = "linear_feature_weight_candidate"


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


def _hard_negative_payload(row: dict[str, Any]) -> dict[str, Any]:
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
    payload = _judgment_payload(row)
    payload.pop("judgment_id", None)
    payload.pop("source_payload_sha256", None)
    payload.pop("deduplication_key", None)
    if isinstance(payload.get("details"), dict):
        payload["details"].pop("source_payload_sha256", None)
    return payload


def _hard_negative_source_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload = _hard_negative_payload(row)
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


def _finalize_judgment_source_hashes(judgments: list[dict[str, Any]]) -> None:
    for row in judgments:
        row["source_payload_sha256"] = _payload_sha256(_judgment_source_payload(row))
        row["payload_json"] = {
            **(row.get("payload_json") or {}),
            "source_payload_sha256": row["source_payload_sha256"],
        }


def _pair_hard_negatives_with_positive_judgments(
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


def _finalize_hard_negative_source_hashes(hard_negatives: list[dict[str, Any]]) -> None:
    for row in hard_negatives:
        row["source_payload_sha256"] = _payload_sha256(_hard_negative_source_payload(row))
        row["details_json"] = {
            **(row.get("details_json") or {}),
            "source_payload_sha256": row["source_payload_sha256"],
        }


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
        "source_payload_sha256": None,
        "deduplication_key": deduplication_key,
        "created_at": created_at,
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
    evidence_by_result_id = _evidence_refs_by_result_id(
        session,
        result_ids
        | {
            result.id
            for results in results_by_request_id.values()
            for result in results
        },
    )

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
                    source_search_request_id=feedback.search_request_id,
                    evidence_refs=evidence_by_result_id.get(result.id, []),
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
                        source_search_request_id=feedback.search_request_id,
                        expected_result_type=expected_type,
                        evidence_refs=evidence_by_result_id.get(candidate.id, []),
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
                        source_search_request_id=feedback.search_request_id,
                        evidence_refs=evidence_by_result_id.get(candidate.id, []),
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
                search_replay_run_id=replay_query.replay_run_id,
                evaluation_query_id=replay_query.evaluation_query_id,
                source_search_request_id=replay_query.source_search_request_id,
                expected_result_type=replay_query.expected_result_type,
                expected_top_n=replay_query.expected_top_n,
                evidence_refs=evidence_by_result_id.get(result.id, []),
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
    _finalize_judgment_source_hashes(judgments)
    _pair_hard_negatives_with_positive_judgments(judgments, hard_negatives)
    _finalize_hard_negative_source_hashes(hard_negatives)
    summary = _summary(
        source_types=normalized_source_types,
        limit=limit,
        judgments=judgments,
        hard_negatives=hard_negatives,
    )
    summary = {
        **summary,
        "training_example_count": summary["judgment_count"] + summary["hard_negative_count"],
    }
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
        example_count=summary["training_example_count"],
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


def _retrieval_training_run_not_found(training_run_id: UUID | None) -> HTTPException:
    context = {}
    if training_run_id is not None:
        context["retrieval_training_run_id"] = str(training_run_id)
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "retrieval_training_run_not_found",
        "Retrieval training run not found.",
        **context,
    )


def _retrieval_learning_candidate_not_found(
    candidate_evaluation_id: UUID,
) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "retrieval_learning_candidate_evaluation_not_found",
        "Retrieval learning candidate evaluation not found.",
        candidate_evaluation_id=str(candidate_evaluation_id),
    )


def _thresholds_from_candidate_request(
    request: RetrievalLearningCandidateEvaluationRequest,
) -> dict[str, Any]:
    return {
        "max_total_regressed_count": request.max_total_regressed_count,
        "max_mrr_drop": request.max_mrr_drop,
        "max_zero_result_count_increase": request.max_zero_result_count_increase,
        "max_foreign_top_result_count_increase": (
            request.max_foreign_top_result_count_increase
        ),
        "min_total_shared_query_count": request.min_total_shared_query_count,
    }


def _latest_completed_training_run(session: Session) -> RetrievalTrainingRun | None:
    return session.scalar(
        select(RetrievalTrainingRun)
        .where(RetrievalTrainingRun.status == RetrievalTrainingRunStatus.COMPLETED.value)
        .order_by(RetrievalTrainingRun.created_at.desc())
        .limit(1)
    )


def _resolve_training_run(
    session: Session,
    retrieval_training_run_id: UUID | None,
) -> RetrievalTrainingRun:
    if retrieval_training_run_id is not None:
        training_run = session.get(RetrievalTrainingRun, retrieval_training_run_id)
    else:
        training_run = _latest_completed_training_run(session)
    if training_run is None:
        raise _retrieval_training_run_not_found(retrieval_training_run_id)
    if training_run.status != RetrievalTrainingRunStatus.COMPLETED.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "retrieval_training_run_not_completed",
            "Retrieval training run is not completed.",
            retrieval_training_run_id=str(training_run.id),
            status=training_run.status,
        )
    if training_run.example_count <= 0:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "retrieval_training_run_empty",
            "Retrieval training run has no examples.",
            retrieval_training_run_id=str(training_run.id),
        )
    return training_run


def _learning_candidate_package(
    *,
    training_run: RetrievalTrainingRun,
    evaluation: SearchHarnessEvaluationResponse,
    release: SearchHarnessReleaseResponse,
    request: RetrievalLearningCandidateEvaluationRequest,
) -> dict[str, Any]:
    return _json_payload(
        {
            "schema_name": "retrieval_learning_candidate_package",
            "schema_version": "1.0",
            "retrieval_training_run": {
                "retrieval_training_run_id": training_run.id,
                "judgment_set_id": training_run.judgment_set_id,
                "training_dataset_sha256": training_run.training_dataset_sha256,
                "training_example_count": training_run.example_count,
                "positive_count": training_run.positive_count,
                "negative_count": training_run.negative_count,
                "missing_count": training_run.missing_count,
                "hard_negative_count": training_run.hard_negative_count,
                "summary": training_run.summary_json or {},
            },
            "candidate_request": {
                "candidate_harness_name": request.candidate_harness_name,
                "baseline_harness_name": request.baseline_harness_name,
                "source_types": list(request.source_types),
                "limit": request.limit,
                "thresholds": _thresholds_from_candidate_request(request),
                "requested_by": request.requested_by,
                "review_note": request.review_note,
            },
            "evaluation": evaluation.model_dump(mode="json"),
            "release": release.model_dump(mode="json"),
        }
    )


def _candidate_request_from_artifact_request(
    request: RetrievalRerankerArtifactRequest,
) -> RetrievalLearningCandidateEvaluationRequest:
    return RetrievalLearningCandidateEvaluationRequest(
        retrieval_training_run_id=request.retrieval_training_run_id,
        candidate_harness_name=request.candidate_harness_name,
        baseline_harness_name=request.baseline_harness_name,
        source_types=list(request.source_types),
        limit=request.limit,
        max_total_regressed_count=request.max_total_regressed_count,
        max_mrr_drop=request.max_mrr_drop,
        max_zero_result_count_increase=request.max_zero_result_count_increase,
        max_foreign_top_result_count_increase=(
            request.max_foreign_top_result_count_increase
        ),
        min_total_shared_query_count=request.min_total_shared_query_count,
        requested_by=request.requested_by,
        review_note=request.review_note,
    )


def _bounded_float(value: float, *, lower: float, upper: float) -> float:
    return round(max(lower, min(upper, value)), 6)


def _rows_from_training_payload(
    training_run: RetrievalTrainingRun,
) -> tuple[list[dict], list[dict]]:
    payload = training_run.training_payload_json or {}
    judgments = payload.get("judgments") if isinstance(payload, dict) else []
    hard_negatives = payload.get("hard_negatives") if isinstance(payload, dict) else []
    return (
        [row for row in judgments or [] if isinstance(row, dict)],
        [row for row in hard_negatives or [] if isinstance(row, dict)],
    )


def _numeric_feature_average(rows: list[dict], feature_name: str) -> float:
    values: list[float] = []
    for row in rows:
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        features = result.get("rerank_features") if isinstance(result, dict) else {}
        value = features.get(feature_name) if isinstance(features, dict) else None
        if isinstance(value, int | float):
            values.append(float(value))
    if not values:
        return 0.0
    return sum(values) / len(values)


def _result_type_rate(rows: list[dict], result_type: str) -> float:
    typed = [
        row
        for row in rows
        if isinstance(row.get("result"), dict) and row["result"].get("result_type")
    ]
    if not typed:
        return 0.0
    return sum(1 for row in typed if row["result"].get("result_type") == result_type) / len(
        typed
    )


def _feature_weight_candidate(
    *,
    training_run: RetrievalTrainingRun,
    base_harness_name: str,
    candidate_harness_name: str,
    artifact_name: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    base_harness = get_search_harness(base_harness_name)
    base_reranker = base_harness.reranker_config.snapshot()
    judgments, hard_negatives = _rows_from_training_payload(training_run)
    positive_judgments = [
        row for row in judgments if row.get("judgment_kind") == RetrievalJudgmentKind.POSITIVE.value
    ]
    pressure = {
        "positive_table_rate": _result_type_rate(positive_judgments, "table"),
        "hard_negative_table_rate": _result_type_rate(hard_negatives, "table"),
        "positive_chunk_rate": _result_type_rate(positive_judgments, "chunk"),
        "hard_negative_chunk_rate": _result_type_rate(hard_negatives, "chunk"),
    }
    feature_map = {
        "tabular_table_signal": "tabular_table_bonus",
        "title_token_coverage": "title_token_coverage_bonus",
        "source_filename_token_coverage": "source_filename_token_coverage_bonus",
        "document_title_token_coverage": "document_title_token_coverage_bonus",
        "document_cluster_strength": "prose_document_cluster_bonus",
        "heading_token_coverage": "heading_token_coverage_bonus",
        "phrase_overlap": "phrase_overlap_bonus",
        "rare_token_overlap": "rare_token_overlap_bonus",
        "adjacent_chunk_context_signal": "adjacent_chunk_context_bonus",
        "exact_filter_priority": "exact_filter_bonus",
    }
    deltas: dict[str, float] = {}
    observations: dict[str, Any] = {
        "feature_signal_count": len(positive_judgments) + len(hard_negatives),
        "result_type_pressure": pressure,
        "feature_deltas": {},
    }
    for feature_name, weight_name in feature_map.items():
        positive_avg = _numeric_feature_average(positive_judgments, feature_name)
        negative_avg = _numeric_feature_average(hard_negatives, feature_name)
        feature_delta = positive_avg - negative_avg
        observations["feature_deltas"][feature_name] = {
            "positive_average": round(positive_avg, 6),
            "hard_negative_average": round(negative_avg, 6),
            "delta": round(feature_delta, 6),
        }
        if feature_delta <= 0:
            continue
        base_value = float(base_reranker.get(weight_name) or 0.0)
        deltas[weight_name] = _bounded_float(feature_delta * 0.01, lower=0.0, upper=0.015)
        deltas[weight_name] = _bounded_float(
            deltas[weight_name],
            lower=0.0,
            upper=max(0.015, base_value),
        )

    type_pressure = max(
        abs(pressure["positive_table_rate"] - pressure["hard_negative_table_rate"]),
        abs(pressure["positive_chunk_rate"] - pressure["hard_negative_chunk_rate"]),
    )
    hard_negative_pressure = min(training_run.hard_negative_count, 10) / 10
    result_type_delta = max(0.001, (type_pressure + hard_negative_pressure) * 0.004)
    deltas["result_type_priority_bonus"] = _bounded_float(
        result_type_delta,
        lower=0.001,
        upper=0.012,
    )

    proposed_reranker_overrides = {
        key: _bounded_float(float(base_reranker.get(key) or 0.0) + delta, lower=0.0, upper=5.0)
        for key, delta in sorted(deltas.items())
    }
    feature_weights = {
        "schema_name": "retrieval_reranker_feature_weights",
        "schema_version": "1.0",
        "base_harness_name": base_harness_name,
        "base_reranker_name": base_harness.reranker_name,
        "base_reranker_version": base_harness.reranker_version,
        "candidate_harness_name": candidate_harness_name,
        "artifact_name": artifact_name,
        "training_dataset_sha256": training_run.training_dataset_sha256,
        "training_example_count": training_run.example_count,
        "positive_count": training_run.positive_count,
        "negative_count": training_run.negative_count,
        "missing_count": training_run.missing_count,
        "hard_negative_count": training_run.hard_negative_count,
        "observations": observations,
        "base_reranker_config": base_reranker,
        "proposed_reranker_overrides": proposed_reranker_overrides,
    }
    override_spec = {
        "base_harness_name": base_harness_name,
        "override_type": "retrieval_reranker_artifact",
        "override_source": "retrieval_learning",
        "rationale": (
            "Data-derived linear reranker candidate from persisted judgments and "
            "hard negatives."
        ),
        "reranker_overrides": proposed_reranker_overrides,
        "retrieval_profile_overrides": {},
    }
    harness_overrides = {candidate_harness_name: override_spec}
    return feature_weights, harness_overrides, override_spec


def _maybe_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _training_reference_set(training_run: RetrievalTrainingRun) -> dict[str, Any]:
    judgments, hard_negatives = _rows_from_training_payload(training_run)
    uuid_refs: set[UUID] = set()
    content_hashes: set[str] = set()
    source_payload_hashes: set[str] = set()
    result_type_counts: Counter[str] = Counter()
    source_type_counts: Counter[str] = Counter()
    for row in [*judgments, *hard_negatives]:
        if source_hash := row.get("source_payload_sha256"):
            source_payload_hashes.add(str(source_hash))
            content_hashes.add(str(source_hash))
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        query = row.get("query") if isinstance(row.get("query"), dict) else {}
        for key in (
            "source_ref_id",
            "search_feedback_id",
            "search_replay_query_id",
            "search_replay_run_id",
            "evaluation_query_id",
            "source_search_request_id",
            "search_request_id",
            "search_request_result_id",
        ):
            if value := _maybe_uuid(source.get(key)):
                uuid_refs.add(value)
        for key in ("result_id", "document_id", "run_id"):
            if value := _maybe_uuid(result.get(key)):
                uuid_refs.add(value)
        if result_type := result.get("result_type"):
            result_type_counts[str(result_type)] += 1
        if source_type := source.get("source_type"):
            source_type_counts[str(source_type)] += 1
        if query_hash := query.get("query_sha256"):
            content_hashes.add(str(query_hash))
        for evidence_ref in result.get("evidence_refs") or []:
            if not isinstance(evidence_ref, dict):
                continue
            for key in (
                "search_request_result_span_id",
                "retrieval_evidence_span_id",
                "source_id",
            ):
                if value := _maybe_uuid(evidence_ref.get(key)):
                    uuid_refs.add(value)
            for key in ("content_sha256", "source_snapshot_sha256"):
                if value := evidence_ref.get(key):
                    content_hashes.add(str(value))
    return {
        "uuid_refs": uuid_refs,
        "content_hashes": content_hashes,
        "source_payload_hashes": source_payload_hashes,
        "result_type_counts": dict(sorted(result_type_counts.items())),
        "source_type_counts": dict(sorted(source_type_counts.items())),
    }


def _trace_owner_predicates(rows: list[EvidenceTraceNode]):
    manifest_ids = {row.evidence_manifest_id for row in rows if row.evidence_manifest_id}
    export_ids = {
        row.evidence_package_export_id for row in rows if row.evidence_package_export_id
    }
    predicates = []
    if manifest_ids:
        predicates.append(EvidenceTraceNode.evidence_manifest_id.in_(manifest_ids))
    if export_ids:
        predicates.append(EvidenceTraceNode.evidence_package_export_id.in_(export_ids))
    return predicates, manifest_ids, export_ids


def _change_impact_report(
    session: Session,
    *,
    artifact_id: UUID,
    artifact_payload: dict[str, Any],
    artifact_sha256: str,
    training_run: RetrievalTrainingRun,
    evaluation: SearchHarnessEvaluationResponse,
    release: SearchHarnessReleaseResponse,
) -> dict[str, Any]:
    refs = _training_reference_set(training_run)
    uuid_refs = refs["uuid_refs"]
    content_hashes = refs["content_hashes"]
    matching_trace_nodes: list[EvidenceTraceNode] = []
    if uuid_refs or content_hashes:
        predicates = []
        if uuid_refs:
            predicates.append(EvidenceTraceNode.source_id.in_(uuid_refs))
        if content_hashes:
            predicates.append(EvidenceTraceNode.content_sha256.in_(content_hashes))
        matching_trace_nodes = (
            session.execute(select(EvidenceTraceNode).where(or_(*predicates)).limit(200))
            .scalars()
            .all()
        )
    owner_predicates, manifest_ids, export_ids = _trace_owner_predicates(matching_trace_nodes)
    owner_nodes: list[EvidenceTraceNode] = []
    owner_edges: list[EvidenceTraceEdge] = []
    if owner_predicates:
        owner_nodes = (
            session.execute(select(EvidenceTraceNode).where(or_(*owner_predicates)).limit(500))
            .scalars()
            .all()
        )
        edge_predicates = []
        if manifest_ids:
            edge_predicates.append(EvidenceTraceEdge.evidence_manifest_id.in_(manifest_ids))
        if export_ids:
            edge_predicates.append(EvidenceTraceEdge.evidence_package_export_id.in_(export_ids))
        owner_edges = (
            session.execute(select(EvidenceTraceEdge).where(or_(*edge_predicates)).limit(500))
            .scalars()
            .all()
            if edge_predicates
            else []
        )
    claim_nodes = [
        row
        for row in owner_nodes
        if row.node_kind in {"technical_report_claim", "claim_derivation"}
    ][:50]
    derivations = (
        session.execute(
            select(ClaimEvidenceDerivation)
            .where(ClaimEvidenceDerivation.evidence_package_export_id.in_(export_ids))
            .limit(100)
        )
        .scalars()
        .all()
        if export_ids
        else []
    )
    release_row = session.get(SearchHarnessRelease, release.release_id)
    semantic_policy = (
        search_harness_release_semantic_governance_context(session, release_row)["policy"]
        if release_row is not None
        else {}
    )
    return _json_payload(
        {
            "schema_name": "retrieval_reranker_change_impact_report",
            "schema_version": "1.0",
            "artifact": {
                "artifact_id": artifact_id,
                "artifact_sha256": artifact_sha256,
                "artifact_name": artifact_payload["artifact_name"],
                "artifact_version": artifact_payload["artifact_version"],
                "candidate_harness_name": artifact_payload["candidate_harness_name"],
                "base_harness_name": artifact_payload["base_harness_name"],
            },
            "changed_state_refs": {
                "retrieval_training_run_id": training_run.id,
                "judgment_set_id": training_run.judgment_set_id,
                "training_dataset_sha256": training_run.training_dataset_sha256,
                "search_harness_evaluation_id": evaluation.evaluation_id,
                "search_harness_release_id": release.release_id,
                "semantic_policy": semantic_policy,
            },
            "source_reference_summary": {
                "uuid_ref_count": len(uuid_refs),
                "content_hash_count": len(content_hashes),
                "source_payload_hash_count": len(refs["source_payload_hashes"]),
                "result_type_counts": refs["result_type_counts"],
                "source_type_counts": refs["source_type_counts"],
            },
            "affected_trace_summary": {
                "matching_trace_node_count": len(matching_trace_nodes),
                "owner_trace_node_count": len(owner_nodes),
                "owner_trace_edge_count": len(owner_edges),
                "affected_claim_count": len(claim_nodes),
                "affected_derivation_count": len(derivations),
            },
            "affected_claims": [
                {
                    "node_id": row.id,
                    "node_key": row.node_key,
                    "node_kind": row.node_kind,
                    "source_table": row.source_table,
                    "source_id": row.source_id,
                    "content_sha256": row.content_sha256,
                }
                for row in claim_nodes
            ],
            "affected_derivations": [
                {
                    "derivation_id": row.id,
                    "claim_id": row.claim_id,
                    "derivation_rule": row.derivation_rule,
                    "derivation_sha256": row.derivation_sha256,
                }
                for row in derivations
            ],
            "impact_policy": {
                "scope": "ranking_artifact_to_training_sources_and_trace_owners",
                "requires_release_gate": True,
                "requires_semantic_governance_context": True,
                "requires_trace_recheck_when_affected_claim_count_gt_zero": True,
            },
        }
    )


def _record_retrieval_learning_candidate_governance_event(
    session: Session,
    *,
    row: RetrievalLearningCandidateEvaluation,
    training_run: RetrievalTrainingRun,
) -> None:
    event = record_semantic_governance_event(
        session,
        event_kind=SemanticGovernanceEventKind.RETRIEVAL_LEARNING_CANDIDATE_EVALUATED.value,
        governance_scope=f"retrieval_learning:{training_run.id}",
        subject_table="retrieval_learning_candidate_evaluations",
        subject_id=row.id,
        search_harness_evaluation_id=row.search_harness_evaluation_id,
        search_harness_release_id=row.search_harness_release_id,
        event_payload={
            "retrieval_learning_candidate_evaluation": {
                "candidate_evaluation_id": str(row.id),
                "retrieval_training_run_id": str(training_run.id),
                "judgment_set_id": str(training_run.judgment_set_id),
                "training_dataset_sha256": row.training_dataset_sha256,
                "training_example_count": row.training_example_count,
                "search_harness_evaluation_id": str(row.search_harness_evaluation_id),
                "search_harness_release_id": (
                    str(row.search_harness_release_id)
                    if row.search_harness_release_id is not None
                    else None
                ),
                "baseline_harness_name": row.baseline_harness_name,
                "candidate_harness_name": row.candidate_harness_name,
                "source_types": list(row.source_types_json or []),
                "limit": row.limit,
                "status": row.status,
                "gate_outcome": row.gate_outcome,
                "metrics": row.metrics_json or {},
                "thresholds": row.thresholds_json or {},
                "learning_package_sha256": row.learning_package_sha256,
            }
        },
        deduplication_key=(
            f"retrieval_learning_candidate_evaluated:{row.id}:"
            f"{row.learning_package_sha256}"
        ),
        created_by=row.created_by,
    )
    row.semantic_governance_event_id = event.id
    session.flush()


def _to_candidate_summary(
    row: RetrievalLearningCandidateEvaluation,
) -> RetrievalLearningCandidateEvaluationSummaryResponse:
    return RetrievalLearningCandidateEvaluationSummaryResponse(
        candidate_evaluation_id=row.id,
        retrieval_training_run_id=row.retrieval_training_run_id,
        judgment_set_id=row.judgment_set_id,
        search_harness_evaluation_id=row.search_harness_evaluation_id,
        search_harness_release_id=row.search_harness_release_id,
        semantic_governance_event_id=row.semantic_governance_event_id,
        training_dataset_sha256=row.training_dataset_sha256,
        training_example_count=row.training_example_count,
        positive_count=row.positive_count,
        negative_count=row.negative_count,
        missing_count=row.missing_count,
        hard_negative_count=row.hard_negative_count,
        baseline_harness_name=row.baseline_harness_name,
        candidate_harness_name=row.candidate_harness_name,
        source_types=list(row.source_types_json or []),
        limit=row.limit,
        status=row.status,
        gate_outcome=row.gate_outcome,
        thresholds=row.thresholds_json or {},
        metrics=row.metrics_json or {},
        reasons=list(row.reasons_json or []),
        learning_package_sha256=row.learning_package_sha256,
        created_by=row.created_by,
        review_note=row.review_note,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


def _to_candidate_response(
    row: RetrievalLearningCandidateEvaluation,
) -> RetrievalLearningCandidateEvaluationResponse:
    summary = _to_candidate_summary(row)
    release = None
    if row.search_harness_release_id is not None and row.release_snapshot_json:
        release = SearchHarnessReleaseResponse.model_validate(row.release_snapshot_json)
    return RetrievalLearningCandidateEvaluationResponse(
        **summary.model_dump(),
        details=row.details_json or {},
        evaluation=SearchHarnessEvaluationResponse.model_validate(
            row.evaluation_snapshot_json or {}
        ),
        release=release,
    )


def evaluate_retrieval_learning_candidate(
    session: Session,
    request: RetrievalLearningCandidateEvaluationRequest,
) -> RetrievalLearningCandidateEvaluationResponse:
    training_run = _resolve_training_run(session, request.retrieval_training_run_id)
    evaluation = evaluate_search_harness(
        session,
        SearchHarnessEvaluationRequest(
            candidate_harness_name=request.candidate_harness_name,
            baseline_harness_name=request.baseline_harness_name,
            source_types=request.source_types,
            limit=request.limit,
        ),
    )
    if evaluation.evaluation_id is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "search_harness_evaluation_missing_id",
            "Learning candidates require a durable search harness evaluation.",
        )
    gate_request = SearchHarnessReleaseGateRequest(
        evaluation_id=evaluation.evaluation_id,
        max_total_regressed_count=request.max_total_regressed_count,
        max_mrr_drop=request.max_mrr_drop,
        max_zero_result_count_increase=request.max_zero_result_count_increase,
        max_foreign_top_result_count_increase=request.max_foreign_top_result_count_increase,
        min_total_shared_query_count=request.min_total_shared_query_count,
        requested_by=request.requested_by,
        review_note=request.review_note,
    )
    release = record_search_harness_release_gate(
        session,
        evaluation,
        gate_request,
        requested_by=request.requested_by,
        review_note=request.review_note,
    )
    created_at = utcnow()
    package = _learning_candidate_package(
        training_run=training_run,
        evaluation=evaluation,
        release=release,
        request=request,
    )
    status_value = (
        RetrievalLearningCandidateStatus.COMPLETED.value
        if evaluation.status == "completed"
        else RetrievalLearningCandidateStatus.FAILED.value
    )
    row = RetrievalLearningCandidateEvaluation(
        id=uuid.uuid4(),
        retrieval_training_run_id=training_run.id,
        judgment_set_id=training_run.judgment_set_id,
        search_harness_evaluation_id=evaluation.evaluation_id,
        search_harness_release_id=release.release_id,
        training_dataset_sha256=training_run.training_dataset_sha256,
        training_example_count=training_run.example_count,
        positive_count=training_run.positive_count,
        negative_count=training_run.negative_count,
        missing_count=training_run.missing_count,
        hard_negative_count=training_run.hard_negative_count,
        baseline_harness_name=request.baseline_harness_name,
        candidate_harness_name=request.candidate_harness_name,
        source_types_json=list(request.source_types),
        limit=request.limit,
        status=status_value,
        gate_outcome=release.outcome,
        thresholds_json=_thresholds_from_candidate_request(request),
        metrics_json=release.metrics,
        reasons_json=list(release.reasons),
        evaluation_snapshot_json=evaluation.model_dump(mode="json"),
        release_snapshot_json=release.model_dump(mode="json"),
        details_json={
            "schema_name": "retrieval_learning_candidate_evaluation_details",
            "schema_version": "1.0",
            "learning_loop_stage": "training_dataset_to_harness_release_gate",
            "training_dataset_summary": training_run.summary_json or {},
            "release_gate": {
                "outcome": release.outcome,
                "metrics": release.metrics,
                "reasons": release.reasons,
                "details": release.details,
            },
        },
        learning_package_sha256=_payload_sha256(package),
        created_by=request.requested_by,
        review_note=request.review_note,
        created_at=created_at,
        completed_at=created_at,
    )
    session.add(row)
    session.flush()

    if training_run.search_harness_evaluation_id is None:
        training_run.search_harness_evaluation_id = evaluation.evaluation_id
    if training_run.search_harness_release_id is None:
        training_run.search_harness_release_id = release.release_id

    _record_retrieval_learning_candidate_governance_event(
        session,
        row=row,
        training_run=training_run,
    )
    return _to_candidate_response(row)


def list_retrieval_learning_candidate_evaluations(
    session: Session,
    *,
    limit: int = 20,
    retrieval_training_run_id: UUID | None = None,
    candidate_harness_name: str | None = None,
) -> list[RetrievalLearningCandidateEvaluationSummaryResponse]:
    statement = select(RetrievalLearningCandidateEvaluation).order_by(
        RetrievalLearningCandidateEvaluation.created_at.desc()
    )
    if retrieval_training_run_id is not None:
        statement = statement.where(
            RetrievalLearningCandidateEvaluation.retrieval_training_run_id
            == retrieval_training_run_id
        )
    if candidate_harness_name:
        statement = statement.where(
            RetrievalLearningCandidateEvaluation.candidate_harness_name
            == candidate_harness_name
        )
    rows = session.execute(statement.limit(limit)).scalars().all()
    return [_to_candidate_summary(row) for row in rows]


def get_retrieval_learning_candidate_evaluation_detail(
    session: Session,
    candidate_evaluation_id: UUID,
) -> RetrievalLearningCandidateEvaluationResponse:
    row = session.get(RetrievalLearningCandidateEvaluation, candidate_evaluation_id)
    if row is None:
        raise _retrieval_learning_candidate_not_found(candidate_evaluation_id)
    return _to_candidate_response(row)


def _retrieval_reranker_artifact_not_found(artifact_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "retrieval_reranker_artifact_not_found",
        "Retrieval reranker artifact not found.",
        artifact_id=str(artifact_id),
    )


def _record_reranker_artifact_governance_event(
    session: Session,
    *,
    row: RetrievalRerankerArtifact,
    training_run: RetrievalTrainingRun,
) -> None:
    event = record_semantic_governance_event(
        session,
        event_kind=(
            SemanticGovernanceEventKind.RETRIEVAL_RERANKER_ARTIFACT_MATERIALIZED.value
        ),
        governance_scope=f"retrieval_reranker_artifact:{row.id}",
        subject_table="retrieval_reranker_artifacts",
        subject_id=row.id,
        search_harness_evaluation_id=row.search_harness_evaluation_id,
        search_harness_release_id=row.search_harness_release_id,
        event_payload={
            "retrieval_reranker_artifact": {
                "artifact_id": str(row.id),
                "artifact_kind": row.artifact_kind,
                "artifact_name": row.artifact_name,
                "artifact_version": row.artifact_version,
                "retrieval_training_run_id": str(training_run.id),
                "judgment_set_id": str(training_run.judgment_set_id),
                "candidate_evaluation_id": str(
                    row.retrieval_learning_candidate_evaluation_id
                ),
                "search_harness_evaluation_id": str(row.search_harness_evaluation_id),
                "search_harness_release_id": (
                    str(row.search_harness_release_id)
                    if row.search_harness_release_id is not None
                    else None
                ),
                "training_dataset_sha256": row.training_dataset_sha256,
                "artifact_sha256": row.artifact_sha256,
                "change_impact_sha256": row.change_impact_sha256,
                "gate_outcome": row.gate_outcome,
                "feature_weights": row.feature_weights_json or {},
                "harness_overrides": row.harness_overrides_json or {},
            }
        },
        deduplication_key=(
            f"retrieval_reranker_artifact_materialized:{row.id}:"
            f"{row.artifact_sha256}:{row.change_impact_sha256}"
        ),
        created_by=row.created_by,
    )
    row.semantic_governance_event_id = event.id
    session.flush()


def _to_reranker_artifact_summary(
    row: RetrievalRerankerArtifact,
) -> RetrievalRerankerArtifactSummaryResponse:
    return RetrievalRerankerArtifactSummaryResponse(
        artifact_id=row.id,
        retrieval_training_run_id=row.retrieval_training_run_id,
        judgment_set_id=row.judgment_set_id,
        retrieval_learning_candidate_evaluation_id=(
            row.retrieval_learning_candidate_evaluation_id
        ),
        search_harness_evaluation_id=row.search_harness_evaluation_id,
        search_harness_release_id=row.search_harness_release_id,
        semantic_governance_event_id=row.semantic_governance_event_id,
        artifact_kind=row.artifact_kind,
        artifact_name=row.artifact_name,
        artifact_version=row.artifact_version,
        status=row.status,
        gate_outcome=row.gate_outcome,
        baseline_harness_name=row.baseline_harness_name,
        candidate_harness_name=row.candidate_harness_name,
        source_types=list(row.source_types_json or []),
        limit=row.limit,
        training_dataset_sha256=row.training_dataset_sha256,
        training_example_count=row.training_example_count,
        positive_count=row.positive_count,
        negative_count=row.negative_count,
        missing_count=row.missing_count,
        hard_negative_count=row.hard_negative_count,
        thresholds=row.thresholds_json or {},
        metrics=row.metrics_json or {},
        reasons=list(row.reasons_json or []),
        artifact_sha256=row.artifact_sha256,
        change_impact_sha256=row.change_impact_sha256,
        created_by=row.created_by,
        review_note=row.review_note,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


def _to_reranker_artifact_response(
    session: Session,
    row: RetrievalRerankerArtifact,
) -> RetrievalRerankerArtifactResponse:
    summary = _to_reranker_artifact_summary(row)
    candidate = session.get(
        RetrievalLearningCandidateEvaluation,
        row.retrieval_learning_candidate_evaluation_id,
    )
    if candidate is None:
        raise _retrieval_learning_candidate_not_found(
            row.retrieval_learning_candidate_evaluation_id
        )
    release = None
    if row.search_harness_release_id is not None and row.release_snapshot_json:
        release = SearchHarnessReleaseResponse.model_validate(row.release_snapshot_json)
    return RetrievalRerankerArtifactResponse(
        **summary.model_dump(),
        feature_weights=row.feature_weights_json or {},
        harness_overrides=row.harness_overrides_json or {},
        artifact=row.artifact_payload_json or {},
        change_impact_report=row.change_impact_report_json or {},
        evaluation=SearchHarnessEvaluationResponse.model_validate(
            row.evaluation_snapshot_json or {}
        ),
        release=release,
        candidate_evaluation=_to_candidate_response(candidate),
    )


def create_retrieval_reranker_artifact(
    session: Session,
    request: RetrievalRerankerArtifactRequest,
) -> RetrievalRerankerArtifactResponse:
    training_run = _resolve_training_run(session, request.retrieval_training_run_id)
    created_at = utcnow()
    artifact_id = uuid.uuid4()
    artifact_name = request.artifact_name or (
        f"{request.candidate_harness_name}-reranker-{artifact_id.hex[:8]}"
    )
    try:
        feature_weights, harness_overrides, override_spec = _feature_weight_candidate(
            training_run=training_run,
            base_harness_name=request.base_harness_name,
            candidate_harness_name=request.candidate_harness_name,
            artifact_name=artifact_name,
        )
    except ValueError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "search_harness_not_found",
            str(exc),
            base_harness_name=request.base_harness_name,
        ) from exc
    candidate_request = _candidate_request_from_artifact_request(request)
    evaluation = evaluate_search_harness(
        session,
        SearchHarnessEvaluationRequest(
            candidate_harness_name=request.candidate_harness_name,
            baseline_harness_name=request.baseline_harness_name,
            source_types=request.source_types,
            limit=request.limit,
        ),
        harness_overrides=harness_overrides,
    )
    if evaluation.evaluation_id is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "search_harness_evaluation_missing_id",
            "Reranker artifacts require a durable search harness evaluation.",
        )
    release = record_search_harness_release_gate(
        session,
        evaluation,
        SearchHarnessReleaseGateRequest(
            evaluation_id=evaluation.evaluation_id,
            max_total_regressed_count=request.max_total_regressed_count,
            max_mrr_drop=request.max_mrr_drop,
            max_zero_result_count_increase=request.max_zero_result_count_increase,
            max_foreign_top_result_count_increase=(
                request.max_foreign_top_result_count_increase
            ),
            min_total_shared_query_count=request.min_total_shared_query_count,
            requested_by=request.requested_by,
            review_note=request.review_note,
        ),
        requested_by=request.requested_by,
        review_note=request.review_note,
    )
    candidate_package = _learning_candidate_package(
        training_run=training_run,
        evaluation=evaluation,
        release=release,
        request=candidate_request,
    )
    status_value = (
        RetrievalLearningCandidateStatus.COMPLETED.value
        if evaluation.status == "completed"
        else RetrievalLearningCandidateStatus.FAILED.value
    )
    candidate_row = RetrievalLearningCandidateEvaluation(
        id=uuid.uuid4(),
        retrieval_training_run_id=training_run.id,
        judgment_set_id=training_run.judgment_set_id,
        search_harness_evaluation_id=evaluation.evaluation_id,
        search_harness_release_id=release.release_id,
        training_dataset_sha256=training_run.training_dataset_sha256,
        training_example_count=training_run.example_count,
        positive_count=training_run.positive_count,
        negative_count=training_run.negative_count,
        missing_count=training_run.missing_count,
        hard_negative_count=training_run.hard_negative_count,
        baseline_harness_name=request.baseline_harness_name,
        candidate_harness_name=request.candidate_harness_name,
        source_types_json=list(request.source_types),
        limit=request.limit,
        status=status_value,
        gate_outcome=release.outcome,
        thresholds_json=_thresholds_from_candidate_request(candidate_request),
        metrics_json=release.metrics,
        reasons_json=list(release.reasons),
        evaluation_snapshot_json=evaluation.model_dump(mode="json"),
        release_snapshot_json=release.model_dump(mode="json"),
        details_json={
            "schema_name": "retrieval_learning_candidate_evaluation_details",
            "schema_version": "1.0",
            "learning_loop_stage": "training_dataset_to_reranker_artifact_gate",
            "training_dataset_summary": training_run.summary_json or {},
            "reranker_artifact": {
                "artifact_id": str(artifact_id),
                "artifact_name": artifact_name,
                "artifact_kind": RETRIEVAL_RERANKER_ARTIFACT_KIND,
                "override_spec": override_spec,
            },
            "release_gate": {
                "outcome": release.outcome,
                "metrics": release.metrics,
                "reasons": release.reasons,
                "details": release.details,
            },
        },
        learning_package_sha256=_payload_sha256(candidate_package),
        created_by=request.requested_by,
        review_note=request.review_note,
        created_at=created_at,
        completed_at=created_at,
    )
    session.add(candidate_row)
    session.flush()
    if training_run.search_harness_evaluation_id is None:
        training_run.search_harness_evaluation_id = evaluation.evaluation_id
    if training_run.search_harness_release_id is None:
        training_run.search_harness_release_id = release.release_id
    _record_retrieval_learning_candidate_governance_event(
        session,
        row=candidate_row,
        training_run=training_run,
    )

    artifact_version = (
        f"{request.candidate_harness_name}+{training_run.training_dataset_sha256[:12]}"
    )
    artifact_payload = _json_payload(
        {
            "schema_name": RETRIEVAL_RERANKER_ARTIFACT_SCHEMA,
            "schema_version": RETRIEVAL_RERANKER_ARTIFACT_SCHEMA_VERSION,
            "artifact_id": artifact_id,
            "artifact_kind": RETRIEVAL_RERANKER_ARTIFACT_KIND,
            "artifact_name": artifact_name,
            "artifact_version": artifact_version,
            "candidate_harness_name": request.candidate_harness_name,
            "base_harness_name": request.base_harness_name,
            "baseline_harness_name": request.baseline_harness_name,
            "retrieval_training_run": {
                "retrieval_training_run_id": training_run.id,
                "judgment_set_id": training_run.judgment_set_id,
                "training_dataset_sha256": training_run.training_dataset_sha256,
                "training_example_count": training_run.example_count,
            },
            "feature_weights": feature_weights,
            "harness_overrides": harness_overrides,
            "evaluation": evaluation.model_dump(mode="json"),
            "release": release.model_dump(mode="json"),
        }
    )
    artifact_sha256 = _payload_sha256(artifact_payload)
    change_impact_report = _change_impact_report(
        session,
        artifact_id=artifact_id,
        artifact_payload=artifact_payload,
        artifact_sha256=artifact_sha256,
        training_run=training_run,
        evaluation=evaluation,
        release=release,
    )
    change_impact_sha256 = _payload_sha256(change_impact_report)
    row = RetrievalRerankerArtifact(
        id=artifact_id,
        retrieval_training_run_id=training_run.id,
        judgment_set_id=training_run.judgment_set_id,
        retrieval_learning_candidate_evaluation_id=candidate_row.id,
        search_harness_evaluation_id=evaluation.evaluation_id,
        search_harness_release_id=release.release_id,
        artifact_kind=RETRIEVAL_RERANKER_ARTIFACT_KIND,
        artifact_name=artifact_name,
        artifact_version=artifact_version,
        status="evaluated" if evaluation.status == "completed" else "failed",
        gate_outcome=release.outcome,
        baseline_harness_name=request.baseline_harness_name,
        candidate_harness_name=request.candidate_harness_name,
        source_types_json=list(request.source_types),
        limit=request.limit,
        training_dataset_sha256=training_run.training_dataset_sha256,
        training_example_count=training_run.example_count,
        positive_count=training_run.positive_count,
        negative_count=training_run.negative_count,
        missing_count=training_run.missing_count,
        hard_negative_count=training_run.hard_negative_count,
        thresholds_json=_thresholds_from_candidate_request(candidate_request),
        metrics_json=release.metrics,
        reasons_json=list(release.reasons),
        feature_weights_json=feature_weights,
        harness_overrides_json=harness_overrides,
        artifact_payload_json=artifact_payload,
        evaluation_snapshot_json=evaluation.model_dump(mode="json"),
        release_snapshot_json=release.model_dump(mode="json"),
        change_impact_report_json=change_impact_report,
        artifact_sha256=artifact_sha256,
        change_impact_sha256=change_impact_sha256,
        created_by=request.requested_by,
        review_note=request.review_note,
        created_at=created_at,
        completed_at=created_at,
    )
    session.add(row)
    session.flush()
    _record_reranker_artifact_governance_event(
        session,
        row=row,
        training_run=training_run,
    )
    return _to_reranker_artifact_response(session, row)


def list_retrieval_reranker_artifacts(
    session: Session,
    *,
    limit: int = 20,
    retrieval_training_run_id: UUID | None = None,
    candidate_harness_name: str | None = None,
) -> list[RetrievalRerankerArtifactSummaryResponse]:
    statement = select(RetrievalRerankerArtifact).order_by(
        RetrievalRerankerArtifact.created_at.desc()
    )
    if retrieval_training_run_id is not None:
        statement = statement.where(
            RetrievalRerankerArtifact.retrieval_training_run_id
            == retrieval_training_run_id
        )
    if candidate_harness_name:
        statement = statement.where(
            RetrievalRerankerArtifact.candidate_harness_name == candidate_harness_name
        )
    rows = session.execute(statement.limit(limit)).scalars().all()
    return [_to_reranker_artifact_summary(row) for row in rows]


def get_retrieval_reranker_artifact_detail(
    session: Session,
    artifact_id: UUID,
) -> RetrievalRerankerArtifactResponse:
    row = session.get(RetrievalRerankerArtifact, artifact_id)
    if row is None:
        raise _retrieval_reranker_artifact_not_found(artifact_id)
    return _to_reranker_artifact_response(session, row)
