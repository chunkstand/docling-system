from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

import app.services.evaluation_scoring as scoring_owners
from app.core.files import source_filename_matches
from app.db.public.ingest import Document
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.evaluation_fixtures import EvaluationAnswerCase


def _evaluate_answer_case(
    session: Session,
    *,
    document: Document,
    run_id: UUID,
    baseline_run_id: UUID | None,
    evaluation_id: UUID,
    case: EvaluationAnswerCase,
) -> dict:
    request = ChatRequest(
        question=case.question,
        mode=case.mode,
        document_id=document.id if case.include_document_filter else None,
        top_k=case.top_k,
    )
    candidate_response = scoring_owners.answer_question(
        session,
        request,
        run_id=run_id if case.include_document_filter else None,
        origin="evaluation_answer_candidate",
        evaluation_id=evaluation_id,
        persist=False,
    )
    baseline_response = (
        scoring_owners.answer_question(
            session,
            request,
            run_id=baseline_run_id if case.include_document_filter else None,
            origin="evaluation_answer_baseline",
            evaluation_id=evaluation_id,
            persist=False,
        )
        if baseline_run_id and case.include_document_filter
        else None
    )

    def _answer_passed(
        response: ChatResponse | None,
    ) -> tuple[bool, list[str], int, int | None, int | None]:
        if response is None:
            return False, case.expected_answer_contains, 0, None, None
        missing_substrings = scoring_owners._missing_answer_substrings(
            response.answer, case.expected_answer_contains
        )
        citation_count = len(response.citations)
        matching_citation_count = None
        foreign_citation_count = None
        if case.expected_citation_source_filename is not None:
            matching_citation_count = sum(
                1
                for citation in response.citations
                if source_filename_matches(
                    citation.source_filename, case.expected_citation_source_filename
                )
            )
            foreign_citation_count = citation_count - matching_citation_count
        if case.expect_no_answer:
            maximum_citation_count = case.maximum_citation_count
            if maximum_citation_count is None:
                maximum_citation_count = 0
            passed = response.used_fallback and citation_count <= maximum_citation_count
        else:
            passed = (
                not missing_substrings
                and citation_count >= case.minimum_citation_count
                and (case.allow_fallback or not response.used_fallback)
                and (
                    case.expected_citation_source_filename is None
                    or (matching_citation_count or 0) > 0
                )
                and (
                    case.maximum_foreign_citations is None
                    or (foreign_citation_count or 0) <= case.maximum_foreign_citations
                )
            )
        return (
            passed,
            missing_substrings,
            citation_count,
            matching_citation_count,
            foreign_citation_count,
        )

    (
        candidate_passed,
        candidate_missing_substrings,
        candidate_citation_count,
        candidate_matching_citation_count,
        candidate_foreign_citation_count,
    ) = _answer_passed(candidate_response)
    (
        baseline_passed,
        baseline_missing_substrings,
        baseline_citation_count,
        baseline_matching_citation_count,
        baseline_foreign_citation_count,
    ) = _answer_passed(baseline_response)
    delta_kind = scoring_owners._classify_delta(candidate_passed, baseline_passed, None)
    filters_payload = dict(case.filters)
    if case.include_document_filter:
        filters_payload["document_id"] = str(document.id)

    return {
        "query_text": case.question,
        "mode": case.mode,
        "filters_json": filters_payload,
        "expected_result_type": None,
        "expected_top_n": None,
        "passed": candidate_passed,
        "candidate_rank": None,
        "baseline_rank": None,
        "rank_delta": None,
        "candidate_score": None,
        "baseline_score": None,
        "candidate_result_type": "answer" if candidate_response is not None else None,
        "baseline_result_type": "answer" if baseline_response is not None else None,
        "candidate_label": scoring_owners._answer_excerpt(candidate_response.answer),
        "baseline_label": scoring_owners._answer_excerpt(baseline_response.answer)
        if baseline_response is not None
        else None,
        "details_json": {
            "evaluation_kind": "answer",
            "delta_kind": delta_kind,
            "expected_answer_contains": case.expected_answer_contains,
            "minimum_citation_count": case.minimum_citation_count,
            "allow_fallback": case.allow_fallback,
            "expect_no_answer": case.expect_no_answer,
            "maximum_citation_count": case.maximum_citation_count,
            "expected_result_type": case.expected_result_type,
            "expected_citation_source_filename": case.expected_citation_source_filename,
            "maximum_foreign_citations": case.maximum_foreign_citations,
            "candidate_missing_substrings": candidate_missing_substrings,
            "candidate_citation_count": candidate_citation_count,
            "candidate_matching_citation_count": candidate_matching_citation_count,
            "candidate_foreign_citation_count": candidate_foreign_citation_count,
            "candidate_used_fallback": candidate_response.used_fallback,
            "candidate_warning": candidate_response.warning,
            "candidate_search_request_id": str(candidate_response.search_request_id)
            if candidate_response.search_request_id
            else None,
            "candidate_chat_answer_id": str(candidate_response.chat_answer_id)
            if candidate_response.chat_answer_id
            else None,
            "baseline_missing_substrings": baseline_missing_substrings,
            "baseline_citation_count": baseline_citation_count,
            "baseline_matching_citation_count": baseline_matching_citation_count,
            "baseline_foreign_citation_count": baseline_foreign_citation_count,
            "baseline_used_fallback": baseline_response.used_fallback
            if baseline_response is not None
            else None,
            "baseline_warning": (
                baseline_response.warning if baseline_response is not None else None
            ),
            "baseline_search_request_id": str(baseline_response.search_request_id)
            if baseline_response is not None and baseline_response.search_request_id
            else None,
            "baseline_chat_answer_id": str(baseline_response.chat_answer_id)
            if baseline_response is not None and baseline_response.chat_answer_id
            else None,
        },
        "delta_kind": delta_kind,
    }
