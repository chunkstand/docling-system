from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    Document,
    DocumentChunk,
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
from app.schemas.search import SearchFilters, SearchRequest, SearchResult
from app.services.chat import answer_question
from app.services.search import search_documents

EVAL_VERSION = 1
DEFAULT_CORPUS_NAME = "default"
DEFAULT_CORPUS_PATH = Path("docs") / "evaluation_corpus.yaml"
AUTO_CORPUS_FILENAME = "evaluation_corpus.auto.yaml"
AUTO_FIXTURE_KIND = "auto_generated_document"
AUTO_QUERY_TOP_N = 3
AUTO_TABLE_QUERY_LIMIT = 2
AUTO_CHUNK_QUERY_LIMIT = 3
AUTO_QUERY_MAX_WORDS = 8
TABLE_PREFIX_PATTERN = re.compile(
    r"^(?:table|figure|appendix)\s+[0-9A-Z().:-]+\s*",
    re.IGNORECASE,
)
AUTO_FIXTURE_NAME_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass
class EvaluationFixture:
    name: str
    path: str
    queries: list[EvaluationQueryCase]
    answer_queries: list[EvaluationAnswerCase]
    thresholds: EvaluationThresholds


@dataclass
class EvaluationQueryCase:
    query: str
    mode: str
    filters: dict
    expected_result_type: str
    expected_top_n: int


@dataclass
class EvaluationAnswerCase:
    question: str
    mode: str
    filters: dict
    expected_answer_contains: list[str]
    minimum_citation_count: int
    allow_fallback: bool
    top_k: int


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


def _auto_corpus_path() -> Path:
    return get_settings().storage_root.resolve() / AUTO_CORPUS_FILENAME


def _load_corpus_documents(path: Path) -> list[dict]:
    if not path.exists():
        return []
    config = yaml.safe_load(path.read_text()) or {}
    documents = config.get("documents") or []
    return [document for document in documents if isinstance(document, dict)]


def _write_corpus_documents(path: Path, documents: list[dict]) -> None:
    settings = get_settings()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "rollout_mode": "auto_generated_append_only",
        "embedding_contract": {
            "model": settings.openai_embedding_model,
            "dimension": settings.embedding_dim,
        },
        "documents": documents,
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False))


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


