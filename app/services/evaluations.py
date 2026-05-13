from __future__ import annotations

import uuid
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.core.config import get_settings as _get_settings
from app.core.files import path_exists, source_filename_matches
from app.core.time import utcnow
from app.db.models import (
    Document,
    DocumentFigure,
    DocumentRun,
    DocumentRunEvaluation,
    DocumentRunEvaluationQuery,
    DocumentTable,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.evaluations import (
    EvaluationDetailResponse,
    EvaluationQueryResultResponse,
    EvaluationSummaryResponse,
)
from app.schemas.search import SearchResult
from app.services import evaluation_fixtures as fixture_owners
from app.services.chat import answer_question
from app.services.evaluation_execution import (
    EvaluationBatchResult,
    build_completed_evaluation_summary,
    execute_answer_queries,
    execute_retrieval_queries,
)
from app.services.search import search_documents

EVAL_VERSION = 1
DEFAULT_CORPUS_NAME = "default"
get_settings = _get_settings
DEFAULT_CORPUS_PATH = fixture_owners.DEFAULT_CORPUS_PATH
AUTO_CORPUS_FILENAME = fixture_owners.AUTO_CORPUS_FILENAME
AUTO_FIXTURE_KIND = fixture_owners.AUTO_FIXTURE_KIND
EvaluationFixture = fixture_owners.EvaluationFixture
EvaluationQueryCase = fixture_owners.EvaluationQueryCase
EvaluationAnswerCase = fixture_owners.EvaluationAnswerCase
EvaluationMergeExpectation = fixture_owners.EvaluationMergeExpectation
EvaluationThresholds = fixture_owners.EvaluationThresholds
_auto_corpus_path = fixture_owners._auto_corpus_path
_configured_manual_corpus_path = fixture_owners._configured_manual_corpus_path
_matching_rank = fixture_owners._matching_rank
_metadata_for_row = fixture_owners._metadata_for_row
_normalized_caption_text = fixture_owners._normalized_caption_text
build_auto_evaluation_fixture_document = fixture_owners.build_auto_evaluation_fixture_document
ensure_auto_evaluation_fixture = fixture_owners.ensure_auto_evaluation_fixture
fixture_for_document = fixture_owners.fixture_for_document
load_evaluation_fixtures = fixture_owners.load_evaluation_fixtures


def resolve_baseline_run_id(
    candidate_run_id: UUID,
    active_run_id: UUID | None,
    *,
    explicit_baseline_run_id: UUID | None = None,
) -> UUID | None:
    if explicit_baseline_run_id is not None:
        return None if explicit_baseline_run_id == candidate_run_id else explicit_baseline_run_id
    if active_run_id is None or active_run_id == candidate_run_id:
        return None
    return active_run_id


def _run_label(result: SearchResult | None) -> str | None:
    if result is None:
        return None
    if result.result_type == "table":
        return result.table_title or result.table_heading or result.table_preview
    return result.heading or result.chunk_text


def _top_result_details(results: list[SearchResult], limit: int = 3) -> list[dict]:
    return [
        {
            "rank": idx,
            "result_type": result.result_type,
            "label": _run_label(result),
            "score": result.score,
            "page_from": result.page_from,
            "page_to": result.page_to,
            "source_filename": result.source_filename,
        }
        for idx, result in enumerate(results[:limit], start=1)
    ]


def _result_at_rank(results: list[SearchResult], rank: int | None) -> SearchResult | None:
    if rank is None or rank <= 0 or rank > len(results):
        return None
    return results[rank - 1]


def _result_matches_expected(
    result: SearchResult,
    expected_result_type: str,
    *,
    expected_source_filename: str | None = None,
) -> bool:
    return result.result_type == expected_result_type and source_filename_matches(
        result.source_filename, expected_source_filename
    )


def _rank_delta(candidate_rank: int | None, baseline_rank: int | None) -> int | None:
    if candidate_rank is None or baseline_rank is None:
        return None
    return baseline_rank - candidate_rank


def _classify_delta(candidate_passed: bool, baseline_passed: bool, rank_delta: int | None) -> str:
    if candidate_passed and not baseline_passed:
        return "improved"
    if baseline_passed and not candidate_passed:
        return "regressed"
    if rank_delta is None or rank_delta == 0:
        return "stable"
    return "improved" if rank_delta > 0 else "regressed"


def _upsert_evaluation_row(
    session: Session,
    run: DocumentRun,
    *,
    corpus_name: str,
    fixture_name: str | None,
) -> DocumentRunEvaluation:
    existing = session.execute(
        select(DocumentRunEvaluation).where(
            DocumentRunEvaluation.run_id == run.id,
            DocumentRunEvaluation.corpus_name == corpus_name,
            DocumentRunEvaluation.eval_version == EVAL_VERSION,
        )
    ).scalar_one_or_none()
    if existing is not None:
        session.query(DocumentRunEvaluationQuery).filter(
            DocumentRunEvaluationQuery.evaluation_id == existing.id
        ).delete()
        session.delete(existing)
        session.flush()

    evaluation = DocumentRunEvaluation(
        id=uuid.uuid4(),
        run_id=run.id,
        corpus_name=corpus_name,
        fixture_name=fixture_name,
        eval_version=EVAL_VERSION,
        status="pending",
        summary_json={},
        created_at=utcnow(),
    )
    session.add(evaluation)
    session.flush()
    return evaluation


def _table_label(row: object) -> str:
    return (
        getattr(row, "title", None)
        or getattr(row, "heading", None)
        or getattr(row, "preview_text", None)
        or f"table_{getattr(row, 'table_index', 'unknown')}"
    )


def _source_segment_count(row: object) -> int:
    metadata = _metadata_for_row(row)
    return int(metadata.get("source_segment_count") or metadata.get("segment_count") or 0)


def _text_contains(value: str | None, expected_substring: str | None) -> bool:
    if expected_substring is None:
        return True
    return expected_substring.lower() in (value or "").lower()


def _table_matches_merge_expectation(
    table: object, expectation: EvaluationMergeExpectation
) -> bool:
    metadata = _metadata_for_row(table)
    if not _text_contains(getattr(table, "title", None), expectation.title_contains):
        return False
    if not _text_contains(getattr(table, "heading", None), expectation.heading_contains):
        return False
    if (
        expectation.page_from is not None
        and getattr(table, "page_from", None) != expectation.page_from
    ):
        return False
    if expectation.page_to is not None and getattr(table, "page_to", None) != expectation.page_to:
        return False
    if _source_segment_count(table) < expectation.minimum_source_segment_count:
        return False
    if (
        expectation.overlay_applied is not None
        and bool(metadata.get("overlay_applied")) != expectation.overlay_applied
    ):
        return False
    if (
        expectation.overlay_family_key is not None
        and metadata.get("overlay_family_key") != expectation.overlay_family_key
    ):
        return False
    return True


def _answer_excerpt(answer_text: str, limit: int = 180) -> str:
    normalized = " ".join(answer_text.split()).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


def _missing_answer_substrings(answer_text: str, expected_substrings: list[str]) -> list[str]:
    normalized_answer = answer_text.lower()
    return [
        substring for substring in expected_substrings if substring.lower() not in normalized_answer
    ]


def _expected_document_source(case: EvaluationQueryCase) -> str | None:
    return case.expected_source_filename or case.expected_top_result_source_filename


def _top_n_source_hit_count(
    results: list[SearchResult], expected_source_filename: str | None, top_n: int
) -> int | None:
    if expected_source_filename is None:
        return None
    return sum(
        1
        for result in results[:top_n]
        if source_filename_matches(result.source_filename, expected_source_filename)
    )


def _foreign_results_before_first_expected_hit(
    results: list[SearchResult],
    expected_result_type: str,
    *,
    expected_source_filename: str | None = None,
) -> int | None:
    rank = _matching_rank(
        results,
        expected_result_type,
        expected_source_filename=expected_source_filename,
    )
    if rank is None or expected_source_filename is None:
        return None
    return sum(
        1
        for result in results[: rank - 1]
        if not source_filename_matches(result.source_filename, expected_source_filename)
    )


def _top_result_source_filename(results: list[SearchResult]) -> str | None:
    return results[0].source_filename if results else None


def _expected_hit_count_in_window(
    results: list[SearchResult],
    *,
    expected_result_type: str,
    expected_source_filename: str | None,
    window: int,
) -> int:
    return sum(
        1
        for result in results[:window]
        if _result_matches_expected(
            result,
            expected_result_type,
            expected_source_filename=expected_source_filename,
        )
    )


def _reciprocal_rank(rank: int | None) -> float:
    if rank is None or rank <= 0:
        return 0.0
    return 1.0 / rank


def _has_foreign_top_result(
    results: list[SearchResult], expected_source_filename: str | None
) -> bool:
    if not results or expected_source_filename is None:
        return False
    return not source_filename_matches(results[0].source_filename, expected_source_filename)


def _retrieval_failure_kind(
    *,
    case: EvaluationQueryCase,
    results: list[SearchResult],
    passed: bool,
    rank: int | None,
    top_result_is_foreign: bool,
    expected_hits_in_top_n: int | None,
    foreign_results_before_first_expected_hit: int | None,
) -> str | None:
    if passed:
        return None
    if not results:
        return "zero_results"
    if rank is None:
        return "wrong_result"
    if case.expected_top_result_source_filename is not None and top_result_is_foreign:
        return "foreign_top_result"
    if (
        case.maximum_foreign_results_before_first_expected_hit is not None
        and foreign_results_before_first_expected_hit is not None
        and foreign_results_before_first_expected_hit
        > case.maximum_foreign_results_before_first_expected_hit
    ):
        return "foreign_results_before_expected_hit"
    if (
        case.minimum_top_n_hits_from_expected_document is not None
        and (expected_hits_in_top_n or 0) < case.minimum_top_n_hits_from_expected_document
    ):
        return "insufficient_expected_hits"
    if rank > case.expected_top_n:
        return "rank_miss"
    return "constraint_failed"


def _empty_retrieval_rank_metrics() -> dict:
    return {
        "candidate_mrr": 0.0,
        "baseline_mrr": 0.0,
        "candidate_top_1_hit_queries": 0,
        "candidate_top_3_hit_queries": 0,
        "candidate_top_5_hit_queries": 0,
        "baseline_top_1_hit_queries": 0,
        "baseline_top_3_hit_queries": 0,
        "baseline_top_5_hit_queries": 0,
        "candidate_zero_result_queries": 0,
        "candidate_wrong_result_queries": 0,
        "candidate_foreign_top_result_queries": 0,
        "baseline_zero_result_queries": 0,
        "baseline_wrong_result_queries": 0,
        "baseline_foreign_top_result_queries": 0,
        "candidate_failure_kind_counts": {},
        "baseline_failure_kind_counts": {},
    }


def _increment_failure_kind(counts: dict[str, int], failure_kind: str | None) -> None:
    if failure_kind is None:
        return
    counts[failure_kind] = counts.get(failure_kind, 0) + 1


def _summarize_retrieval_rank_metrics(outcomes: list[dict]) -> dict:
    metrics = _empty_retrieval_rank_metrics()
    retrieval_query_count = len(outcomes)
    if retrieval_query_count == 0:
        return metrics

    candidate_mrr_sum = 0.0
    baseline_mrr_sum = 0.0
    for outcome in outcomes:
        details = outcome["details_json"]
        candidate_mrr_sum += float(details.get("candidate_reciprocal_rank") or 0.0)
        baseline_mrr_sum += float(details.get("baseline_reciprocal_rank") or 0.0)
        metrics["candidate_top_1_hit_queries"] += int(
            (details.get("candidate_expected_hits_in_top_1") or 0) > 0
        )
        metrics["candidate_top_3_hit_queries"] += int(
            (details.get("candidate_expected_hits_in_top_3") or 0) > 0
        )
        metrics["candidate_top_5_hit_queries"] += int(
            (details.get("candidate_expected_hits_in_top_5") or 0) > 0
        )
        metrics["baseline_top_1_hit_queries"] += int(
            (details.get("baseline_expected_hits_in_top_1") or 0) > 0
        )
        metrics["baseline_top_3_hit_queries"] += int(
            (details.get("baseline_expected_hits_in_top_3") or 0) > 0
        )
        metrics["baseline_top_5_hit_queries"] += int(
            (details.get("baseline_expected_hits_in_top_5") or 0) > 0
        )
        metrics["candidate_zero_result_queries"] += int(details.get("candidate_zero_results") or 0)
        metrics["candidate_wrong_result_queries"] += int(
            details.get("candidate_failure_kind") == "wrong_result"
        )
        metrics["candidate_foreign_top_result_queries"] += int(
            details.get("candidate_foreign_top_result") or 0
        )
        metrics["baseline_zero_result_queries"] += int(details.get("baseline_zero_results") or 0)
        metrics["baseline_wrong_result_queries"] += int(
            details.get("baseline_failure_kind") == "wrong_result"
        )
        metrics["baseline_foreign_top_result_queries"] += int(
            details.get("baseline_foreign_top_result") or 0
        )
        _increment_failure_kind(
            metrics["candidate_failure_kind_counts"],
            details.get("candidate_failure_kind"),
        )
        _increment_failure_kind(
            metrics["baseline_failure_kind_counts"],
            details.get("baseline_failure_kind"),
        )

    metrics["candidate_mrr"] = candidate_mrr_sum / retrieval_query_count
    metrics["baseline_mrr"] = baseline_mrr_sum / retrieval_query_count
    return metrics


def _evaluate_retrieval_case(
    *,
    case: EvaluationQueryCase,
    filters_payload: dict,
    candidate_results: list[SearchResult],
    baseline_results: list[SearchResult],
) -> dict:
    expected_document_source = _expected_document_source(case)
    candidate_rank = _matching_rank(
        candidate_results,
        case.expected_result_type,
        expected_source_filename=expected_document_source,
    )
    baseline_rank = _matching_rank(
        baseline_results,
        case.expected_result_type,
        expected_source_filename=expected_document_source,
    )
    candidate_top_result_source = _top_result_source_filename(candidate_results)
    baseline_top_result_source = _top_result_source_filename(baseline_results)
    candidate_source_hit_count = _top_n_source_hit_count(
        candidate_results, expected_document_source, case.expected_top_n
    )
    baseline_source_hit_count = _top_n_source_hit_count(
        baseline_results, expected_document_source, case.expected_top_n
    )
    candidate_foreign_before_first_hit = _foreign_results_before_first_expected_hit(
        candidate_results,
        case.expected_result_type,
        expected_source_filename=expected_document_source,
    )
    baseline_foreign_before_first_hit = _foreign_results_before_first_expected_hit(
        baseline_results,
        case.expected_result_type,
        expected_source_filename=expected_document_source,
    )
    candidate_expected_hits_top_1 = _expected_hit_count_in_window(
        candidate_results,
        expected_result_type=case.expected_result_type,
        expected_source_filename=expected_document_source,
        window=1,
    )
    candidate_expected_hits_top_3 = _expected_hit_count_in_window(
        candidate_results,
        expected_result_type=case.expected_result_type,
        expected_source_filename=expected_document_source,
        window=3,
    )
    candidate_expected_hits_top_5 = _expected_hit_count_in_window(
        candidate_results,
        expected_result_type=case.expected_result_type,
        expected_source_filename=expected_document_source,
        window=5,
    )
    baseline_expected_hits_top_1 = _expected_hit_count_in_window(
        baseline_results,
        expected_result_type=case.expected_result_type,
        expected_source_filename=expected_document_source,
        window=1,
    )
    baseline_expected_hits_top_3 = _expected_hit_count_in_window(
        baseline_results,
        expected_result_type=case.expected_result_type,
        expected_source_filename=expected_document_source,
        window=3,
    )
    baseline_expected_hits_top_5 = _expected_hit_count_in_window(
        baseline_results,
        expected_result_type=case.expected_result_type,
        expected_source_filename=expected_document_source,
        window=5,
    )
    candidate_foreign_top_result = _has_foreign_top_result(
        candidate_results, expected_document_source
    )
    baseline_foreign_top_result = _has_foreign_top_result(
        baseline_results, expected_document_source
    )

    candidate_passed = candidate_rank is not None and candidate_rank <= case.expected_top_n
    baseline_passed = baseline_rank is not None and baseline_rank <= case.expected_top_n

    if case.expected_top_result_source_filename is not None:
        candidate_passed = candidate_passed and source_filename_matches(
            candidate_top_result_source, case.expected_top_result_source_filename
        )
        baseline_passed = baseline_passed and source_filename_matches(
            baseline_top_result_source, case.expected_top_result_source_filename
        )
    if case.minimum_top_n_hits_from_expected_document is not None:
        candidate_passed = candidate_passed and (
            (candidate_source_hit_count or 0) >= case.minimum_top_n_hits_from_expected_document
        )
        baseline_passed = baseline_passed and (
            (baseline_source_hit_count or 0) >= case.minimum_top_n_hits_from_expected_document
        )
    if case.maximum_foreign_results_before_first_expected_hit is not None:
        candidate_passed = candidate_passed and (
            candidate_foreign_before_first_hit is not None
            and candidate_foreign_before_first_hit
            <= case.maximum_foreign_results_before_first_expected_hit
        )
        baseline_passed = baseline_passed and (
            baseline_foreign_before_first_hit is not None
            and baseline_foreign_before_first_hit
            <= case.maximum_foreign_results_before_first_expected_hit
        )

    delta_kind = _classify_delta(
        candidate_passed,
        baseline_passed,
        _rank_delta(candidate_rank, baseline_rank),
    )
    candidate_failure_kind = _retrieval_failure_kind(
        case=case,
        results=candidate_results,
        passed=candidate_passed,
        rank=candidate_rank,
        top_result_is_foreign=candidate_foreign_top_result,
        expected_hits_in_top_n=candidate_source_hit_count,
        foreign_results_before_first_expected_hit=candidate_foreign_before_first_hit,
    )
    baseline_failure_kind = _retrieval_failure_kind(
        case=case,
        results=baseline_results,
        passed=baseline_passed,
        rank=baseline_rank,
        top_result_is_foreign=baseline_foreign_top_result,
        expected_hits_in_top_n=baseline_source_hit_count,
        foreign_results_before_first_expected_hit=baseline_foreign_before_first_hit,
    )
    candidate_match = _result_at_rank(candidate_results, candidate_rank)
    baseline_match = _result_at_rank(baseline_results, baseline_rank)
    return {
        "query_text": case.query,
        "mode": case.mode,
        "filters_json": filters_payload,
        "expected_result_type": case.expected_result_type,
        "expected_top_n": case.expected_top_n,
        "passed": candidate_passed,
        "candidate_rank": candidate_rank,
        "baseline_rank": baseline_rank,
        "rank_delta": _rank_delta(candidate_rank, baseline_rank),
        "candidate_score": candidate_match.score if candidate_match else None,
        "baseline_score": baseline_match.score if baseline_match else None,
        "candidate_result_type": candidate_match.result_type if candidate_match else None,
        "baseline_result_type": baseline_match.result_type if baseline_match else None,
        "candidate_label": _run_label(candidate_match),
        "baseline_label": _run_label(baseline_match),
        "details_json": {
            "evaluation_kind": "retrieval",
            "candidate_top_results": _top_result_details(candidate_results),
            "baseline_top_results": _top_result_details(baseline_results),
            "delta_kind": delta_kind,
            "expected_source_filename": case.expected_source_filename,
            "expected_top_result_source_filename": case.expected_top_result_source_filename,
            "minimum_top_n_hits_from_expected_document": (
                case.minimum_top_n_hits_from_expected_document
            ),
            "maximum_foreign_results_before_first_expected_hit": (
                case.maximum_foreign_results_before_first_expected_hit
            ),
            "candidate_result_count": len(candidate_results),
            "baseline_result_count": len(baseline_results),
            "candidate_zero_results": not candidate_results,
            "baseline_zero_results": not baseline_results,
            "candidate_reciprocal_rank": _reciprocal_rank(candidate_rank),
            "baseline_reciprocal_rank": _reciprocal_rank(baseline_rank),
            "candidate_expected_hits_in_top_1": candidate_expected_hits_top_1,
            "candidate_expected_hits_in_top_3": candidate_expected_hits_top_3,
            "candidate_expected_hits_in_top_5": candidate_expected_hits_top_5,
            "baseline_expected_hits_in_top_1": baseline_expected_hits_top_1,
            "baseline_expected_hits_in_top_3": baseline_expected_hits_top_3,
            "baseline_expected_hits_in_top_5": baseline_expected_hits_top_5,
            "candidate_top_result_source_filename": candidate_top_result_source,
            "baseline_top_result_source_filename": baseline_top_result_source,
            "candidate_foreign_top_result": candidate_foreign_top_result,
            "baseline_foreign_top_result": baseline_foreign_top_result,
            "candidate_expected_source_hit_count": candidate_source_hit_count,
            "baseline_expected_source_hit_count": baseline_source_hit_count,
            "candidate_foreign_results_before_first_expected_hit": (
                candidate_foreign_before_first_hit
            ),
            "baseline_foreign_results_before_first_expected_hit": (
                baseline_foreign_before_first_hit
            ),
            "candidate_failure_kind": candidate_failure_kind,
            "baseline_failure_kind": baseline_failure_kind,
        },
        "delta_kind": delta_kind,
    }


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
    candidate_response = answer_question(
        session,
        request,
        run_id=run_id if case.include_document_filter else None,
        origin="evaluation_answer_candidate",
        evaluation_id=evaluation_id,
        persist=False,
    )
    baseline_response = (
        answer_question(
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
        missing_substrings = _missing_answer_substrings(
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
    delta_kind = _classify_delta(candidate_passed, baseline_passed, None)
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
        "candidate_label": _answer_excerpt(candidate_response.answer),
        "baseline_label": _answer_excerpt(baseline_response.answer)
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


def _summarize_structural_checks(
    tables: list[object], figures: list[object], thresholds: EvaluationThresholds
) -> dict:
    checks: list[dict] = []

    actual_table_count = len(tables)
    if thresholds.expected_logical_table_count is not None:
        passed = (
            abs(actual_table_count - thresholds.expected_logical_table_count)
            <= thresholds.logical_table_tolerance
        )
        checks.append(
            {
                "name": "logical_table_count",
                "passed": passed,
                "expected": thresholds.expected_logical_table_count,
                "actual": actual_table_count,
                "tolerance": thresholds.logical_table_tolerance,
            }
        )

    actual_figure_count = len(figures)
    if thresholds.expected_figure_count is not None:
        passed = (
            abs(actual_figure_count - thresholds.expected_figure_count)
            <= thresholds.figure_count_tolerance
        )
        checks.append(
            {
                "name": "figure_count",
                "passed": passed,
                "expected": thresholds.expected_figure_count,
                "actual": actual_figure_count,
                "tolerance": thresholds.figure_count_tolerance,
            }
        )

    captioned_figure_count = sum(1 for figure in figures if getattr(figure, "caption", None))
    if thresholds.minimum_captioned_figure_count is not None:
        checks.append(
            {
                "name": "minimum_captioned_figure_count",
                "passed": captioned_figure_count >= thresholds.minimum_captioned_figure_count,
                "expected_minimum": thresholds.minimum_captioned_figure_count,
                "actual": captioned_figure_count,
            }
        )

    figures_with_provenance = sum(
        1 for figure in figures if (_metadata_for_row(figure).get("provenance") or [])
    )
    if thresholds.minimum_figures_with_provenance is not None:
        checks.append(
            {
                "name": "minimum_figures_with_provenance",
                "passed": figures_with_provenance >= thresholds.minimum_figures_with_provenance,
                "expected_minimum": thresholds.minimum_figures_with_provenance,
                "actual": figures_with_provenance,
            }
        )

    figures_with_artifacts = sum(
        1
        for figure in figures
        if path_exists(getattr(figure, "json_path", None))
        and path_exists(getattr(figure, "yaml_path", None))
    )
    if thresholds.minimum_figures_with_artifacts is not None:
        checks.append(
            {
                "name": "minimum_figures_with_artifacts",
                "passed": figures_with_artifacts >= thresholds.minimum_figures_with_artifacts,
                "expected_minimum": thresholds.minimum_figures_with_artifacts,
                "actual": figures_with_artifacts,
            }
        )

    if thresholds.expected_figure_captions_present:
        expected_captions = [
            _normalized_caption_text(expected)
            for expected in thresholds.expected_figure_captions_present
        ]
        available_captions = [
            _normalized_caption_text(getattr(figure, "caption", None)) for figure in figures
        ]
        missing_captions = [
            expected
            for expected in expected_captions
            if not any(expected.lower() in caption.lower() for caption in available_captions)
        ]
        checks.append(
            {
                "name": "expected_figure_captions_present",
                "passed": not missing_captions,
                "expected": expected_captions,
                "missing": missing_captions,
            }
        )

    merged_tables = [table for table in tables if _metadata_for_row(table).get("is_merged")]
    matched_merged_ids: set[object] = set()
    expectation_results: list[dict] = []
    for expectation in thresholds.expected_merged_tables:
        matches = [
            table for table in merged_tables if _table_matches_merge_expectation(table, expectation)
        ]
        matched_merged_ids.update(id(table) for table in matches)
        expectation_results.append(
            {
                "description": expectation.description,
                "passed": bool(matches),
                "match_count": len(matches),
                "matches": [
                    {
                        "label": _table_label(table),
                        "page_from": getattr(table, "page_from", None),
                        "page_to": getattr(table, "page_to", None),
                        "source_segment_count": _source_segment_count(table),
                        "overlay_family_key": _metadata_for_row(table).get("overlay_family_key"),
                    }
                    for table in matches
                ],
            }
        )

    missing_expected_merges = [
        item["description"] for item in expectation_results if not item["passed"]
    ]
    checks.append(
        {
            "name": "expected_merged_tables",
            "passed": len(missing_expected_merges) <= thresholds.maximum_unexpected_splits,
            "expected_count": len(thresholds.expected_merged_tables),
            "actual_matched_count": len(expectation_results) - len(missing_expected_merges),
            "missing": missing_expected_merges,
            "tolerance": thresholds.maximum_unexpected_splits,
            "details": expectation_results,
        }
    )

    unexpected_merged_tables: list[dict] = []
    if thresholds.enforce_unexpected_merged_tables:
        unexpected_merged_tables = [
            {
                "label": _table_label(table),
                "page_from": getattr(table, "page_from", None),
                "page_to": getattr(table, "page_to", None),
                "merge_reason": _metadata_for_row(table).get("merge_reason"),
            }
            for table in merged_tables
            if id(table) not in matched_merged_ids
        ]
    checks.append(
        {
            "name": "unexpected_merged_tables",
            "passed": len(unexpected_merged_tables) <= thresholds.maximum_unexpected_merges,
            "enforced": thresholds.enforce_unexpected_merged_tables,
            "limit": thresholds.maximum_unexpected_merges,
            "actual": len(unexpected_merged_tables),
            "details": unexpected_merged_tables,
            "observed_merged_table_count": len(merged_tables),
        }
    )

    passed_checks = sum(1 for check in checks if check["passed"])
    failed_checks = len(checks) - passed_checks
    return {
        "passed": failed_checks == 0,
        "check_count": len(checks),
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "checks": checks,
    }


def _evaluate_structural_checks(
    session: Session, run: DocumentRun, thresholds: EvaluationThresholds
) -> dict:
    tables = (
        session.execute(
            select(DocumentTable)
            .where(DocumentTable.run_id == run.id)
            .order_by(DocumentTable.table_index)
        )
        .scalars()
        .all()
    )
    figures = (
        session.execute(
            select(DocumentFigure)
            .where(DocumentFigure.run_id == run.id)
            .order_by(DocumentFigure.figure_index)
        )
        .scalars()
        .all()
    )
    return _summarize_structural_checks(tables, figures, thresholds)


def evaluate_run(
    session: Session,
    document: Document,
    run: DocumentRun,
    *,
    baseline_run_id: UUID | None = None,
    corpus_path: Path | None = None,
    corpus_name: str = DEFAULT_CORPUS_NAME,
    refresh_auto_fixture: bool = True,
) -> DocumentRunEvaluation:
    active_corpus_path = corpus_path or _configured_manual_corpus_path() or _auto_corpus_path()
    baseline_run_id = resolve_baseline_run_id(
        run.id,
        document.active_run_id,
        explicit_baseline_run_id=baseline_run_id,
    )
    if baseline_run_id is not None:
        baseline_run = session.get(DocumentRun, baseline_run_id)
        if baseline_run is None:
            raise ValueError(f"Baseline run {baseline_run_id} does not exist.")
        if baseline_run.document_id != document.id:
            raise ValueError("Baseline run must belong to the same document as the candidate run.")

    evaluation = _upsert_evaluation_row(session, run, corpus_name=corpus_name, fixture_name=None)
    now = utcnow()
    fixture = None
    try:
        fixture = fixture_for_document(document, active_corpus_path)
        if fixture is None or (refresh_auto_fixture and fixture.kind == AUTO_FIXTURE_KIND):
            ensure_auto_evaluation_fixture(session, document, run)
            fixture = fixture_for_document(document, active_corpus_path)

        if fixture is None:
            evaluation.fixture_name = None
            evaluation.status = "skipped"
            evaluation.summary_json = {
                "status": "skipped",
                "reason": "No evaluation fixture matches the document identity.",
                "query_count": 0,
                "retrieval_query_count": 0,
                "answer_query_count": 0,
                "passed_queries": 0,
                "failed_queries": 0,
                "passed_retrieval_queries": 0,
                "failed_retrieval_queries": 0,
                "passed_answer_queries": 0,
                "failed_answer_queries": 0,
                "regressed_queries": 0,
                "improved_queries": 0,
                "stable_queries": 0,
                "retrieval_rank_metrics": _empty_retrieval_rank_metrics(),
                "baseline_run_id": str(baseline_run_id) if baseline_run_id else None,
            }
            evaluation.completed_at = now
            session.commit()
            return evaluation

        evaluation.fixture_name = fixture.name
        retrieval_batch = execute_retrieval_queries(
            session,
            document=document,
            run=run,
            evaluation_id=evaluation.id,
            baseline_run_id=baseline_run_id,
            queries=fixture.queries,
            created_at=now,
            search_documents_fn=search_documents,
            evaluate_retrieval_case_fn=_evaluate_retrieval_case,
        )
        answer_batch = execute_answer_queries(
            session,
            document=document,
            run=run,
            evaluation_id=evaluation.id,
            baseline_run_id=baseline_run_id,
            queries=fixture.answer_queries,
            created_at=now,
            evaluate_answer_case_fn=_evaluate_answer_case,
        )
        batch = EvaluationBatchResult().merge(retrieval_batch).merge(answer_batch)
        structural_summary = _evaluate_structural_checks(session, run, fixture.thresholds)
        retrieval_rank_metrics = _summarize_retrieval_rank_metrics(
            retrieval_batch.retrieval_outcomes
        )
        evaluation.status = "completed"
        evaluation.summary_json = build_completed_evaluation_summary(
            fixture_name=fixture.name,
            batch=batch,
            structural_summary=structural_summary,
            retrieval_rank_metrics=retrieval_rank_metrics,
            baseline_run_id=baseline_run_id,
        )
        evaluation.completed_at = now
        session.commit()
        return evaluation
    except Exception as exc:
        session.rollback()
        evaluation = _upsert_evaluation_row(
            session,
            run,
            corpus_name=corpus_name,
            fixture_name=getattr(fixture, "name", None),
        )
        evaluation.status = "failed"
        evaluation.error_message = str(exc)
        evaluation.summary_json = {
            "status": "failed",
            "fixture_name": getattr(fixture, "name", None),
            "reason": str(exc),
            "query_count": 0,
            "retrieval_query_count": 0,
            "answer_query_count": 0,
            "passed_queries": 0,
            "failed_queries": 0,
            "passed_retrieval_queries": 0,
            "failed_retrieval_queries": 0,
            "passed_answer_queries": 0,
            "failed_answer_queries": 0,
            "regressed_queries": 0,
            "improved_queries": 0,
            "stable_queries": 0,
            "retrieval_rank_metrics": _empty_retrieval_rank_metrics(),
            "baseline_run_id": str(baseline_run_id) if baseline_run_id else None,
        }
        evaluation.completed_at = now
        session.commit()
        return evaluation


def _to_evaluation_summary(evaluation: DocumentRunEvaluation) -> EvaluationSummaryResponse:
    summary = evaluation.summary_json or {}
    baseline_run_id = summary.get("baseline_run_id")
    return EvaluationSummaryResponse(
        evaluation_id=evaluation.id,
        run_id=evaluation.run_id,
        corpus_name=evaluation.corpus_name,
        fixture_name=evaluation.fixture_name,
        status=evaluation.status,
        query_count=summary.get("query_count", 0),
        passed_queries=summary.get("passed_queries", 0),
        failed_queries=summary.get("failed_queries", 0),
        regressed_queries=summary.get("regressed_queries", 0),
        improved_queries=summary.get("improved_queries", 0),
        stable_queries=summary.get("stable_queries", 0),
        baseline_run_id=UUID(baseline_run_id) if baseline_run_id else None,
        error_message=evaluation.error_message,
        created_at=evaluation.created_at,
        completed_at=evaluation.completed_at,
    )


def get_latest_evaluation_summary(
    session: Session, run_id: UUID | None
) -> EvaluationSummaryResponse | None:
    if run_id is None:
        return None
    evaluation = (
        session.execute(
            select(DocumentRunEvaluation)
            .where(DocumentRunEvaluation.run_id == run_id)
            .order_by(DocumentRunEvaluation.created_at.desc())
        )
        .scalars()
        .first()
    )
    if evaluation is None:
        return None
    return _to_evaluation_summary(evaluation)


def get_latest_evaluations_by_run_id(
    session: Session,
    run_ids: list[UUID] | set[UUID],
) -> dict[UUID, DocumentRunEvaluation]:
    run_id_list = list(run_ids)
    if not run_id_list:
        return {}

    ranked_evaluations = (
        select(
            DocumentRunEvaluation.id.label("evaluation_id"),
            func.row_number()
            .over(
                partition_by=DocumentRunEvaluation.run_id,
                order_by=DocumentRunEvaluation.created_at.desc(),
            )
            .label("row_number"),
        )
        .where(DocumentRunEvaluation.run_id.in_(run_id_list))
        .subquery()
    )
    evaluation_alias = aliased(DocumentRunEvaluation)
    rows = (
        session.execute(
            select(evaluation_alias)
            .join(ranked_evaluations, ranked_evaluations.c.evaluation_id == evaluation_alias.id)
            .where(ranked_evaluations.c.row_number == 1)
        )
        .scalars()
        .all()
    )
    return {row.run_id: row for row in rows}


def get_latest_evaluation_summaries(
    session: Session,
    run_ids: list[UUID] | set[UUID],
) -> dict[UUID, EvaluationSummaryResponse]:
    return {
        run_id: _to_evaluation_summary(evaluation)
        for run_id, evaluation in get_latest_evaluations_by_run_id(session, run_ids).items()
    }


def get_latest_document_evaluation(
    session: Session, document: Document
) -> EvaluationDetailResponse | None:
    if document.latest_run_id is None:
        return None
    evaluation = (
        session.execute(
            select(DocumentRunEvaluation)
            .where(DocumentRunEvaluation.run_id == document.latest_run_id)
            .order_by(DocumentRunEvaluation.created_at.desc())
        )
        .scalars()
        .first()
    )
    if evaluation is None:
        return None
    query_rows = (
        session.execute(
            select(DocumentRunEvaluationQuery)
            .where(DocumentRunEvaluationQuery.evaluation_id == evaluation.id)
            .order_by(
                DocumentRunEvaluationQuery.created_at.asc(),
                DocumentRunEvaluationQuery.query_text.asc(),
            )
        )
        .scalars()
        .all()
    )
    summary = _to_evaluation_summary(evaluation)
    return EvaluationDetailResponse(
        **summary.model_dump(),
        summary=evaluation.summary_json or {},
        query_results=[
            EvaluationQueryResultResponse(
                query_text=row.query_text,
                mode=row.mode,
                evaluation_kind=(row.details_json or {}).get("evaluation_kind", "retrieval"),
                expected_result_type=row.expected_result_type,
                expected_top_n=row.expected_top_n,
                passed=row.passed,
                candidate_rank=row.candidate_rank,
                baseline_rank=row.baseline_rank,
                rank_delta=row.rank_delta,
                candidate_score=row.candidate_score,
                baseline_score=row.baseline_score,
                candidate_result_type=row.candidate_result_type,
                baseline_result_type=row.baseline_result_type,
                candidate_label=row.candidate_label,
                baseline_label=row.baseline_label,
                details=row.details_json,
            )
            for row in query_rows
        ],
    )
