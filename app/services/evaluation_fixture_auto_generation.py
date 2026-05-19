from __future__ import annotations

import re
from importlib import import_module
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.evaluation_fixtures as fixture_owners
from app.core.files import source_filename_matches
from app.core.text import collapse_whitespace
from app.db.models import Document, DocumentChunk, DocumentFigure, DocumentRun, DocumentTable

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
    stem = fixture_owners.Path(source_filename).stem.lower()
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
                        richer_candidate
                        for richer_candidate in richer_candidates
                        if richer_candidate.lower() != query.lower()
                        and (
                            richer_candidate.lower().startswith(query.lower())
                            or query.lower() in richer_candidate.lower()
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
    stem = fixture_owners.Path(source_filename).stem.replace("_", " ")
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
        metadata = fixture_owners._metadata_for_row(figure)
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
        int(bool(fixture_owners._normalized_caption_text(getattr(figure, "caption", None))))
        for figure in figures
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
        "kind": fixture_owners.AUTO_FIXTURE_KIND,
        "source_filename": source_filename,
        "autogenerated": True,
        "generated_from_run_id": str(run_id) if run_id else None,
        "thresholds": thresholds,
    }
    normalized_sha256 = fixture_owners._normalized_document_sha256(sha256)
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
    path = fixture_owners._auto_corpus_path()
    documents = [
        entry
        for entry in fixture_owners._load_corpus_documents(path)
        if not (
            fixture_owners._fixture_document_sha256(entry)
            == fixture_owners._normalized_document_sha256(getattr(document, "sha256", None))
            or (
                fixture_owners._fixture_document_sha256(entry) is None
                and source_filename_matches(
                    fixture_owners._fixture_source_filename(entry),
                    document.source_filename,
                )
            )
        )
    ]
    documents.append(fixture_document)
    documents.sort(key=lambda entry: (fixture_owners._fixture_source_filename(entry) or "").lower())
    fixture_owners._write_corpus_documents(path, documents)
    return fixture_document


materialization_owners = import_module("app.services.evaluation_fixture_materialization")

_filter_retrieval_backed_auto_queries = materialization_owners._filter_retrieval_backed_auto_queries
_materialize_retrieval_backed_auto_fixture = (
    materialization_owners._materialize_retrieval_backed_auto_fixture
)
