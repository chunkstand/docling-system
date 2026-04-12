from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Document,
    DocumentFigure,
    DocumentRun,
    DocumentRunEvaluation,
    DocumentRunEvaluationQuery,
    DocumentTable,
)
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
    queries: list[EvaluationQueryCase]
    thresholds: EvaluationThresholds


@dataclass
class EvaluationQueryCase:
    query: str
    mode: str
    filters: dict
    expected_result_type: str
    expected_top_n: int


@dataclass
class EvaluationMergeExpectation:
    description: str
    title_contains: str | None = None
    heading_contains: str | None = None
    page_from: int | None = None
    page_to: int | None = None
    minimum_source_segment_count: int = 2
    overlay_applied: bool | None = None
    overlay_family_key: str | None = None


@dataclass
class EvaluationThresholds:
    expected_logical_table_count: int | None = None
    logical_table_tolerance: int = 0
    expected_figure_count: int | None = None
    figure_count_tolerance: int = 0
    minimum_captioned_figure_count: int | None = None
    minimum_figures_with_provenance: int | None = None
    minimum_figures_with_artifacts: int | None = None
    expected_figure_captions_present: list[str] = field(default_factory=list)
    maximum_unexpected_merges: int = 0
    maximum_unexpected_splits: int = 0
    expected_merged_tables: list[EvaluationMergeExpectation] = field(default_factory=list)
    enforce_unexpected_merged_tables: bool = False


def _utcnow() -> datetime:
    return datetime.now(UTC)


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


def _normalize_thresholds(thresholds: dict) -> EvaluationThresholds:
    expectations = [
        EvaluationMergeExpectation(
            description=entry.get("description")
            or entry.get("title_contains")
            or entry.get("overlay_family_key")
            or "expected_merged_table",
            title_contains=entry.get("title_contains"),
            heading_contains=entry.get("heading_contains"),
            page_from=entry.get("page_from"),
            page_to=entry.get("page_to"),
            minimum_source_segment_count=entry.get("minimum_source_segment_count", 2),
            overlay_applied=entry.get("overlay_applied"),
            overlay_family_key=entry.get("overlay_family_key"),
        )
        for entry in thresholds.get("expected_merged_tables", [])
    ]
    return EvaluationThresholds(
        expected_logical_table_count=thresholds.get("expected_logical_table_count"),
        logical_table_tolerance=thresholds.get("logical_table_tolerance", 0),
        expected_figure_count=thresholds.get("expected_figure_count"),
        figure_count_tolerance=thresholds.get("figure_count_tolerance", 0),
        minimum_captioned_figure_count=thresholds.get("minimum_captioned_figure_count"),
        minimum_figures_with_provenance=thresholds.get("minimum_figures_with_provenance"),
        minimum_figures_with_artifacts=thresholds.get("minimum_figures_with_artifacts"),
        expected_figure_captions_present=thresholds.get("expected_figure_captions_present") or [],
        maximum_unexpected_merges=thresholds.get("maximum_unexpected_merges", 0),
        maximum_unexpected_splits=thresholds.get("maximum_unexpected_splits", 0),
        expected_merged_tables=expectations,
        enforce_unexpected_merged_tables=thresholds.get("enforce_unexpected_merged_tables", False),
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
        fixtures.append(
            EvaluationFixture(
                name=document["name"],
                path=doc_path,
                queries=queries,
                thresholds=_normalize_thresholds(thresholds),
            )
        )
    return fixtures


def fixture_for_document(
    document: Document, corpus_path: Path | None = None
) -> EvaluationFixture | None:
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


def _metadata_for_row(row: object) -> dict:
    return getattr(row, "metadata_json", None) or getattr(row, "metadata", None) or {}


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


def _normalized_caption_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "caption", "value", "label"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
        return ""
    return str(value)


def _table_matches_merge_expectation(
    table: object, expectation: EvaluationMergeExpectation
) -> bool:
    metadata = _metadata_for_row(table)
    if not _text_contains(getattr(table, "title", None), expectation.title_contains):
        return False
    if not _text_contains(getattr(table, "heading", None), expectation.heading_contains):
        return False
    if expectation.page_from is not None and getattr(table, "page_from", None) != expectation.page_from:
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


def _artifact_present(path_value: str | None) -> bool:
    return bool(path_value and Path(path_value).exists())


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
        if _artifact_present(getattr(figure, "json_path", None))
        and _artifact_present(getattr(figure, "yaml_path", None))
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
        matches = [table for table in merged_tables if _table_matches_merge_expectation(table, expectation)]
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

    missing_expected_merges = [item["description"] for item in expectation_results if not item["passed"]]
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
) -> DocumentRunEvaluation:
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
            request = SearchRequest(
                query=case.query,
                mode=case.mode,
                filters=filters,
                limit=max(case.expected_top_n, 10),
            )

            candidate_results = search_documents(session, request, run_id=run.id)
            baseline_results = (
                search_documents(session, request, run_id=baseline_run_id)
                if baseline_run_id
                else []
            )

            candidate_rank = _matching_rank(candidate_results, case.expected_result_type)
            baseline_rank = _matching_rank(baseline_results, case.expected_result_type)
            candidate_passed = candidate_rank is not None and candidate_rank <= case.expected_top_n
            baseline_passed = baseline_rank is not None and baseline_rank <= case.expected_top_n
            delta_kind = _classify_delta(
                candidate_passed, baseline_passed, _rank_delta(candidate_rank, baseline_rank)
            )

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

        structural_summary = _evaluate_structural_checks(session, run, fixture.thresholds)
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
            "structural_check_count": structural_summary["check_count"],
            "passed_structural_checks": structural_summary["passed_checks"],
            "failed_structural_checks": structural_summary["failed_checks"],
            "structural_passed": structural_summary["passed"],
            "structural_checks": structural_summary["checks"],
            "baseline_run_id": str(baseline_run_id) if baseline_run_id else None,
        }
        evaluation.completed_at = now
        session.commit()
        return evaluation
    except Exception as exc:
        session.rollback()
        evaluation = _upsert_evaluation_row(
            session, run, corpus_name=corpus_name, fixture_name=fixture.name
        )
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
            .order_by(DocumentRunEvaluationQuery.query_text.asc())
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
