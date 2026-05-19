from __future__ import annotations

import sys
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path

import yaml

from app.core.config import get_settings as _base_get_settings
from app.core.files import source_filename_matches
from app.db.models import Document
from app.schemas.search import SearchResult
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


auto_generation_owners = import_module("app.services.evaluation_fixture_auto_generation")

AUTO_QUERY_TOP_N = auto_generation_owners.AUTO_QUERY_TOP_N
AUTO_TABLE_QUERY_LIMIT = auto_generation_owners.AUTO_TABLE_QUERY_LIMIT
AUTO_CHUNK_QUERY_LIMIT = auto_generation_owners.AUTO_CHUNK_QUERY_LIMIT
AUTO_QUERY_MAX_WORDS = auto_generation_owners.AUTO_QUERY_MAX_WORDS
SECTION_HEADING_QUERY_PATTERN = auto_generation_owners.SECTION_HEADING_QUERY_PATTERN
TABLE_PREFIX_PATTERN = auto_generation_owners.TABLE_PREFIX_PATTERN
LOW_SIGNAL_CHUNK_QUERY_PATTERNS = auto_generation_owners.LOW_SIGNAL_CHUNK_QUERY_PATTERNS
LOW_SIGNAL_TABLE_QUERY_PATTERNS = auto_generation_owners.LOW_SIGNAL_TABLE_QUERY_PATTERNS
AUTO_FIXTURE_NAME_PATTERN = auto_generation_owners.AUTO_FIXTURE_NAME_PATTERN
AUTO_FILENAME_SPLIT_PATTERN = auto_generation_owners.AUTO_FILENAME_SPLIT_PATTERN
AUTO_FILENAME_DATE_PREFIX_PATTERN = auto_generation_owners.AUTO_FILENAME_DATE_PREFIX_PATTERN
build_auto_evaluation_fixture_document = (
    auto_generation_owners.build_auto_evaluation_fixture_document
)
ensure_auto_evaluation_fixture = auto_generation_owners.ensure_auto_evaluation_fixture
