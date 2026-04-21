from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.core.config import get_settings
from app.core.files import path_exists, source_filename_matches
from app.core.text import collapse_whitespace
from app.core.time import utcnow
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
from app.services.evaluation_execution import (
    EvaluationBatchResult,
    build_completed_evaluation_summary,
    execute_answer_queries,
    execute_retrieval_queries,
)
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
SECTION_HEADING_QUERY_PATTERN = re.compile(r"^\d+(?:\.\d+)*\s+")
TABLE_PREFIX_PATTERN = re.compile(
    r"^(?:table|figure|appendix)\s+[0-9A-Z().:-]+\s*",
    re.IGNORECASE,
)
LOW_SIGNAL_CHUNK_QUERY_PATTERNS = (
    re.compile(r"^untitled\s+document\b", re.IGNORECASE),
    re.compile(r"^draft\s+for\s+publication\b", re.IGNORECASE),
    re.compile(r"^>{2,}\s*message from\b", re.IGNORECASE),
    re.compile(r"^(?:ceo\s+)?document contents:?$", re.IGNORECASE),
    re.compile(r"^prepared\s+(?:for|by)\b", re.IGNORECASE),
    re.compile(r"^project report\b(?:\s*[:.-].*)?$", re.IGNORECASE),
    re.compile(r"^(?:table\s+of\s+)?contents\b", re.IGNORECASE),
    re.compile(r"^recommended\s+citation\b", re.IGNORECASE),
    re.compile(r"^citation:", re.IGNORECASE),
    re.compile(r"^for\s+submittal\s+to\b", re.IGNORECASE),
    re.compile(r"^\d+(?:\.\d+)*\s+alternative\s+\d+\b", re.IGNORECASE),
    re.compile(r"^\d{4}\s+[A-Za-z]+\s+\d{4}\s+[A-Za-z]+$", re.IGNORECASE),
    re.compile(r"^[A-Z][a-z]+\s+[A-Z]\.?$", re.IGNORECASE),
    re.compile(
        r"^list\s+of\s+(?:figures(?:\s+and\s+exhibits)?|tables|acronyms(?:\s+and\s+abbreviations)?|maps)\b",
        re.IGNORECASE,
    ),
    re.compile(r"^(?:figure|exhibit)\s+\d+[A-Z0-9().:-]*\b", re.IGNORECASE),
    re.compile(
        r"^[A-Za-z][A-Za-z0-9/%&+().:'-]*(?:\s+[A-Za-z0-9/%&+().:'-]+){0,4}\s*[><=].*[\"']?$",
        re.IGNORECASE,
    ),
    re.compile(r"^[A-Za-z0-9'/-]+(?:\s+[A-Za-z0-9'/-]+){0,3}\s+project\b", re.IGNORECASE),
    re.compile(r".*\bdoi:\s*\S+", re.IGNORECASE),
    re.compile(r".*\b(?:research paper|experiment station)\b.*", re.IGNORECASE),
)
LOW_SIGNAL_TABLE_QUERY_PATTERNS = (
    re.compile(r"^chapter\s+[ivxlcdm0-9a-z]+\b", re.IGNORECASE),
    re.compile(r"^appendix\s+[a-z0-9]+\s*$", re.IGNORECASE),
    re.compile(r"^\d+\s+cfr\s+part\s+\d+\b", re.IGNORECASE),
    re.compile(r"^for further information contact:?$", re.IGNORECASE),
    re.compile(r"^page\s+(?:figure|table)\b", re.IGNORECASE),
    re.compile(r".*\btrend\s+p-value\b.*", re.IGNORECASE),
    re.compile(r".*\b#\s*of\b.*", re.IGNORECASE),
    re.compile(
        r"^\d{4}\s+[A-Za-z][A-Za-z'().-]+(?:\s+[A-Za-z][A-Za-z'().-]+){1,2}$",
        re.IGNORECASE,
    ),
    re.compile(r".*\bfield\s+review\s+report\b.*", re.IGNORECASE),
)
AUTO_FIXTURE_NAME_PATTERN = re.compile(r"[^a-z0-9]+")
AUTO_FILENAME_SPLIT_PATTERN = re.compile(r"\s*(?:[-|:]+)\s*")
AUTO_FILENAME_DATE_PREFIX_PATTERN = re.compile(r"^\d{6,8}\s+")


