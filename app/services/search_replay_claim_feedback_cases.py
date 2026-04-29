from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    SearchRequestRecord,
    SearchRequestResult,
    TechnicalReportClaimRetrievalFeedback,
)
from app.services import search_replay_common as replay_common
from app.services.session_utils import uses_in_memory_session

ReplayCase = replay_common.ReplayCase
TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE = (
    replay_common.TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE
)


def _claim_feedback_expected_top_n(
    feedback: TechnicalReportClaimRetrievalFeedback,
    result_row: SearchRequestResult | None,
) -> int | None:
    if feedback.learning_label == "positive":
        return 3 if feedback.feedback_status == "weak" else 1
    if feedback.learning_label == "negative" and result_row is not None:
        return 1
    return None


def _claim_feedback_query_fields(
    feedback: TechnicalReportClaimRetrievalFeedback,
    request_row: SearchRequestRecord | None,
) -> tuple[str, str, dict, int]:
    retrieval_context = feedback.retrieval_context_json or {}
    context_requests = retrieval_context.get("requests") or []
    primary_request = context_requests[0] if context_requests else {}
    query_text = (
        getattr(request_row, "query_text", None)
        or retrieval_context.get("primary_query_text")
        or primary_request.get("query_text")
        or feedback.claim_text
        or feedback.claim_id
    )
    mode = (
        getattr(request_row, "mode", None)
        or retrieval_context.get("primary_mode")
        or primary_request.get("mode")
        or "hybrid"
    )
    filters = getattr(request_row, "filters_json", None) or primary_request.get("filters") or {}
    replay_limit = getattr(request_row, "limit", None) or primary_request.get("limit") or 10
    return str(query_text), str(mode), dict(filters or {}), int(replay_limit)


def claim_feedback_traceability_issues(
    case: ReplayCase,
    metadata: dict,
) -> list[str]:
    issues: list[str] = []
    learning_label = metadata.get("learning_label")
    if not metadata.get("claim_feedback_id"):
        issues.append("claim_feedback_id_missing")
    if not metadata.get("feedback_payload_sha256"):
        issues.append("feedback_payload_hash_missing")
    if not metadata.get("source_payload_sha256"):
        issues.append("source_payload_hash_missing")
    if not case.source_search_request_id and not metadata.get("source_search_request_ids"):
        issues.append("source_search_request_missing")
    if learning_label in {"positive", "negative"} and (
        case.target_result_type is None or case.target_result_id is None
    ):
        issues.append("target_result_missing")
    return issues


def _claim_feedback_source_metadata(
    feedback: TechnicalReportClaimRetrievalFeedback,
    result_row: SearchRequestResult | None,
) -> dict:
    return {
        "source_reason": TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE,
        "claim_feedback_id": str(feedback.id),
        "technical_report_verification_task_id": str(
            feedback.technical_report_verification_task_id
        ),
        "claim_id": feedback.claim_id,
        "claim_text": feedback.claim_text,
        "claim_evidence_derivation_id": replay_common._uuid_str(
            feedback.claim_evidence_derivation_id
        ),
        "evidence_manifest_id": replay_common._uuid_str(feedback.evidence_manifest_id),
        "prov_export_artifact_id": replay_common._uuid_str(feedback.prov_export_artifact_id),
        "release_readiness_db_gate_id": replay_common._uuid_str(
            feedback.release_readiness_db_gate_id
        ),
        "semantic_governance_event_id": replay_common._uuid_str(
            feedback.semantic_governance_event_id
        ),
        "support_verdict": feedback.support_verdict,
        "support_score": feedback.support_score,
        "feedback_status": feedback.feedback_status,
        "learning_label": feedback.learning_label,
        "hard_negative_kind": feedback.hard_negative_kind,
        "feedback_payload_sha256": feedback.feedback_payload_sha256,
        "source_payload_sha256": feedback.source_payload_sha256,
        "source_search_request_id": replay_common._uuid_str(feedback.source_search_request_id),
        "source_search_request_ids": feedback.source_search_request_ids_json or [],
        "source_search_request_result_ids": (feedback.source_search_request_result_ids_json or []),
        "search_request_result_span_ids": feedback.search_request_result_span_ids_json or [],
        "retrieval_evidence_span_ids": feedback.retrieval_evidence_span_ids_json or [],
        "search_request_result_id": str(feedback.search_request_result_id)
        if feedback.search_request_result_id is not None
        else None,
        "target_result_rank": result_row.rank if result_row is not None else None,
        "target_source_filename": result_row.source_filename if result_row is not None else None,
    }


def _claim_feedback_replay_case(
    feedback: TechnicalReportClaimRetrievalFeedback,
    request_row: SearchRequestRecord | None,
    result_row: SearchRequestResult | None,
) -> ReplayCase:
    query_text, mode, filters, replay_limit = _claim_feedback_query_fields(
        feedback,
        request_row,
    )
    target_result_type = result_row.result_type if result_row is not None else None
    target_result_id = (
        result_row.table_id or result_row.chunk_id if result_row is not None else None
    )
    expected_top_n = _claim_feedback_expected_top_n(feedback, result_row)
    return ReplayCase(
        query_text=query_text,
        mode=mode,
        filters=filters,
        limit=replay_limit,
        expected_result_type=target_result_type,
        expected_top_n=expected_top_n,
        source_search_request_id=feedback.source_search_request_id,
        target_result_type=target_result_type,
        target_result_id=target_result_id,
        source_reason=TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE,
        source_metadata=_claim_feedback_source_metadata(feedback, result_row),
    )


def technical_report_claim_feedback_cases(
    session: Session,
    limit: int,
) -> list[ReplayCase]:
    if uses_in_memory_session(session):
        return technical_report_claim_feedback_cases_in_memory(session, limit)

    feedback_rows = session.execute(
        select(
            TechnicalReportClaimRetrievalFeedback,
            SearchRequestRecord,
            SearchRequestResult,
        )
        .outerjoin(
            SearchRequestRecord,
            SearchRequestRecord.id
            == TechnicalReportClaimRetrievalFeedback.source_search_request_id,
        )
        .outerjoin(
            SearchRequestResult,
            SearchRequestResult.id
            == TechnicalReportClaimRetrievalFeedback.search_request_result_id,
        )
        .order_by(TechnicalReportClaimRetrievalFeedback.created_at.desc())
        .limit(limit)
    ).all()
    return [
        _claim_feedback_replay_case(feedback, request_row, result_row)
        for feedback, request_row, result_row in feedback_rows
    ]


def technical_report_claim_feedback_cases_in_memory(
    session: Session,
    limit: int,
) -> list[ReplayCase]:
    feedback_rows = (
        session.execute(
            select(TechnicalReportClaimRetrievalFeedback).order_by(
                TechnicalReportClaimRetrievalFeedback.created_at.desc()
            )
        )
        .scalars()
        .all()
    )
    cases: list[ReplayCase] = []
    for feedback in feedback_rows:
        request_row = (
            session.get(SearchRequestRecord, feedback.source_search_request_id)
            if feedback.source_search_request_id is not None
            else None
        )
        result_row = (
            session.get(SearchRequestResult, feedback.search_request_result_id)
            if feedback.search_request_result_id is not None
            else None
        )
        cases.append(_claim_feedback_replay_case(feedback, request_row, result_row))
        if len(cases) >= limit:
            break
    return cases
