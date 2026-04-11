from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
import uuid

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentRun, DocumentRunEvaluation, DocumentRunEvaluationQuery
from app.schemas.evaluations import (
    EvaluationDetailResponse,
    EvaluationQueryResultResponse,
    EvaluationSummaryResponse,
)
from app.schemas.search import SearchFilters, SearchRequest, SearchResult
from app.services.search import search_documents


EVAL_VERSION = 1
DEFAULT_CORPUS_NAME = "default"
DEFAULT_CORPUS_PATH = Path("docs") / "evaluation_corpus.yaml"


@dataclass
class EvaluationFixture:
    name: str
    path: str
    queries: list["EvaluationQueryCase"]


@dataclass
class EvaluationQueryCase:
    query: str
    mode: str
    filters: dict
    expected_result_type: str
    expected_top_n: int


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
        }
        for idx, result in enumerate(results[:limit], start=1)
    ]


def _matching_rank(results: list[SearchResult], expected_result_type: str) -> int | None:
    for idx, result in enumerate(results, start=1):
        if result.result_type == expected_result_type:
            return idx
    return None


def _result_at_rank(results: list[SearchResult], rank: int | None) -> SearchResult | None:
    if rank is None or rank <= 0 or rank > len(results):
        return None
    return results[rank - 1]


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


def _normalize_fixture_query(entry: dict, expected_result_type: str) -> EvaluationQueryCase:
    return EvaluationQueryCase(
        query=entry["query"],
        mode=entry.get("mode", "hybrid"),
        filters=entry.get("filters") or {},
        expected_result_type=entry.get("expected_result_type", expected_result_type),
        expected_top_n=entry.get("top_n", 3),
    )


def load_evaluation_fixtures(corpus_path: Path | None = None) -> list[EvaluationFixture]:
    path = corpus_path or DEFAULT_CORPUS_PATH
    config = yaml.safe_load(path.read_text()) or {}
    fixtures: list[EvaluationFixture] = []
    for document in config.get("documents", []):
        doc_path = document.get("path")
        if not doc_path:
            continue
        thresholds = document.get("thresholds", {})
        queries: list[EvaluationQueryCase] = []
        for entry in thresholds.get("expected_top_n_table_hit_queries", []):
            queries.append(_normalize_fixture_query(entry, "table"))
        for entry in thresholds.get("expected_top_n_chunk_hit_queries", []):
            queries.append(_normalize_fixture_query(entry, "chunk"))
        for entry in thresholds.get("queries", []):
            queries.append(
                EvaluationQueryCase(
                    query=entry["query"],
                    mode=entry.get("mode", "hybrid"),
                    filters=entry.get("filters") or {},
                    expected_result_type=entry["expected_result_type"],
                    expected_top_n=entry.get("top_n", 3),
                )
            )
        fixtures.append(EvaluationFixture(name=document["name"], path=doc_path, queries=queries))
    return fixtures


def fixture_for_document(document: Document, corpus_path: Path | None = None) -> EvaluationFixture | None:
    for fixture in load_evaluation_fixtures(corpus_path):
        if Path(fixture.path).name == document.source_filename:
            return fixture
    return None


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
        created_at=_utcnow(),
    )
    session.add(evaluation)
    session.flush()
    return evaluation


