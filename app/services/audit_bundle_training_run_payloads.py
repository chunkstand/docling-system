from __future__ import annotations

from typing import Any

from app.db.models import (
    RetrievalHardNegative,
    RetrievalJudgment,
    RetrievalJudgmentSet,
    RetrievalTrainingRun,
)


def retrieval_training_run_payload(row: RetrievalTrainingRun) -> dict[str, Any]:
    return {
        "retrieval_training_run_id": str(row.id),
        "judgment_set_id": str(row.judgment_set_id),
        "status": row.status,
        "run_kind": row.run_kind,
        "training_dataset_sha256": row.training_dataset_sha256,
        "example_count": row.example_count,
        "positive_count": row.positive_count,
        "negative_count": row.negative_count,
        "missing_count": row.missing_count,
        "hard_negative_count": row.hard_negative_count,
        "summary": row.summary_json or {},
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def retrieval_training_run_full_payload(row: RetrievalTrainingRun) -> dict[str, Any]:
    payload = retrieval_training_run_payload(row)
    payload.update(
        {
            "search_harness_evaluation_id": (
                str(row.search_harness_evaluation_id) if row.search_harness_evaluation_id else None
            ),
            "search_harness_release_id": (
                str(row.search_harness_release_id) if row.search_harness_release_id else None
            ),
            "semantic_governance_event_id": (
                str(row.semantic_governance_event_id) if row.semantic_governance_event_id else None
            ),
            "training_payload": row.training_payload_json or {},
        }
    )
    return payload


def retrieval_judgment_set_payload(row: RetrievalJudgmentSet) -> dict[str, Any]:
    return {
        "judgment_set_id": str(row.id),
        "set_name": row.set_name,
        "set_kind": row.set_kind,
        "source_types": row.source_types_json or [],
        "source_limit": row.source_limit,
        "criteria": row.criteria_json or {},
        "summary": row.summary_json or {},
        "judgment_count": row.judgment_count,
        "positive_count": row.positive_count,
        "negative_count": row.negative_count,
        "missing_count": row.missing_count,
        "hard_negative_count": row.hard_negative_count,
        "payload_sha256": row.payload_sha256,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat(),
    }


def retrieval_judgment_payload(row: RetrievalJudgment) -> dict[str, Any]:
    return {
        "judgment_id": str(row.id),
        "judgment_set_id": str(row.judgment_set_id),
        "judgment_kind": row.judgment_kind,
        "judgment_label": row.judgment_label,
        "source_type": row.source_type,
        "source_ref_id": str(row.source_ref_id) if row.source_ref_id else None,
        "search_feedback_id": str(row.search_feedback_id) if row.search_feedback_id else None,
        "search_replay_query_id": (
            str(row.search_replay_query_id) if row.search_replay_query_id else None
        ),
        "search_replay_run_id": str(row.search_replay_run_id) if row.search_replay_run_id else None,
        "evaluation_query_id": str(row.evaluation_query_id) if row.evaluation_query_id else None,
        "source_search_request_id": (
            str(row.source_search_request_id) if row.source_search_request_id else None
        ),
        "search_request_id": str(row.search_request_id) if row.search_request_id else None,
        "search_request_result_id": (
            str(row.search_request_result_id) if row.search_request_result_id else None
        ),
        "result_rank": row.result_rank,
        "result_type": row.result_type,
        "result_id": str(row.result_id) if row.result_id else None,
        "document_id": str(row.document_id) if row.document_id else None,
        "run_id": str(row.run_id) if row.run_id else None,
        "score": row.score,
        "query_text": row.query_text,
        "mode": row.mode,
        "filters": row.filters_json or {},
        "expected_result_type": row.expected_result_type,
        "expected_top_n": row.expected_top_n,
        "harness_name": row.harness_name,
        "reranker_name": row.reranker_name,
        "reranker_version": row.reranker_version,
        "retrieval_profile_name": row.retrieval_profile_name,
        "rerank_features": row.rerank_features_json or {},
        "evidence_refs": row.evidence_refs_json or [],
        "rationale": row.rationale,
        "payload": row.payload_json or {},
        "source_payload_sha256": row.source_payload_sha256,
        "deduplication_key": row.deduplication_key,
        "created_at": row.created_at.isoformat(),
    }


def retrieval_hard_negative_payload(row: RetrievalHardNegative) -> dict[str, Any]:
    return {
        "hard_negative_id": str(row.id),
        "judgment_set_id": str(row.judgment_set_id),
        "judgment_id": str(row.judgment_id),
        "positive_judgment_id": (
            str(row.positive_judgment_id) if row.positive_judgment_id else None
        ),
        "hard_negative_kind": row.hard_negative_kind,
        "source_type": row.source_type,
        "source_ref_id": str(row.source_ref_id) if row.source_ref_id else None,
        "search_feedback_id": str(row.search_feedback_id) if row.search_feedback_id else None,
        "search_replay_query_id": (
            str(row.search_replay_query_id) if row.search_replay_query_id else None
        ),
        "search_replay_run_id": str(row.search_replay_run_id) if row.search_replay_run_id else None,
        "evaluation_query_id": str(row.evaluation_query_id) if row.evaluation_query_id else None,
        "source_search_request_id": (
            str(row.source_search_request_id) if row.source_search_request_id else None
        ),
        "search_request_id": str(row.search_request_id) if row.search_request_id else None,
        "search_request_result_id": (
            str(row.search_request_result_id) if row.search_request_result_id else None
        ),
        "result_rank": row.result_rank,
        "result_type": row.result_type,
        "result_id": str(row.result_id) if row.result_id else None,
        "document_id": str(row.document_id) if row.document_id else None,
        "run_id": str(row.run_id) if row.run_id else None,
        "score": row.score,
        "query_text": row.query_text,
        "mode": row.mode,
        "filters": row.filters_json or {},
        "rerank_features": row.rerank_features_json or {},
        "expected_result_type": row.expected_result_type,
        "expected_top_n": row.expected_top_n,
        "evidence_refs": row.evidence_refs_json or [],
        "reason": row.reason,
        "details": row.details_json or {},
        "source_payload_sha256": row.source_payload_sha256,
        "deduplication_key": row.deduplication_key,
        "created_at": row.created_at.isoformat(),
    }