def _normalize_fixture_answer(entry: dict) -> EvaluationAnswerCase:
    answer_contains = entry.get("answer_contains") or entry.get("expected_answer_contains") or []
    if isinstance(answer_contains, str):
        answer_contains = [answer_contains]
    return EvaluationAnswerCase(
        question=entry.get("question") or entry["query"],
        mode=entry.get("mode", "hybrid"),
        filters=entry.get("filters") or {},
        expected_answer_contains=answer_contains,
        minimum_citation_count=entry.get("minimum_citation_count", 1),
        allow_fallback=bool(entry.get("allow_fallback", False)),
        top_k=entry.get("top_k", 6),
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


def _fixture_paths(corpus_path: Path | None = None) -> list[Path]:
    primary_path = corpus_path or DEFAULT_CORPUS_PATH
    paths = [primary_path]
    auto_path = _auto_corpus_path()
    if auto_path != primary_path and auto_path.exists():
        paths.append(auto_path)
    return paths


def load_evaluation_fixtures(corpus_path: Path | None = None) -> list[EvaluationFixture]:
    fixtures: list[EvaluationFixture] = []
    seen_filenames: set[str] = set()
    for path in _fixture_paths(corpus_path):
        for document in _load_corpus_documents(path):
            doc_path = document.get("path")
            if not doc_path:
                continue
            source_filename = Path(doc_path).name
            if source_filename in seen_filenames:
                continue
            seen_filenames.add(source_filename)
            thresholds = document.get("thresholds", {})
            queries: list[EvaluationQueryCase] = []
            answer_queries: list[EvaluationAnswerCase] = []
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
            for entry in thresholds.get("expected_answer_queries", []):
                answer_queries.append(_normalize_fixture_answer(entry))
            fixtures.append(
                EvaluationFixture(
                    name=document["name"],
                    path=doc_path,
                    queries=queries,
                    answer_queries=answer_queries,
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


def _collapse_whitespace(value: str | None) -> str:
    return " ".join((value or "").split()).strip()


def _first_sentence(value: str | None) -> str:
    collapsed = _collapse_whitespace(value)
    if not collapsed:
        return ""
    return re.split(r"(?<=[.!?])\s+", collapsed, maxsplit=1)[0]


def _normalize_query_candidate(
    value: str | None,
    *,
    strip_table_prefix: bool = False,
    max_words: int = AUTO_QUERY_MAX_WORDS,
) -> str | None:
    text = _collapse_whitespace(value)
    if not text:
        return None
    if strip_table_prefix:
        text = TABLE_PREFIX_PATTERN.sub("", text)
    text = text.strip(" .,:;|-")
    words = text.split()
    if len(words) < 2:
        return None
    if "@" in text:
        return None
    alphabetic_words = [word for word in words if re.search(r"[A-Za-z]", word)]
    if len(alphabetic_words) < 2:
        return None
    if text.upper() == text and len(words) <= 4:
        return None
    if len(words) > max_words:
        text = " ".join(words[:max_words])
    return text.strip(" .,:;|-") or None


def _auto_fixture_name(source_filename: str) -> str:
    stem = Path(source_filename).stem.lower()
    slug = AUTO_FIXTURE_NAME_PATTERN.sub("_", stem).strip("_")
    return f"auto_{slug or 'document'}"


def _auto_table_query(table: object) -> str | None:
    for candidate in (
        getattr(table, "title", None),
        getattr(table, "heading", None),
        _first_sentence(getattr(table, "preview_text", None)),
        _first_sentence(getattr(table, "search_text", None)),
    ):
        if query := _normalize_query_candidate(candidate, strip_table_prefix=True):
            return query
    return None


def _auto_chunk_queries(title: str | None, source_filename: str, chunks: list[object]) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()
    candidates: list[str | None] = [title, Path(source_filename).stem.replace("_", " ")]
    for chunk in chunks[:24]:
        candidates.extend(
            [
                getattr(chunk, "heading", None),
                _first_sentence(getattr(chunk, "text", None)),
            ]
        )
    for candidate in candidates:
        query = _normalize_query_candidate(candidate)
        if query is None:
            continue
        key = query.lower()
        if key in seen:
            continue
        seen.add(key)
        queries.append(query)
        if len(queries) >= AUTO_CHUNK_QUERY_LIMIT:
            break
    return queries


def _figure_provenance_count(figures: list[object]) -> int:
    count = 0
    for figure in figures:
        metadata = _metadata_for_row(figure)
        if metadata.get("provenance"):
            count += 1
    return count


def _figure_artifact_count(figures: list[object]) -> int:
    return sum(
        int(bool(getattr(figure, "json_path", None) and getattr(figure, "yaml_path", None)))
        for figure in figures
    )


def build_auto_evaluation_fixture_document(
    source_filename: str,
    *,
    title: str | None,
    chunks: list[object],
    tables: list[object],
    figures: list[object],
    run_id: UUID | None = None,
) -> dict:
    table_queries: list[dict[str, object]] = []
    used_queries: set[str] = set()
    for table in tables:
        query = _auto_table_query(table)
        if query is None or query.lower() in used_queries:
            continue
        used_queries.add(query.lower())
        table_queries.append({"query": query, "top_n": AUTO_QUERY_TOP_N, "mode": "hybrid"})
        if len(table_queries) >= AUTO_TABLE_QUERY_LIMIT:
            break

    chunk_queries: list[dict[str, object]] = []
    for query in _auto_chunk_queries(title, source_filename, chunks):
        if query.lower() in used_queries:
            continue
        used_queries.add(query.lower())
        chunk_queries.append({"query": query, "top_n": AUTO_QUERY_TOP_N, "mode": "hybrid"})
        if len(chunk_queries) >= AUTO_CHUNK_QUERY_LIMIT:
            break

    if not chunk_queries:
        fallback = _normalize_query_candidate(Path(source_filename).stem.replace("_", " "))
        if fallback:
            chunk_queries.append({"query": fallback, "top_n": AUTO_QUERY_TOP_N, "mode": "hybrid"})

    thresholds: dict[str, object] = {
        "expected_logical_table_count": len(tables),
        "logical_table_tolerance": 0,
        "expected_figure_count": len(figures),
        "figure_count_tolerance": 0,
        "maximum_unexpected_merges": 0,
        "maximum_unexpected_splits": 0,
    }

    captioned_figure_count = sum(
        int(bool(_normalized_caption_text(getattr(figure, "caption", None)))) for figure in figures
    )
    if captioned_figure_count:
        thresholds["minimum_captioned_figure_count"] = captioned_figure_count
    figures_with_provenance = _figure_provenance_count(figures)
    if figures_with_provenance:
        thresholds["minimum_figures_with_provenance"] = figures_with_provenance
    figures_with_artifacts = _figure_artifact_count(figures)
    if figures_with_artifacts:
        thresholds["minimum_figures_with_artifacts"] = figures_with_artifacts
    if table_queries:
        thresholds["expected_top_n_table_hit_queries"] = table_queries
    if chunk_queries:
        thresholds["expected_top_n_chunk_hit_queries"] = chunk_queries

    return {
        "name": _auto_fixture_name(source_filename),
        "kind": AUTO_FIXTURE_KIND,
        "path": source_filename,
        "autogenerated": True,
        "generated_from_run_id": str(run_id) if run_id else None,
        "thresholds": thresholds,
    }


def ensure_auto_evaluation_fixture(
    session: Session,
    document: Document,
    run: DocumentRun,
    *,
    title: str | None = None,
) -> dict:
    tables = (
        session.execute(
            select(DocumentTable)
            .where(DocumentTable.document_id == document.id, DocumentTable.run_id == run.id)
            .order_by(DocumentTable.table_index.asc())
        )
        .scalars()
        .all()
    )
    figures = (
        session.execute(
            select(DocumentFigure)
            .where(DocumentFigure.document_id == document.id, DocumentFigure.run_id == run.id)
            .order_by(DocumentFigure.figure_index.asc())
        )
        .scalars()
        .all()
    )
    chunks = (
        session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document.id, DocumentChunk.run_id == run.id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        .scalars()
        .all()
    )

    fixture_document = build_auto_evaluation_fixture_document(
        document.source_filename,
        title=title or getattr(document, "title", None),
        chunks=chunks,
        tables=tables,
        figures=figures,
        run_id=run.id,
    )
    path = _auto_corpus_path()
    documents = [
        entry
        for entry in _load_corpus_documents(path)
        if Path(entry.get("path", "")).name != document.source_filename
    ]
    documents.append(fixture_document)
    documents.sort(key=lambda entry: Path(entry.get("path", "")).name.lower())
    _write_corpus_documents(path, documents)
    return fixture_document


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
    if (
        expectation.page_from is not None
        and getattr(table, "page_from", None) != expectation.page_from
    ):
        return False
    if (
        expectation.page_to is not None
        and getattr(table, "page_to", None) != expectation.page_to
    ):
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


def _answer_excerpt(answer_text: str, limit: int = 180) -> str:
    normalized = " ".join(answer_text.split()).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


def _missing_answer_substrings(answer_text: str, expected_substrings: list[str]) -> list[str]:
    normalized_answer = answer_text.lower()
    return [
        substring
        for substring in expected_substrings
        if substring.lower() not in normalized_answer
    ]


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
        document_id=document.id,
        top_k=case.top_k,
    )
    candidate_response = answer_question(
        session,
        request,
        run_id=run_id,
        origin="evaluation_answer_candidate",
        evaluation_id=evaluation_id,
        persist=False,
    )
    baseline_response = (
        answer_question(
            session,
            request,
            run_id=baseline_run_id,
            origin="evaluation_answer_baseline",
            evaluation_id=evaluation_id,
            persist=False,
        )
        if baseline_run_id
        else None
    )

    def _answer_passed(response: ChatResponse | None) -> tuple[bool, list[str], int]:
        if response is None:
            return False, case.expected_answer_contains, 0
        missing_substrings = _missing_answer_substrings(
            response.answer, case.expected_answer_contains
        )
        citation_count = len(response.citations)
        passed = (
            not missing_substrings
            and citation_count >= case.minimum_citation_count
            and (case.allow_fallback or not response.used_fallback)
        )
        return passed, missing_substrings, citation_count

    candidate_passed, candidate_missing_substrings, candidate_citation_count = _answer_passed(
        candidate_response
    )
    baseline_passed, baseline_missing_substrings, baseline_citation_count = _answer_passed(
        baseline_response
    )
    delta_kind = _classify_delta(candidate_passed, baseline_passed, None)
    filters_payload = {**case.filters, "document_id": str(document.id)}

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
            "candidate_missing_substrings": candidate_missing_substrings,
            "candidate_citation_count": candidate_citation_count,
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
        matches = [
            table
            for table in merged_tables
            if _table_matches_merge_expectation(table, expectation)
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
    if fixture is None:
        ensure_auto_evaluation_fixture(session, document, run)
        fixture = fixture_for_document(document, corpus_path)
    now = _utcnow()
    if fixture is None:
        evaluation.fixture_name = None
        evaluation.status = "skipped"
        evaluation.summary_json = {
            "status": "skipped",
            "reason": "No evaluation fixture matches the document source filename.",
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
            "baseline_run_id": str(baseline_run_id) if baseline_run_id else None,
        }
        evaluation.completed_at = now
        session.commit()
        return evaluation

    evaluation.fixture_name = fixture.name
    try:
        query_count = 0
        retrieval_query_count = 0
        answer_query_count = 0
        passed_queries = 0
        failed_queries = 0
        passed_retrieval_queries = 0
        failed_retrieval_queries = 0
        passed_answer_queries = 0
        failed_answer_queries = 0
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

            candidate_results = search_documents(
                session,
                request,
                run_id=run.id,
                origin="evaluation_candidate",
                evaluation_id=evaluation.id,
            )
            baseline_results = (
                search_documents(
                    session,
                    request,
                    run_id=baseline_run_id,
                    origin="evaluation_baseline",
                    evaluation_id=evaluation.id,
                )
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
            retrieval_query_count += 1
            passed_queries += int(candidate_passed)
            failed_queries += int(not candidate_passed)
            passed_retrieval_queries += int(candidate_passed)
            failed_retrieval_queries += int(not candidate_passed)
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
                        "evaluation_kind": "retrieval",
                        "candidate_top_results": _top_result_details(candidate_results),
                        "baseline_top_results": _top_result_details(baseline_results),
                        "delta_kind": delta_kind,
                    },
                    created_at=now,
                )
            )

        for case in fixture.answer_queries:
            outcome = _evaluate_answer_case(
                session,
                document=document,
                run_id=run.id,
                baseline_run_id=baseline_run_id,
                evaluation_id=evaluation.id,
                case=case,
            )
            query_count += 1
            answer_query_count += 1
            passed_queries += int(outcome["passed"])
            failed_queries += int(not outcome["passed"])
            passed_answer_queries += int(outcome["passed"])
            failed_answer_queries += int(not outcome["passed"])
            regressed_queries += int(outcome["delta_kind"] == "regressed")
            improved_queries += int(outcome["delta_kind"] == "improved")
            stable_queries += int(outcome["delta_kind"] == "stable")

            session.add(
                DocumentRunEvaluationQuery(
                    evaluation_id=evaluation.id,
                    query_text=outcome["query_text"],
                    mode=outcome["mode"],
                    filters_json=outcome["filters_json"],
                    expected_result_type=outcome["expected_result_type"],
                    expected_top_n=outcome["expected_top_n"],
                    passed=outcome["passed"],
                    candidate_rank=outcome["candidate_rank"],
                    baseline_rank=outcome["baseline_rank"],
                    rank_delta=outcome["rank_delta"],
                    candidate_score=outcome["candidate_score"],
                    baseline_score=outcome["baseline_score"],
                    candidate_result_type=outcome["candidate_result_type"],
                    baseline_result_type=outcome["baseline_result_type"],
                    candidate_label=outcome["candidate_label"],
                    baseline_label=outcome["baseline_label"],
                    details_json=outcome["details_json"],
                    created_at=now,
                )
            )

        structural_summary = _evaluate_structural_checks(session, run, fixture.thresholds)
        evaluation.status = "completed"
        evaluation.summary_json = {
            "status": "completed",
            "fixture_name": fixture.name,
            "query_count": query_count,
            "retrieval_query_count": retrieval_query_count,
            "answer_query_count": answer_query_count,
            "passed_queries": passed_queries,
            "failed_queries": failed_queries,
            "passed_retrieval_queries": passed_retrieval_queries,
            "failed_retrieval_queries": failed_retrieval_queries,
            "passed_answer_queries": passed_answer_queries,
            "failed_answer_queries": failed_answer_queries,
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
