from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings as _base_get_settings
from app.core.files import source_filename_matches
from app.core.text import collapse_whitespace
from app.db.models import Document, DocumentChunk, DocumentFigure, DocumentRun, DocumentTable
from app.schemas.search import SearchFilters, SearchRequest, SearchResult
from app.services.evaluation_fixture_cache import load_corpus_documents_cached
from app.services.search import search_documents as _search_documents


def get_settings():
    facade = sys.modules.get("app.services.evaluations")
    facade_get_settings = getattr(facade, "get_settings", None) if facade is not None else None
    if callable(facade_get_settings) and facade_get_settings is not get_settings:
        return facade_get_settings()
    return _base_get_settings()


def search_documents(*args, **kwargs):
    facade = sys.modules.get("app.services.evaluations")
    facade_search_documents = (
        getattr(facade, "search_documents", None) if facade is not None else None
    )
    if callable(facade_search_documents) and facade_search_documents is not search_documents:
        return facade_search_documents(*args, **kwargs)
    return _search_documents(*args, **kwargs)

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
    return load_corpus_documents_cached(path)


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


def _metadata_for_row(row: object) -> dict:
    return getattr(row, "metadata_json", None) or getattr(row, "metadata", None) or {}


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