def evaluate_run(
    session: Session,
    document: Document,
    run: DocumentRun,
    *,
    baseline_run_id: UUID | None = None,
    corpus_path: Path | None = None,
    corpus_name: str = DEFAULT_CORPUS_NAME,
) -> DocumentRunEvaluation:
    evaluation = _upsert_evaluation_row(session, run, corpus_name=corpus_name, fixture_name=None)
    fixture = fixture_for_document(document, corpus_path)
    now = _utcnow()
    if fixture is None:
        evaluation.fixture_name = None
        evaluation.status = "skipped"
        evaluation.summary_json = {
            "status": "skipped",
            "reason": "No evaluation fixture matches the document source filename.",
            "query_count": 0,
            "passed_queries": 0,
            "failed_queries": 0,
            "regressed_queries": 0,
            "improved_queries": 0,
            "stable_queries": 0,
            "baseline_run_id": str(baseline_run_id) if baseline_run_id else None,
        }
        evaluation.completed_at = now
        session.commit()
        return evaluation

    evaluation.fixture_name = fixture.name
    try:
        query_count = 0
        passed_queries = 0
        failed_queries = 0
        regressed_queries = 0
        improved_queries = 0
        stable_queries = 0

        for case in fixture.queries:
            filters_payload = {**case.filters, "document_id": str(document.id)}
            filters = SearchFilters.model_validate(filters_payload)
            request = SearchRequest(query=case.query, mode=case.mode, filters=filters, limit=max(case.expected_top_n, 10))

            candidate_results = search_documents(session, request, run_id=run.id)
            baseline_results = search_documents(session, request, run_id=baseline_run_id) if baseline_run_id else []

            candidate_rank = _matching_rank(candidate_results, case.expected_result_type)
            baseline_rank = _matching_rank(baseline_results, case.expected_result_type)
            candidate_passed = candidate_rank is not None and candidate_rank <= case.expected_top_n
            baseline_passed = baseline_rank is not None and baseline_rank <= case.expected_top_n
            delta_kind = _classify_delta(candidate_passed, baseline_passed, _rank_delta(candidate_rank, baseline_rank))

            query_count += 1
            passed_queries += int(candidate_passed)
            failed_queries += int(not candidate_passed)
            regressed_queries += int(delta_kind == "regressed")
            improved_queries += int(delta_kind == "improved")
            stable_queries += int(delta_kind == "stable")

            candidate_match = _result_at_rank(candidate_results, candidate_rank)
            baseline_match = _result_at_rank(baseline_results, baseline_rank)
            session.add(
                DocumentRunEvaluationQuery(
                    evaluation_id=evaluation.id,
                    query_text=case.query,
                    mode=case.mode,
                    filters_json=filters.model_dump(mode="json", exclude_none=True),
                    expected_result_type=case.expected_result_type,
                    expected_top_n=case.expected_top_n,
                    passed=candidate_passed,
                    candidate_rank=candidate_rank,
                    baseline_rank=baseline_rank,
                    rank_delta=_rank_delta(candidate_rank, baseline_rank),
                    candidate_score=candidate_match.score if candidate_match else None,
                    baseline_score=baseline_match.score if baseline_match else None,
                    candidate_result_type=candidate_match.result_type if candidate_match else None,
                    baseline_result_type=baseline_match.result_type if baseline_match else None,
                    candidate_label=_run_label(candidate_match),
                    baseline_label=_run_label(baseline_match),
                    details_json={
                        "candidate_top_results": _top_result_details(candidate_results),
                        "baseline_top_results": _top_result_details(baseline_results),
                        "delta_kind": delta_kind,
                    },
                    created_at=now,
                )
            )

        evaluation.status = "completed"
        evaluation.summary_json = {
            "status": "completed",
            "fixture_name": fixture.name,
            "query_count": query_count,
            "passed_queries": passed_queries,
            "failed_queries": failed_queries,
            "regressed_queries": regressed_queries,
            "improved_queries": improved_queries,
            "stable_queries": stable_queries,
            "baseline_run_id": str(baseline_run_id) if baseline_run_id else None,
        }
        evaluation.completed_at = now
        session.commit()
        return evaluation
    except Exception as exc:
        session.rollback()
        evaluation = _upsert_evaluation_row(session, run, corpus_name=corpus_name, fixture_name=fixture.name)
        evaluation.status = "failed"
        evaluation.error_message = str(exc)
        evaluation.summary_json = {
            "status": "failed",
            "fixture_name": fixture.name,
            "reason": str(exc),
            "query_count": 0,
            "passed_queries": 0,
            "failed_queries": 0,
            "regressed_queries": 0,
            "improved_queries": 0,
            "stable_queries": 0,
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


def get_latest_evaluation_summary(session: Session, run_id: UUID | None) -> EvaluationSummaryResponse | None:
    if run_id is None:
        return None
    evaluation = session.execute(
        select(DocumentRunEvaluation)
        .where(DocumentRunEvaluation.run_id == run_id)
        .order_by(DocumentRunEvaluation.created_at.desc())
    ).scalars().first()
    if evaluation is None:
        return None
    return _to_evaluation_summary(evaluation)


def get_latest_document_evaluation(session: Session, document: Document) -> EvaluationDetailResponse | None:
    if document.latest_run_id is None:
        return None
    evaluation = session.execute(
        select(DocumentRunEvaluation)
        .where(DocumentRunEvaluation.run_id == document.latest_run_id)
        .order_by(DocumentRunEvaluation.created_at.desc())
    ).scalars().first()
    if evaluation is None:
        return None
    query_rows = session.execute(
        select(DocumentRunEvaluationQuery)
        .where(DocumentRunEvaluationQuery.evaluation_id == evaluation.id)
        .order_by(DocumentRunEvaluationQuery.query_text.asc())
    ).scalars().all()
    summary = _to_evaluation_summary(evaluation)
    return EvaluationDetailResponse(
        **summary.model_dump(),
        summary=evaluation.summary_json or {},
        query_results=[
            EvaluationQueryResultResponse(
                query_text=row.query_text,
                mode=row.mode,
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