@dataclass
class EvaluationFixture:
    name: str
    source_filename: str
    document_sha256: str | None
    kind: str | None
    path: str | None
    queries: list[EvaluationQueryCase]
    answer_queries: list[EvaluationAnswerCase]
    thresholds: EvaluationThresholds


@dataclass
class EvaluationQueryCase:
    query: str
    mode: str
    filters: dict
    include_document_filter: bool
    expected_result_type: str
    expected_top_n: int
    expected_source_filename: str | None = None
    expected_top_result_source_filename: str | None = None
    minimum_top_n_hits_from_expected_document: int | None = None
    maximum_foreign_results_before_first_expected_hit: int | None = None


@dataclass
class EvaluationAnswerCase:
    question: str
    mode: str
    filters: dict
    include_document_filter: bool
    expected_answer_contains: list[str]
    minimum_citation_count: int
    allow_fallback: bool
    top_k: int
    expected_result_type: str | None = None
    expect_no_answer: bool = False
    maximum_citation_count: int | None = None
    expected_citation_source_filename: str | None = None
    maximum_foreign_citations: int | None = None


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


def _auto_corpus_path() -> Path:
    return get_settings().storage_root.resolve() / AUTO_CORPUS_FILENAME


def _configured_manual_corpus_path() -> Path | None:
    configured = getattr(get_settings(), "manual_evaluation_corpus_path", None)
    if configured is None:
        return None
    return Path(configured).expanduser().resolve()


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
            "source_filename": result.source_filename,
        }
        for idx, result in enumerate(results[:limit], start=1)
    ]


def _matching_rank(
    results: list[SearchResult],
    expected_result_type: str,
    *,
    expected_source_filename: str | None = None,
) -> int | None:
    for idx, result in enumerate(results, start=1):
        if result.result_type == expected_result_type and source_filename_matches(
            result.source_filename, expected_source_filename
        ):
            return idx
    return None


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


def _normalize_fixture_query(entry: dict, expected_result_type: str) -> EvaluationQueryCase:
    return EvaluationQueryCase(
        query=entry["query"],
        mode=entry.get("mode", "hybrid"),
        filters=entry.get("filters") or {},
        include_document_filter=bool(entry.get("include_document_filter", True)),
        expected_result_type=entry.get("expected_result_type", expected_result_type),
        expected_top_n=entry.get("top_n", 3),
        expected_source_filename=entry.get("expected_source_filename"),
        expected_top_result_source_filename=entry.get("expected_top_result_source_filename"),
        minimum_top_n_hits_from_expected_document=entry.get(
            "minimum_top_n_hits_from_expected_document"
        ),
        maximum_foreign_results_before_first_expected_hit=entry.get(
            "maximum_foreign_results_before_first_expected_hit"
        ),
    )


