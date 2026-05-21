from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.json_utils import canonical_json_value as _json_payload
from app.db.public.audit_and_evidence import TechnicalReportClaimRetrievalFeedback
from app.db.public.retrieval import (
    RetrievalHardNegativeKind,
    RetrievalJudgmentKind,
    SearchFeedback,
    SearchReplayQuery,
    SearchReplayRun,
    SearchRequestRecord,
    SearchRequestResult,
)
from app.services.query_utils import load_by_ids as _load_by_ids
from app.services.retrieval_learning_dataset_rows import (
    evidence_refs_by_result_id,
    group_results_by_request,
    make_hard_negative_row,
    make_judgment_row,
    replay_run_source_type,
    request_fields,
    target_result_from_details,
)

TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE = "technical_report_claim_feedback"


def collect_feedback_sources(
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
    results_by_request_id = group_results_by_request(session, request_ids)
    evidence_by_result_id = evidence_refs_by_result_id(
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
        query = request_fields(request)
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

        judgment = make_judgment_row(
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
                make_hard_negative_row(
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
                    make_hard_negative_row(
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
                    make_hard_negative_row(
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


def collect_replay_sources(
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
    results_by_request_id = group_results_by_request(session, replay_request_ids)
    result_ids = {
        result.id
        for results in results_by_request_id.values()
        for result in results
    }
    evidence_by_result_id = evidence_refs_by_result_id(session, result_ids)

    judgments: list[dict[str, Any]] = []
    hard_negatives: list[dict[str, Any]] = []

    for replay_query in replay_queries:
        replay_run = replay_runs_by_id.get(replay_query.replay_run_id)
        replay_request = replay_requests_by_id.get(replay_query.replay_search_request_id)
        source_request = source_requests_by_id.get(replay_query.source_search_request_id)
        query = request_fields(replay_request or source_request)
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
            "replay_source_type": replay_run_source_type(replay_run),
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
            result = target_result_from_details(replay_query, replay_results)
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
                make_judgment_row(
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
            judgments.append(
                make_judgment_row(
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
            )
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
        judgment = make_judgment_row(
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
            make_hard_negative_row(
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


def collect_technical_report_claim_feedback_sources(
    session: Session,
    *,
    judgment_set_id: UUID,
    limit: int,
    created_at: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    feedback_rows = list(
        session.scalars(
            select(TechnicalReportClaimRetrievalFeedback)
            .order_by(TechnicalReportClaimRetrievalFeedback.created_at.desc())
            .limit(limit)
        )
    )
    request_ids = {
        row.source_search_request_id
        for row in feedback_rows
        if row.source_search_request_id is not None
    }
    result_ids = {
        row.search_request_result_id
        for row in feedback_rows
        if row.search_request_result_id is not None
    }
    requests_by_id = _load_by_ids(session, SearchRequestRecord, request_ids)
    results_by_id = _load_by_ids(session, SearchRequestResult, result_ids)
    evidence_by_result_id = evidence_refs_by_result_id(session, result_ids)

    judgments: list[dict[str, Any]] = []
    hard_negatives: list[dict[str, Any]] = []
    for feedback in feedback_rows:
        request = (
            requests_by_id.get(feedback.source_search_request_id)
            if feedback.source_search_request_id is not None
            else None
        )
        result = (
            results_by_id.get(feedback.search_request_result_id)
            if feedback.search_request_result_id is not None
            else None
        )
        query = request_fields(request)
        if not query["query_text"]:
            query = {
                **query,
                "query_text": feedback.claim_text or feedback.claim_id,
                "mode": "hybrid",
                "filters": {},
            }
        retrieval_context = feedback.retrieval_context_json or {}
        primary_context = {
            "harness_name": retrieval_context.get("primary_harness_name"),
            "reranker_name": retrieval_context.get("primary_reranker_name"),
            "reranker_version": retrieval_context.get("primary_reranker_version"),
            "retrieval_profile_name": retrieval_context.get("primary_retrieval_profile_name"),
            "harness_config": retrieval_context.get("primary_harness_config") or {},
        }
        query = {**query, **{key: value for key, value in primary_context.items() if value}}
        evidence_refs = (
            list(feedback.evidence_refs_json or [])
            or evidence_by_result_id.get(feedback.search_request_result_id, [])
        )
        if feedback.learning_label == RetrievalJudgmentKind.POSITIVE.value:
            judgment_kind = RetrievalJudgmentKind.POSITIVE.value
            judgment_label = "technical_report_claim_supported"
            rationale = "Technical-report verification judged this cited claim supported."
        elif feedback.learning_label == RetrievalJudgmentKind.MISSING.value:
            judgment_kind = RetrievalJudgmentKind.MISSING.value
            judgment_label = "technical_report_claim_missing_evidence"
            rationale = "Technical-report verification found missing traceable retrieval evidence."
        else:
            judgment_kind = RetrievalJudgmentKind.NEGATIVE.value
            judgment_label = f"technical_report_claim_{feedback.feedback_status}"
            rationale = "Technical-report verification rejected or contradicted the cited evidence."

        source_details = _json_payload(
            {
                "source_family": TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE,
                "feedback_id": feedback.id,
                "technical_report_verification_task_id": (
                    feedback.technical_report_verification_task_id
                ),
                "claim_id": feedback.claim_id,
                "claim_text": feedback.claim_text,
                "claim_evidence_derivation_id": feedback.claim_evidence_derivation_id,
                "evidence_manifest_id": feedback.evidence_manifest_id,
                "prov_export_artifact_id": feedback.prov_export_artifact_id,
                "release_readiness_db_gate_id": feedback.release_readiness_db_gate_id,
                "semantic_governance_event_id": feedback.semantic_governance_event_id,
                "support_verdict": feedback.support_verdict,
                "support_score": feedback.support_score,
                "feedback_status": feedback.feedback_status,
                "learning_label": feedback.learning_label,
                "hard_negative_kind": feedback.hard_negative_kind,
                "feedback_payload_sha256": feedback.feedback_payload_sha256,
                "source_payload_sha256": feedback.source_payload_sha256,
                "source_payload": feedback.source_payload_json or {},
            }
        )
        judgment = make_judgment_row(
            judgment_set_id=judgment_set_id,
            source_type=TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE,
            source_ref_id=feedback.id,
            judgment_kind=judgment_kind,
            judgment_label=judgment_label,
            query=query,
            result=result,
            evidence_refs=evidence_refs,
            created_at=created_at,
            rationale=rationale,
            source_search_request_id=feedback.source_search_request_id,
            search_request_id=feedback.source_search_request_id,
            expected_result_type=(result.result_type if result is not None else None),
            expected_top_n=1 if result is not None else None,
            details=source_details,
        )
        judgments.append(judgment)

        if judgment_kind == RetrievalJudgmentKind.NEGATIVE.value and result is not None:
            hard_negatives.append(
                make_hard_negative_row(
                    judgment_set_id=judgment_set_id,
                    judgment_id=judgment["id"],
                    hard_negative_kind=(
                        feedback.hard_negative_kind
                        or RetrievalHardNegativeKind.EXPLICIT_IRRELEVANT.value
                    ),
                    source_type=TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE,
                    source_ref_id=feedback.id,
                    query=query,
                    result=result,
                    created_at=created_at,
                    reason="Claim feedback labels this retrieved evidence as unsuitable support.",
                    source_search_request_id=feedback.source_search_request_id,
                    expected_result_type=result.result_type,
                    expected_top_n=1,
                    evidence_refs=evidence_refs,
                    details=source_details,
                )
            )
    return judgments, hard_negatives