def _normalize_fixture_answer(entry: dict) -> EvaluationAnswerCase:
    answer_contains = entry.get("answer_contains") or entry.get("expected_answer_contains") or []
    if isinstance(answer_contains, str):
        answer_contains = [answer_contains]
    return EvaluationAnswerCase(
        question=entry.get("question") or entry["query"],
        mode=entry.get("mode", "hybrid"),
        filters=entry.get("filters") or {},
        include_document_filter=bool(entry.get("include_document_filter", True)),
        expected_answer_contains=answer_contains,
        minimum_citation_count=entry.get("minimum_citation_count", 1),
        allow_fallback=bool(entry.get("allow_fallback", False)),
        top_k=entry.get("top_k", 6),
        expected_result_type=entry.get("expected_result_type"),
        expect_no_answer=bool(entry.get("expect_no_answer", False)),
        maximum_citation_count=entry.get("maximum_citation_count"),
        expected_citation_source_filename=entry.get("expected_citation_source_filename"),
        maximum_foreign_citations=entry.get("maximum_foreign_citations"),
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
    primary_path = (
        Path(corpus_path).expanduser().resolve()
        if corpus_path is not None
        else _configured_manual_corpus_path()
    )
    paths: list[Path] = []
    if primary_path is not None:
        paths.append(primary_path)
    auto_path = _auto_corpus_path()
    if auto_path.exists() and auto_path not in paths:
        paths.append(auto_path)
    return paths


def _fixture_source_filename(document: dict) -> str | None:
    raw_source_filename = document.get("source_filename")
    if raw_source_filename:
        return Path(str(raw_source_filename)).name

    doc_path = document.get("path")
    if doc_path:
        return Path(str(doc_path)).name

    return None


def _normalized_document_sha256(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    return normalized or None


def _fixture_document_sha256(document: dict) -> str | None:
    return _normalized_document_sha256(document.get("sha256") or document.get("document_sha256"))


def load_evaluation_fixtures(corpus_path: Path | None = None) -> list[EvaluationFixture]:
    fixtures: list[EvaluationFixture] = []
    for path in _fixture_paths(corpus_path):
        for document in _load_corpus_documents(path):
            source_filename = _fixture_source_filename(document)
            if source_filename is None:
                continue
            doc_path = document.get("path")
            thresholds = document.get("thresholds", {})
            queries: list[EvaluationQueryCase] = []
            answer_queries: list[EvaluationAnswerCase] = []
            for entry in thresholds.get("expected_top_n_table_hit_queries", []):
                queries.append(_normalize_fixture_query(entry, "table"))
            for entry in thresholds.get("expected_top_n_chunk_hit_queries", []):
                queries.append(_normalize_fixture_query(entry, "chunk"))
            for entry in thresholds.get("queries", []):
                queries.append(
                    _normalize_fixture_query(
                        entry,
                        entry["expected_result_type"],
                    )
                )
            for entry in thresholds.get("expected_answer_queries", []):
                answer_queries.append(_normalize_fixture_answer(entry))
            fixtures.append(
                EvaluationFixture(
                    name=document["name"],
                    source_filename=source_filename,
                    document_sha256=_fixture_document_sha256(document),
                    kind=document.get("kind"),
                    path=str(doc_path) if doc_path else None,
                    queries=queries,
                    answer_queries=answer_queries,
                    thresholds=_normalize_thresholds(thresholds),
                )
            )
    return fixtures


def fixture_for_document(
    document: Document,
    corpus_path: Path | None = None,
    *,
    allow_manual_filename_fallback: bool = False,
) -> EvaluationFixture | None:
    fixtures = load_evaluation_fixtures(corpus_path)
    document_sha256 = _normalized_document_sha256(getattr(document, "sha256", None))
    if document_sha256 is not None:
        for fixture in fixtures:
            if fixture.document_sha256 == document_sha256:
                return fixture

    document_source_filename = getattr(document, "source_filename", None)
    if not document_source_filename:
        return None

    filename_matches = [
        fixture
        for fixture in fixtures
        if source_filename_matches(fixture.source_filename, document_source_filename)
    ]
    auto_matches = [fixture for fixture in filename_matches if fixture.kind == AUTO_FIXTURE_KIND]
    if len(auto_matches) == 1:
        return auto_matches[0]

    if allow_manual_filename_fallback:
        if len(filename_matches) == 1:
            return filename_matches[0]
        manual_matches = [
            fixture for fixture in filename_matches if fixture.kind != AUTO_FIXTURE_KIND
        ]
        if len(manual_matches) == 1:
            return manual_matches[0]
    return None


def _first_sentence(value: str | None) -> str:
    collapsed = collapse_whitespace(value)
    if not collapsed:
        return ""
    return re.split(r"(?<=[.!?])\s+", collapsed, maxsplit=1)[0]


def _collapse_adjacent_duplicate_words(value: str) -> str:
    words = value.split()
    collapsed: list[str] = []
    for word in words:
        normalized_word = re.sub(r"[^A-Za-z0-9]+", "", word).lower()
        if (
            collapsed
            and normalized_word
            and normalized_word == re.sub(r"[^A-Za-z0-9]+", "", collapsed[-1]).lower()
        ):
            continue
        collapsed.append(word)
    return " ".join(collapsed)


def _normalize_query_candidate(
    value: str | None,
    *,
    strip_table_prefix: bool = False,
    max_words: int = AUTO_QUERY_MAX_WORDS,
) -> str | None:
    text = collapse_whitespace(value)
    if not text:
        return None
    if strip_table_prefix:
        text = TABLE_PREFIX_PATTERN.sub("", text)
    text = _collapse_adjacent_duplicate_words(text)
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


def _is_low_signal_chunk_query(query: str) -> bool:
    normalized = collapse_whitespace(query).strip(" .,:;|-")
    if any(pattern.match(normalized) for pattern in LOW_SIGNAL_CHUNK_QUERY_PATTERNS):
        return True

    words = normalized.split()
    if 2 <= len(words) <= 4 and any(marker in normalized for marker in (",", "/", ".")):
        alphabetic_words = re.findall(r"[A-Za-z]+", normalized)
        if len(alphabetic_words) >= 2 and all(len(word) <= 3 for word in alphabetic_words):
            return True

    return False


def _is_section_heading_query(query: str) -> bool:
    normalized = collapse_whitespace(query).strip(" .,:;|-")
    return bool(SECTION_HEADING_QUERY_PATTERN.match(normalized))


def _is_low_signal_table_query(query: str) -> bool:
    normalized = collapse_whitespace(query).strip(" .,:;|-")
    if any(pattern.match(normalized) for pattern in LOW_SIGNAL_TABLE_QUERY_PATTERNS):
        return True
    if "|" not in normalized:
        return False

    cells = [cell.strip(" .,:;|-") for cell in normalized.split("|") if cell.strip(" .,:;|-")]
    if len(cells) < 2:
        return False
    if cells[0].isdigit():
        return True

    lowered_cells = [cell.lower() for cell in cells]
    if lowered_cells[0].startswith("contents") and any(
        "page" in cell for cell in lowered_cells[1:]
    ):
        return True
    return len(set(lowered_cells[: min(3, len(lowered_cells))])) < min(3, len(lowered_cells))


def _is_weak_table_text_fallback(query: str) -> bool:
    normalized = collapse_whitespace(query).strip(" .,:;|-")
    if not normalized:
        return True
    if "|" in normalized:
        return True
    words = normalized.split()
    if words and any(char.isdigit() for char in words[0]):
        return True
    alphabetic_words = [word for word in words if re.search(r"[A-Za-z]", word)]
    return len(alphabetic_words) < 3


def _pipe_cell_query_candidate(value: str | None) -> str | None:
    text = collapse_whitespace(value)
    if not text or "|" not in text:
        return None

    pieces: list[str] = []
    seen: set[str] = set()
    for raw_cell in text.split("|"):
        query = _normalize_query_candidate(raw_cell, strip_table_prefix=True, max_words=4)
        if query is None:
            continue
        if _is_low_signal_table_query(query) or _is_low_signal_chunk_query(query):
            continue
        key = query.lower()
        if key in seen:
            continue
        seen.add(key)
        pieces.append(query)
        if len(pieces) < 2:
            continue
        combined = _normalize_query_candidate(" ".join(pieces), strip_table_prefix=True)
        if combined is None:
            continue
        if _is_low_signal_table_query(combined) or _is_low_signal_chunk_query(combined):
            continue
        return combined
    return None


def _auto_fixture_name(source_filename: str) -> str:
    stem = Path(source_filename).stem.lower()
    slug = AUTO_FIXTURE_NAME_PATTERN.sub("_", stem).strip("_")
    return f"auto_{slug or 'document'}"


def _auto_table_query(table: object) -> str | None:
    richer_candidates = [
        query
        for query in (
            _pipe_cell_query_candidate(getattr(table, "preview_text", None)),
            _pipe_cell_query_candidate(getattr(table, "search_text", None)),
        )
        if query
    ]
    for candidate, preview_fallback in (
        (getattr(table, "title", None), False),
        (getattr(table, "heading", None), False),
        (getattr(table, "preview_text", None), True),
        (getattr(table, "search_text", None), True),
    ):
        query = _pipe_cell_query_candidate(candidate) if preview_fallback else None
        if query is None:
            text_candidate = _first_sentence(candidate) if preview_fallback else candidate
            query = _normalize_query_candidate(text_candidate, strip_table_prefix=True)
        if query:
            if _is_low_signal_table_query(query):
                continue
            if not preview_fallback and len(query.split()) <= 4:
                richer_query = next(
                    (
                        candidate
                        for candidate in richer_candidates
                        if candidate.lower() != query.lower()
                        and (
                            candidate.lower().startswith(query.lower())
                            or query.lower() in candidate.lower()
                        )
                    ),
                    None,
                )
                if richer_query is not None:
                    return richer_query
            if preview_fallback and _is_weak_table_text_fallback(query):
                continue
            return query
    return None


def _cover_chunk_queries(chunks: list[object], *, limit: int = 1) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()
    for chunk in chunks[:8]:
        if getattr(chunk, "heading", None):
            continue
        page_from = getattr(chunk, "page_from", None)
        if page_from is not None and page_from != 1:
            continue
        query = _normalize_query_candidate(_first_sentence(getattr(chunk, "text", None)))
        if query is None or _is_low_signal_chunk_query(query):
            continue
        key = query.lower()
        if key in seen:
            continue
        seen.add(key)
        queries.append(query)
        if len(queries) >= limit:
            break
    return queries


def _source_filename_queries(source_filename: str) -> list[str]:
    stem = Path(source_filename).stem.replace("_", " ")
    stem = AUTO_FILENAME_DATE_PREFIX_PATTERN.sub("", stem).strip()
    candidates = [stem]
    candidates.extend(
        part.strip()
        for part in AUTO_FILENAME_SPLIT_PATTERN.split(stem)
        if part.strip() and part.strip() != stem
    )
    queries: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        query = _normalize_query_candidate(candidate)
        if query is None:
            continue
        key = query.lower()
        if key in seen:
            continue
        seen.add(key)
        queries.append(query)
    return queries


def _chunk_query_conflicts_with_tables(query: str, table_queries: list[str]) -> bool:
    normalized_query = query.lower()
    return any(
        normalized_query in table_query.lower() or table_query.lower() in normalized_query
        for table_query in table_queries
    )


def _auto_chunk_queries(
    title: str | None,
    source_filename: str,
    chunks: list[object],
    tables: list[object],
) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()
    if not tables:
        candidates: list[str | None] = [title, *_source_filename_queries(source_filename)]
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
            if _is_low_signal_chunk_query(query):
                continue
            key = query.lower()
            if key in seen:
                continue
            seen.add(key)
            queries.append(query)
            if len(queries) >= AUTO_CHUNK_QUERY_LIMIT:
                break
        return queries

    table_queries: list[str] = []
    for table in tables:
        for candidate in (
            getattr(table, "title", None),
            getattr(table, "heading", None),
            _auto_table_query(table),
        ):
            query = _normalize_query_candidate(candidate)
            if query is None:
                continue
            key = query.lower()
            if key in seen:
                continue
            seen.add(key)
            table_queries.append(query)

    seen.clear()
    title_query = _normalize_query_candidate(title)
    use_title_candidate = bool(
        title_query
        and not _is_low_signal_chunk_query(title_query)
        and not _is_section_heading_query(title_query)
    )

    content_candidates: list[str | None] = [title] if use_title_candidate else []
    if not use_title_candidate:
        content_candidates.extend(_cover_chunk_queries(chunks))
    for candidate in content_candidates:
        query = _normalize_query_candidate(candidate)
        if query is None:
            continue
        if _is_low_signal_chunk_query(query):
            continue
        if _chunk_query_conflicts_with_tables(query, table_queries):
            continue
        key = query.lower()
        if key in seen:
            continue
        seen.add(key)
        queries.append(query)
        if len(queries) >= AUTO_CHUNK_QUERY_LIMIT:
            break
    if queries:
        return queries
    for chunk in chunks[:24]:
        candidate = getattr(chunk, "heading", None)
        query = _normalize_query_candidate(candidate)
        if query is None:
            continue
        if _is_low_signal_chunk_query(query):
            continue
        if _chunk_query_conflicts_with_tables(query, table_queries):
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


def _filter_retrieval_backed_auto_queries(
    session: Session,
    document: Document,
    run: DocumentRun,
    entries: list[dict[str, object]],
    *,
    expected_result_type: str,
) -> list[dict[str, object]]:
    supported: list[tuple[int, int, dict[str, object]]] = []
    for index, entry in enumerate(entries):
        request = SearchRequest(
            query=str(entry["query"]),
            mode=str(entry.get("mode", "hybrid")),
            filters=SearchFilters(document_id=document.id),
            limit=max(int(entry.get("top_n", AUTO_QUERY_TOP_N)), 10),
        )
        results = search_documents(
            session,
            request,
            run_id=run.id,
            origin="auto_fixture_generation",
        )
        rank = _matching_rank(
            results,
            expected_result_type,
            expected_source_filename=document.source_filename,
        )
        if rank is None or rank > int(entry.get("top_n", AUTO_QUERY_TOP_N)):
            continue
        supported.append((rank, index, dict(entry)))

    supported.sort(key=lambda item: (item[0], item[1]))
    return [entry for _, _, entry in supported]


def _materialize_retrieval_backed_auto_fixture(
    session: Session,
    document: Document,
    run: DocumentRun,
    fixture_document: dict,
) -> dict:
    thresholds = dict(fixture_document.get("thresholds", {}))
    thresholds["expected_top_n_table_hit_queries"] = _filter_retrieval_backed_auto_queries(
        session,
        document,
        run,
        list(thresholds.get("expected_top_n_table_hit_queries", [])),
        expected_result_type="table",
    )
    thresholds["expected_top_n_chunk_hit_queries"] = _filter_retrieval_backed_auto_queries(
        session,
        document,
        run,
        list(thresholds.get("expected_top_n_chunk_hit_queries", [])),
        expected_result_type="chunk",
    )
    return {**fixture_document, "thresholds": thresholds}


def build_auto_evaluation_fixture_document(
    source_filename: str,
    *,
    sha256: str | None = None,
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
    can_emit_chunk_queries = bool(chunks)
    if can_emit_chunk_queries:
        for query in _auto_chunk_queries(title, source_filename, chunks, tables):
            if query.lower() in used_queries:
                continue
            used_queries.add(query.lower())
            chunk_queries.append({"query": query, "top_n": AUTO_QUERY_TOP_N, "mode": "hybrid"})
            if len(chunk_queries) >= AUTO_CHUNK_QUERY_LIMIT:
                break

    if not chunk_queries and not tables and can_emit_chunk_queries:
        filename_queries = _source_filename_queries(source_filename)
        if filename_queries:
            fallback = filename_queries[0]
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

    fixture_document = {
        "name": _auto_fixture_name(source_filename),
        "kind": AUTO_FIXTURE_KIND,
        "source_filename": source_filename,
        "autogenerated": True,
        "generated_from_run_id": str(run_id) if run_id else None,
        "thresholds": thresholds,
    }
    normalized_sha256 = _normalized_document_sha256(sha256)
    if normalized_sha256 is not None:
        fixture_document["sha256"] = normalized_sha256
    return fixture_document


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
        sha256=getattr(document, "sha256", None),
        title=title or getattr(document, "title", None),
        chunks=chunks,
        tables=tables,
        figures=figures,
        run_id=run.id,
    )
    fixture_document = _materialize_retrieval_backed_auto_fixture(
        session,
        document,
        run,
        fixture_document,
    )
    path = _auto_corpus_path()
    documents = [
        entry
        for entry in _load_corpus_documents(path)
        if not (
            _fixture_document_sha256(entry)
            == _normalized_document_sha256(getattr(document, "sha256", None))
            or (
                _fixture_document_sha256(entry) is None
                and source_filename_matches(
                    _fixture_source_filename(entry),
                    document.source_filename,
                )
            )
        )
    ]
    documents.append(fixture_document)
    documents.sort(key=lambda entry: (_fixture_source_filename(entry) or "").lower())
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
        created_at=utcnow(),
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
        if fixture is None or fixture.kind == AUTO_FIXTURE_KIND:
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
