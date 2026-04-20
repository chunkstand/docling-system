from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from app.core.config import default_local_ingest_roots, get_settings

HEADING_PATTERN = re.compile(r"^(Chapter\s+\d+|Part\s+[IVXLC]+|[0-9]+(?:\.[0-9]+)*\s)")
TABLE_LABEL_PATTERN = re.compile(r"^TABLE\s+[0-9A-Z().-]+", re.IGNORECASE)
TITLE_REGEX_FAMILY_MATCHER = "title_regex_family"
DEFAULT_CONTINUATION_TITLE_PATTERN = r"\bcontinued\b"
TABLE_ARTIFACT_SCHEMA_VERSION = "1.0"
FIGURE_ARTIFACT_SCHEMA_VERSION = "1.0"
UUID_LIKE_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@dataclass
class ParsedChunk:
    chunk_index: int
    text: str
    heading: str | None
    page_from: int | None
    page_to: int | None
    metadata: dict[str, Any]
    embedding: list[float] | None = None


@dataclass
class ParsedTableSegment:
    segment_index: int
    segment_order: int
    source_table_ref: str | None
    title: str | None
    heading: str | None
    page_from: int | None
    page_to: int | None
    row_count: int
    col_count: int
    rows: list[list[str]]
    metadata: dict[str, Any]


@dataclass
class ParsedTable:
    table_index: int
    title: str | None
    heading: str | None
    page_from: int | None
    page_to: int | None
    row_count: int
    col_count: int
    rows: list[list[str]]
    search_text: str
    preview_text: str
    metadata: dict[str, Any]
    segments: list[ParsedTableSegment]
    embedding: list[float] | None = None

    def artifact_payload(
        self,
        *,
        document_id: str,
        run_id: str,
        table_id: str,
        logical_table_key: str | None,
        created_at: str,
    ) -> dict[str, Any]:
        artifact_metadata = {
            key: value for key, value in (self.metadata or {}).items() if key != "audit"
        }
        return {
            "schema_version": TABLE_ARTIFACT_SCHEMA_VERSION,
            "document_id": document_id,
            "run_id": run_id,
            "table_id": table_id,
            "table_index": self.table_index,
            "logical_table_key": logical_table_key,
            "title": self.title,
            "heading": self.heading,
            "page_from": self.page_from,
            "page_to": self.page_to,
            "row_count": self.row_count,
            "col_count": self.col_count,
            "created_at": created_at,
            "search_text": self.search_text,
            "preview_text": self.preview_text,
            "metadata": artifact_metadata,
            "rows": self.rows,
            "segments": [
                {
                    "segment_index": segment.segment_index,
                    "segment_order": segment.segment_order,
                    "source_table_ref": segment.source_table_ref,
                    "title": segment.title,
                    "heading": segment.heading,
                    "page_from": segment.page_from,
                    "page_to": segment.page_to,
                    "row_count": segment.row_count,
                    "col_count": segment.col_count,
                    "metadata": segment.metadata,
                }
                for segment in self.segments
            ],
        }


@dataclass
class ParsedFigure:
    figure_index: int
    source_figure_ref: str | None
    caption: str | None
    heading: str | None
    page_from: int | None
    page_to: int | None
    confidence: float | None
    metadata: dict[str, Any]

    def artifact_payload(
        self,
        *,
        document_id: str,
        run_id: str,
        figure_id: str,
        created_at: str,
    ) -> dict[str, Any]:
        artifact_metadata = {
            key: value for key, value in (self.metadata or {}).items() if key != "audit"
        }
        return {
            "schema_version": FIGURE_ARTIFACT_SCHEMA_VERSION,
            "document_id": document_id,
            "run_id": run_id,
            "figure_id": figure_id,
            "figure_index": self.figure_index,
            "page_from": self.page_from,
            "page_to": self.page_to,
            "created_at": created_at,
            "source_figure_ref": self.source_figure_ref,
            "caption": self.caption,
            "heading": self.heading,
            "confidence": self.confidence,
            "metadata": artifact_metadata,
        }


@dataclass
class ParsedDocument:
    title: str | None
    page_count: int
    yaml_text: str
    docling_json: str
    chunks: list[ParsedChunk]
    tables: list[ParsedTable]
    raw_table_segments: list[ParsedTableSegment]
    figures: list[ParsedFigure]


@dataclass
class ItemSnapshot:
    index: int
    self_ref: str | None
    label: str
    text: str | None
    level: int | None
    page_from: int | None
    page_to: int | None


@dataclass(frozen=True)
class TableFamilyMatcher:
    kind: str
    family_key_pattern: str
    continuation_title_pattern: str | None = DEFAULT_CONTINUATION_TITLE_PATTERN
    max_page_gap: int = 1
    require_same_heading: bool = True


@dataclass(frozen=True)
class TableSupplementRule:
    document_filenames: tuple[str, ...]
    supplement_filename: str
    matcher: TableFamilyMatcher
    overlay_type: str
    description: str | None = None

    def matches_document(self, source_filename: str | None) -> bool:
        if source_filename is None:
            return False
        normalized = Path(source_filename).name
        return normalized in self.document_filenames


def _normalize_document_title(value: str | None) -> str | None:
    text = " ".join((value or "").split()).strip()
    if not text or len(text) > 160:
        return None
    if UUID_LIKE_PATTERN.fullmatch(text):
        return None
    return text


def _infer_document_title(chunks: list[ParsedChunk], document_name: str | None) -> str:
    heading_title = next(
        (
            normalized
            for chunk in chunks
            if (normalized := _normalize_document_title(chunk.heading)) is not None
        ),
        None,
    )
    if heading_title is not None:
        return heading_title

    text_title = next(
        (
            normalized
            for chunk in chunks
            if (normalized := _normalize_document_title(chunk.text)) is not None
        ),
        None,
    )
    if text_title is not None:
        return text_title

    return _normalize_document_title(document_name) or "Untitled document"


def _synthetic_title_chunk(title: str, *, page_count: int) -> ParsedChunk:
    page_value = 1 if page_count > 0 else None
    return ParsedChunk(
        chunk_index=0,
        text=title,
        heading=title,
        page_from=page_value,
        page_to=page_value,
        metadata={
            "synthetic": True,
            "synthetic_source": "document_title_fallback",
        },
    )


@lru_cache(maxsize=1)
def get_document_converter() -> DocumentConverter:
    settings = get_settings()
    options = PdfPipelineOptions()
    options.document_timeout = settings.docling_document_timeout_seconds
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=options),
        }
    )


@lru_cache(maxsize=1)
def get_fallback_document_converter() -> DocumentConverter:
    settings = get_settings()
    options = PdfPipelineOptions()
    fallback_timeout = settings.docling_fallback_document_timeout_seconds
    primary_timeout = settings.docling_document_timeout_seconds
    if fallback_timeout is None:
        options.document_timeout = primary_timeout
    elif primary_timeout is None:
        options.document_timeout = fallback_timeout
    else:
        options.document_timeout = max(fallback_timeout, primary_timeout)
    options.do_ocr = False
    options.do_table_structure = False
    options.force_backend_text = True
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=options),
        }
    )


@lru_cache(maxsize=1)
def get_timeout_rescue_document_converter() -> DocumentConverter:
    options = PdfPipelineOptions()
    options.document_timeout = None
    options.do_ocr = False
    options.do_table_structure = False
    options.force_backend_text = True
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=options),
        }
    )


def _conversion_status_value(result: Any) -> str | None:
    status = getattr(result, "status", None)
    if status is None:
        return None
    return getattr(status, "value", status)


def _conversion_succeeded(result: Any) -> bool:
    return _conversion_status_value(result) in {None, "success"}


def _conversion_error_message(
    result: Any,
    *,
    source_path: Path,
    attempted_fallback: bool,
) -> str:
    status = _conversion_status_value(result) or "unknown"
    errors = getattr(result, "errors", None) or []
    if isinstance(errors, list):
        detail = "; ".join(str(item) for item in errors if item)
    else:
        detail = str(errors)
    prefix = (
        "Docling conversion failed after fallback"
        if attempted_fallback
        else "Docling conversion failed"
    )
    if detail:
        return f"{prefix} for {source_path.name}: status={status}; {detail}"
    return f"{prefix} for {source_path.name}: status={status}"


def _conversion_timed_out(result: Any) -> bool:
    status = _conversion_status_value(result) or ""
    if status not in {"partial_success", "failure"}:
        return False
    errors = getattr(result, "errors", None) or []
    if isinstance(errors, list):
        return any("document timeout exceeded" in str(item).lower() for item in errors if item)
    return "document timeout exceeded" in str(errors).lower()


def _should_attempt_timeout_rescue(primary_result: Any, fallback_result: Any) -> bool:
    fallback_status = _conversion_status_value(fallback_result) or ""
    if fallback_status == "success":
        return False
    return (
        _conversion_timed_out(primary_result)
        or _conversion_timed_out(fallback_result)
        or fallback_status == "partial_success"
    )


@lru_cache(maxsize=4)
def _load_table_supplement_registry(registry_path: str) -> tuple[TableSupplementRule, ...]:
    path = Path(registry_path)
    if not path.is_file():
        return ()

    payload = yaml.safe_load(path.read_text()) or {}
    if not isinstance(payload, dict):
        raise ValueError("Table supplement registry must be a mapping.")

    raw_rules = payload.get("rules") or []
    if not isinstance(raw_rules, list):
        raise ValueError("Table supplement registry rules must be a list.")

    rules: list[TableSupplementRule] = []
    for raw_rule in raw_rules:
        if not isinstance(raw_rule, dict):
            raise ValueError("Each table supplement rule must be a mapping.")

        raw_filenames = raw_rule.get("document_filenames") or raw_rule.get("document_filename")
        if isinstance(raw_filenames, str):
            document_filenames = (Path(raw_filenames).name,)
        elif isinstance(raw_filenames, list) and raw_filenames:
            document_filenames = tuple(Path(str(item)).name for item in raw_filenames if item)
        else:
            raise ValueError("Table supplement rules require document_filenames.")

        raw_matcher = raw_rule.get("matcher")
        matcher_payload = raw_matcher if isinstance(raw_matcher, dict) else {}
        matcher_kind = (
            matcher_payload.get("kind")
            if isinstance(raw_matcher, dict)
            else raw_matcher or raw_rule.get("matcher_kind")
        )
        if not matcher_kind and raw_rule.get("family_key_pattern"):
            matcher_kind = TITLE_REGEX_FAMILY_MATCHER
        matcher_kind = str(matcher_kind or "").strip()
        if matcher_kind != TITLE_REGEX_FAMILY_MATCHER:
            raise ValueError(f"Unsupported table supplement matcher: {matcher_kind}")

        family_key_pattern = str(
            matcher_payload.get("family_key_pattern") or raw_rule.get("family_key_pattern") or ""
        ).strip()
        if not family_key_pattern:
            raise ValueError("Table supplement rules require family_key_pattern.")
        continuation_title_pattern = (
            matcher_payload.get("continuation_title_pattern")
            or raw_rule.get("continuation_title_pattern")
            or DEFAULT_CONTINUATION_TITLE_PATTERN
        )
        if continuation_title_pattern is not None:
            continuation_title_pattern = str(continuation_title_pattern).strip() or None
        max_page_gap = int(
            matcher_payload.get("max_page_gap") or raw_rule.get("max_page_gap") or 1
        )
        require_same_heading = bool(
            matcher_payload.get("require_same_heading", raw_rule.get("require_same_heading", True))
        )

        supplement_filename = Path(str(raw_rule.get("supplement_filename") or "")).name
        if not supplement_filename:
            raise ValueError("Table supplement rules require supplement_filename.")

        overlay_type = (
            str(raw_rule.get("overlay_type") or "").strip() or "clean_pdf_family_replacement"
        )
        description = raw_rule.get("description")
        rules.append(
            TableSupplementRule(
                document_filenames=document_filenames,
                supplement_filename=supplement_filename,
                matcher=TableFamilyMatcher(
                    kind=matcher_kind,
                    family_key_pattern=family_key_pattern,
                    continuation_title_pattern=continuation_title_pattern,
                    max_page_gap=max_page_gap,
                    require_same_heading=require_same_heading,
                ),
                overlay_type=overlay_type,
                description=str(description).strip() if description else None,
            )
        )

    return tuple(rules)


def get_table_supplement_registry() -> tuple[TableSupplementRule, ...]:
    settings = get_settings()
    registry_path = settings.table_supplement_registry_path.expanduser().resolve()
    return _load_table_supplement_registry(str(registry_path))


def _collect_page_range(item: Any) -> tuple[int | None, int | None]:
    provenances = getattr(item, "prov", None) or []
    if not provenances:
        return None, None

    page_numbers = [
        prov.page_no for prov in provenances if getattr(prov, "page_no", None) is not None
    ]
    if not page_numbers:
        return None, None
    return min(page_numbers), max(page_numbers)


def _normalize_text(value: str | None) -> str:
    # Docling can emit raw NUL bytes from OCR-heavy tables; Postgres rejects them in text fields.
    return " ".join((value or "").replace("\x00", " ").split()).strip()


def _is_structural_heading(snapshot: ItemSnapshot) -> bool:
    return snapshot.label == "section_header" and bool(
        snapshot.text and HEADING_PATTERN.match(snapshot.text)
    )


def _snapshot_items(docling_document: Any) -> list[ItemSnapshot]:
    snapshots: list[ItemSnapshot] = []
    for index, (item, _level) in enumerate(docling_document.iterate_items()):
        page_from, page_to = _collect_page_range(item)
        snapshots.append(
            ItemSnapshot(
                index=index,
                self_ref=getattr(item, "self_ref", None),
                label=str(getattr(item, "label", "")),
                text=_normalize_text(getattr(item, "text", None)),
                level=getattr(item, "level", None),
                page_from=page_from,
                page_to=page_to,
            )
        )
    return snapshots


def _normalize_chunks(snapshots: list[ItemSnapshot]) -> list[ParsedChunk]:
    chunks: list[ParsedChunk] = []
    current_heading: str | None = None

    for snapshot in snapshots:
        normalized_text = snapshot.text or ""
        if not normalized_text:
            continue

        metadata: dict[str, Any] = {"label": snapshot.label}
        if snapshot.level is not None:
            metadata["level"] = snapshot.level

        if _is_structural_heading(snapshot):
            current_heading = normalized_text
            continue

        if snapshot.label == "table":
            continue

        chunks.append(
            ParsedChunk(
                chunk_index=len(chunks),
                text=normalized_text,
                heading=current_heading,
                page_from=snapshot.page_from,
                page_to=snapshot.page_to,
                metadata=metadata,
            )
        )

    return chunks


def _normalize_grid_rows(table_data: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for grid_row in table_data.get("grid") or []:
        row = [_normalize_text(cell.get("text")) for cell in grid_row]
        if any(row):
            rows.append(row)
    return rows


def _build_exported_text_lookup(exported_doc: dict[str, Any]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for item in exported_doc.get("texts") or []:
        ref = item.get("self_ref")
        text = _normalize_text(item.get("text") or item.get("orig"))
        if ref and text:
            lookup[ref] = text
    return lookup


def _sha256_json(value: Any) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _page_distance(reference: ItemSnapshot, candidate: ItemSnapshot) -> int:
    reference_page = reference.page_from or reference.page_to or 0
    candidate_page = candidate.page_from or candidate.page_to or 0
    return abs(reference_page - candidate_page)


def _normalize_provenance(provenances: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for prov in provenances or []:
        bbox = prov.get("bbox") or {}
        normalized.append(
            {
                "page_no": prov.get("page_no"),
                "bbox": {
                    "l": bbox.get("l"),
                    "t": bbox.get("t"),
                    "r": bbox.get("r"),
                    "b": bbox.get("b"),
                    "coord_origin": bbox.get("coord_origin"),
                },
                "charspan": prov.get("charspan"),
            }
        )
    return normalized


def _annotation_confidence(value: Any) -> float | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if lowered in {"confidence", "score", "probability"} and isinstance(
                nested, (int, float)
            ):
                return float(nested)
            nested_value = _annotation_confidence(nested)
            if nested_value is not None:
                return nested_value
    if isinstance(value, list):
        for item in value:
            nested_value = _annotation_confidence(item)
            if nested_value is not None:
                return nested_value
    return None


def _find_nearby_caption(snapshots: list[ItemSnapshot], table_snapshot: ItemSnapshot) -> str | None:
    best_match: tuple[int, str] | None = None
    for candidate in snapshots[
        max(0, table_snapshot.index - 3) : min(len(snapshots), table_snapshot.index + 4)
    ]:
        text = candidate.text or ""
        if not TABLE_LABEL_PATTERN.match(text):
            continue
        score = abs(candidate.index - table_snapshot.index) + (
            _page_distance(table_snapshot, candidate) * 2
        )
        if best_match is None or score < best_match[0]:
            best_match = (score, text)
    return best_match[1] if best_match else None


def _is_figure_group_label(text: str) -> bool:
    normalized = text.lower()
    return "diagram" in normalized or "figure" in normalized


def _looks_like_figure_caption_candidate(snapshot: ItemSnapshot) -> bool:
    text = snapshot.text or ""
    if not text:
        return False
    if snapshot.label in {"table", "picture", "footnote", "list_item"}:
        return False
    if _is_structural_heading(snapshot):
        return False
    if TABLE_LABEL_PATTERN.match(text):
        return False
    if text.lower() == "diagram":
        return False
    if len(text.split()) > 20:
        return False
    return True


def _find_nearby_figure_caption(
    snapshots: list[ItemSnapshot],
    picture_snapshot: ItemSnapshot,
) -> tuple[str | None, str, float | None, list[str]]:
    candidates: list[ItemSnapshot] = []
    start = max(0, picture_snapshot.index - 2)
    end = min(len(snapshots), picture_snapshot.index + 5)
    for candidate in snapshots[start:end]:
        if not _looks_like_figure_caption_candidate(candidate):
            continue
        if candidate.index == picture_snapshot.index:
            continue
        candidates.append(candidate)

    if not candidates:
        return None, "none", None, []

    candidates.sort(
        key=lambda candidate: (
            0 if candidate.index >= picture_snapshot.index else 1,
            abs(candidate.index - picture_snapshot.index),
            _page_distance(picture_snapshot, candidate),
        )
    )
    candidate_texts = [candidate.text or "" for candidate in candidates]
    primary = candidates[0]
    secondary = candidates[1] if len(candidates) > 1 else None

    if primary.label == "caption":
        return primary.text, "nearby_caption", 0.85, candidate_texts

    if primary.text and _is_figure_group_label(primary.text) and secondary and secondary.text:
        return (
            f"{primary.text} {secondary.text}".strip(),
            "nearby_group_label",
            0.7,
            candidate_texts,
        )

    return primary.text, "nearby_text", 0.6, candidate_texts


def _looks_like_table_title_hint(snapshot: ItemSnapshot) -> bool:
    if not snapshot.text or snapshot.label in {"table", "caption", "footnote", "list_item"}:
        return False
    if _is_structural_heading(snapshot):
        return False
    if TABLE_LABEL_PATTERN.match(snapshot.text):
        return False
    word_count = len(snapshot.text.split())
    if word_count < 2 and len(snapshot.text) < 8:
        return False
    return snapshot.text.isupper() or snapshot.label == "section_header"


def _find_table_title_hint(
    snapshots: list[ItemSnapshot], table_snapshot: ItemSnapshot
) -> str | None:
    candidates = []
    for candidate in snapshots[
        max(0, table_snapshot.index - 2) : min(len(snapshots), table_snapshot.index + 3)
    ]:
        if not _looks_like_table_title_hint(candidate):
            continue
        candidates.append(candidate)

    if not candidates:
        return None

    candidates.sort(
        key=lambda candidate: (
            abs(candidate.index - table_snapshot.index),
            _page_distance(table_snapshot, candidate),
        )
    )
    return candidates[0].text


def _combine_table_title(caption: str | None, title_hint: str | None) -> str | None:
    if caption and title_hint and title_hint.lower() not in caption.lower():
        return f"{caption} {title_hint}".strip()
    return caption or title_hint


def _heading_lookup_by_item_index(snapshots: list[ItemSnapshot]) -> dict[int, str | None]:
    current_heading: str | None = None
    headings_by_index: dict[int, str | None] = {}
    for snapshot in snapshots:
        if _is_structural_heading(snapshot):
            current_heading = snapshot.text
        headings_by_index[snapshot.index] = current_heading
    return headings_by_index


def _build_raw_table_segments(
    exported_doc: dict[str, Any],
    snapshots: list[ItemSnapshot],
    *,
    headings_by_index: dict[int, str | None],
) -> list[ParsedTableSegment]:
    table_snapshots = [snapshot for snapshot in snapshots if snapshot.label == "table"]
    raw_segments: list[ParsedTableSegment] = []

    for segment_index, (table_snapshot, exported_table) in enumerate(
        zip(table_snapshots, exported_doc.get("tables") or [], strict=False)
    ):
        table_data = exported_table.get("data") or {}
        rows = _normalize_grid_rows(table_data)
        caption = _find_nearby_caption(snapshots, table_snapshot)
        title_hint = _find_table_title_hint(snapshots, table_snapshot)
        heading = headings_by_index.get(table_snapshot.index)
        title_source = "caption"
        if caption and title_hint:
            title_source = "caption+title_hint"
        elif title_hint:
            title_source = "title_hint"
        elif not caption:
            title_source = "inferred"

        raw_segments.append(
            ParsedTableSegment(
                segment_index=segment_index,
                segment_order=table_snapshot.index,
                source_table_ref=exported_table.get("self_ref"),
                title=_combine_table_title(caption, title_hint),
                heading=heading,
                page_from=table_snapshot.page_from,
                page_to=table_snapshot.page_to,
                # Use normalized rows as the source of truth for logical-table building.
                # Docling can emit title-only placeholder table fragments with declared
                # num_rows/num_cols but an all-empty grid.
                row_count=len(rows),
                col_count=max((len(row) for row in rows), default=0),
                rows=rows,
                metadata={
                    "caption": caption,
                    "title_hint": title_hint,
                    "segment_label": table_snapshot.label,
                    "title_source": title_source,
                    "header_rows_retained": min(len(rows), 3),
                    "header_rows_removed": 0,
                    "source_artifact_sha256": _sha256_json(exported_table),
                },
            )
        )

    return raw_segments


def _meaningful_table_segments(raw_segments: list[ParsedTableSegment]) -> list[ParsedTableSegment]:
    meaningful_segments: list[ParsedTableSegment] = []
    pending_empty_segments: list[ParsedTableSegment] = []

    for segment in raw_segments:
        if not segment.rows:
            pending_empty_segments.append(segment)
            continue

        collapsible = [
            empty_segment
            for empty_segment in pending_empty_segments
            if empty_segment.heading == segment.heading and _pages_adjacent(empty_segment, segment)
        ]
        if collapsible:
            carried_page_from = min(
                (
                    empty_segment.page_from
                    for empty_segment in collapsible
                    if empty_segment.page_from is not None
                ),
                default=segment.page_from,
            )
            carried_page_to = max(
                (
                    empty_segment.page_to
                    for empty_segment in collapsible
                    if empty_segment.page_to is not None
                ),
                default=segment.page_to,
            )
            if carried_page_from is not None:
                segment.page_from = (
                    min(segment.page_from, carried_page_from)
                    if segment.page_from is not None
                    else carried_page_from
                )
            if carried_page_to is not None:
                segment.page_to = (
                    max(segment.page_to, carried_page_to)
                    if segment.page_to is not None
                    else carried_page_to
                )
            segment.metadata["collapsed_empty_segment_indices"] = [
                empty_segment.segment_index for empty_segment in collapsible
            ]

        pending_empty_segments.clear()
        meaningful_segments.append(segment)

    return meaningful_segments


def _build_figures(
    exported_doc: dict[str, Any],
    snapshots: list[ItemSnapshot],
    *,
    headings_by_index: dict[int, str | None],
) -> list[ParsedFigure]:
    picture_snapshots = [snapshot for snapshot in snapshots if snapshot.label == "picture"]
    text_lookup = _build_exported_text_lookup(exported_doc)
    figures: list[ParsedFigure] = []

    for figure_index, (picture_snapshot, exported_picture) in enumerate(
        zip(picture_snapshots, exported_doc.get("pictures") or [], strict=False)
    ):
        caption_refs = [
            ref for ref in exported_picture.get("captions") or [] if isinstance(ref, str)
        ]
        explicit_captions = [text_lookup[ref] for ref in caption_refs if ref in text_lookup]
        explicit_caption = " ".join(dict.fromkeys(explicit_captions)).strip() or None

        if explicit_caption:
            caption = explicit_caption
            caption_source = "explicit_ref"
            caption_confidence = 1.0
            caption_candidates = explicit_captions
        else:
            caption, caption_source, caption_confidence, caption_candidates = (
                _find_nearby_figure_caption(
                    snapshots,
                    picture_snapshot,
                )
            )

        annotations = exported_picture.get("annotations") or []
        source_confidence = _annotation_confidence(annotations)
        figure_confidence = (
            source_confidence if source_confidence is not None else caption_confidence
        )
        heading = headings_by_index.get(picture_snapshot.index)
        provenance = _normalize_provenance(exported_picture.get("prov"))

        figures.append(
            ParsedFigure(
                figure_index=figure_index,
                source_figure_ref=exported_picture.get("self_ref"),
                caption=caption,
                heading=heading,
                page_from=picture_snapshot.page_from,
                page_to=picture_snapshot.page_to,
                confidence=figure_confidence,
                metadata={
                    "label": exported_picture.get("label"),
                    "caption_resolution_source": caption_source,
                    "caption_candidates": caption_candidates,
                    "caption_attachment_confidence": caption_confidence,
                    "source_confidence": source_confidence,
                    "captions": caption_refs,
                    "references": exported_picture.get("references") or [],
                    "footnotes": exported_picture.get("footnotes") or [],
                    "annotations": annotations,
                    "provenance": provenance,
                    "source_artifact_sha256": _sha256_json(exported_picture),
                },
            )
        )

    return figures


def _normalized_title_key(title: str | None) -> str | None:
    if not title:
        return None
    return re.sub(r"\s+", " ", title).strip().lower()


def _pages_adjacent(left: ParsedTableSegment, right: ParsedTableSegment) -> bool:
    left_page = left.page_to or left.page_from
    right_page = right.page_from or right.page_to
    if left_page is None or right_page is None:
        return False
    return right_page - left_page <= 1


def _segment_merge_reason(previous: ParsedTableSegment, current: ParsedTableSegment) -> str | None:
    if not _pages_adjacent(previous, current):
        return None
    if previous.heading and current.heading and previous.heading != current.heading:
        return None

    previous_title = _normalized_title_key(previous.title)
    current_title = _normalized_title_key(current.title)
    if previous_title and current_title:
        if previous_title != current_title:
            return None
        if previous.col_count and current.col_count and previous.col_count != current.col_count:
            return "adjacent_same_title_heading_continuation"
        return "adjacent_matching_shape_and_title"
    if previous_title is not None and current_title is None:
        return "adjacent_titled_then_untitled_continuation"
    if previous_title is None and current_title is None:
        if previous.col_count and current.col_count and previous.col_count != current.col_count:
            return None
        return "adjacent_matching_shape_and_title"
    return None


def _should_merge_segments(previous: ParsedTableSegment, current: ParsedTableSegment) -> bool:
    return _segment_merge_reason(previous, current) is not None


def _row_key(row: list[str]) -> str:
    return " | ".join(_normalize_text(cell).lower() for cell in row).strip()


def _row_looks_like_header(row: list[str]) -> bool:
    normalized_cells = [_normalize_text(cell) for cell in row]
    populated_cells = [cell for cell in normalized_cells if cell]
    if not populated_cells:
        return False
    alpha_cells = [cell for cell in populated_cells if re.search(r"[A-Za-z]", cell)]
    if not alpha_cells:
        return False
    return len(alpha_cells) >= max(1, len(populated_cells) // 2)


def _strip_repeated_header_rows(
    existing_rows: list[list[str]], new_rows: list[list[str]]
) -> tuple[list[list[str]], int]:
    if not existing_rows or not new_rows:
        return new_rows, 0

    max_header_rows = min(3, len(existing_rows), len(new_rows))
    removed = 0
    for header_rows in range(max_header_rows, 0, -1):
        existing_prefix = [_row_key(row) for row in existing_rows[:header_rows]]
        new_prefix = [_row_key(row) for row in new_rows[:header_rows]]
        if existing_prefix == new_prefix:
            removed = header_rows
            break

    return new_rows[removed:], removed


def _build_search_text(title: str | None, heading: str | None, rows: list[list[str]]) -> str:
    parts: list[str] = []
    if title:
        parts.append(title)
    if heading:
        parts.append(heading)
    parts.extend(" | ".join(cell for cell in row if cell) for row in rows if any(row))
    return "\n".join(part for part in parts if part).strip()


def _build_preview_text(rows: list[list[str]]) -> str:
    preview_rows = [" | ".join(cell for cell in row if cell) for row in rows[:4] if any(row)]
    return "\n".join(preview_rows).strip()


def _preferred_family_title(tables: list[ParsedTable]) -> str | None:
    candidates = [title for table in tables if (title := table.title)]
    if not candidates:
        return None

    def title_score(title: str) -> tuple[int, int]:
        normalized = _normalize_text(title)
        return (0 if "continued" in normalized.lower() else 1, len(normalized))

    return max(candidates, key=title_score)


@lru_cache(maxsize=32)
def _compiled_family_key_pattern(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


@lru_cache(maxsize=32)
def _compiled_optional_pattern(pattern: str | None) -> re.Pattern[str] | None:
    if pattern is None:
        return None
    return re.compile(pattern, re.IGNORECASE)


def _canonicalize_family_key(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    if not normalized:
        return None
    normalized = re.sub(r"\s*([()[\]{}])\s*", r"\1", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.upper()


def _extract_title_regex_family_key(title: str | None, matcher: TableFamilyMatcher) -> str | None:
    normalized = _normalize_text(title)
    match = _compiled_family_key_pattern(matcher.family_key_pattern).search(normalized)
    if not match:
        return None
    explicit_family_key = match.groupdict().get("family_key") if match.groupdict() else None
    return _canonicalize_family_key(explicit_family_key or match.group(0))


def _is_family_continuation_fragment(
    normalized_title: str,
    *,
    matcher: TableFamilyMatcher,
) -> bool:
    if not normalized_title:
        return True
    if "continued" in normalized_title.lower():
        return True
    continuation_pattern = _compiled_optional_pattern(matcher.continuation_title_pattern)
    if continuation_pattern is not None and continuation_pattern.search(normalized_title):
        return True
    return not TABLE_LABEL_PATTERN.match(normalized_title)


def _group_tables_by_title_regex_family(
    tables: list[ParsedTable],
    *,
    matcher: TableFamilyMatcher,
) -> dict[str, list[ParsedTable]]:
    grouped: dict[str, list[ParsedTable]] = {}
    current_family: str | None = None
    previous_table: ParsedTable | None = None

    for table in tables:
        normalized_title = _normalize_text(table.title)
        family_key = _extract_title_regex_family_key(normalized_title, matcher)
        if family_key is None and current_family and previous_table is not None:
            same_heading = (
                table.heading == previous_table.heading if matcher.require_same_heading else True
            )
            previous_page = previous_table.page_to or previous_table.page_from
            current_page = table.page_from or table.page_to
            is_continuation_fragment = _is_family_continuation_fragment(
                normalized_title,
                matcher=matcher,
            )
            if (
                is_continuation_fragment
                and same_heading
                and previous_page is not None
                and current_page is not None
            ):
                if current_page - previous_page <= matcher.max_page_gap:
                    family_key = current_family

        if family_key is None:
            if normalized_title and TABLE_LABEL_PATTERN.match(normalized_title):
                current_family = None
            previous_table = table
            continue

        grouped.setdefault(family_key, []).append(table)
        current_family = family_key
        previous_table = table

    return grouped


def _merge_table_family(
    tables: list[ParsedTable],
    *,
    table_index: int,
    page_from: int | None = None,
    page_to: int | None = None,
    heading: str | None = None,
    segments: list[ParsedTableSegment] | None = None,
    metadata_updates: dict[str, Any] | None = None,
) -> ParsedTable:
    rows: list[list[str]] = []
    total_removed_headers = 0

    for position, table in enumerate(tables):
        table_rows = table.rows
        if position > 0:
            table_rows, removed = _strip_repeated_header_rows(rows, table_rows)
            total_removed_headers += removed
        rows.extend(table_rows)

    merged_segments = (
        segments
        if segments is not None
        else [segment for table in tables for segment in table.segments]
    )
    resolved_title = _preferred_family_title(tables)
    resolved_heading = heading or next((table.heading for table in tables if table.heading), None)
    resolved_page_from = (
        page_from
        if page_from is not None
        else min((table.page_from for table in tables if table.page_from is not None), default=None)
    )
    resolved_page_to = (
        page_to
        if page_to is not None
        else max((table.page_to for table in tables if table.page_to is not None), default=None)
    )

    metadata = dict(tables[0].metadata)
    metadata.update(
        {
            "is_merged": len(tables) > 1,
            "source_segment_count": len(merged_segments),
            "segment_count": len(merged_segments),
            "merge_reason": (
                "provisional_family_group_merge"
                if len(tables) > 1
                else metadata.get("merge_reason")
            )
            or "single_segment",
            "merge_confidence": 0.7 if len(tables) > 1 else metadata.get("merge_confidence", 1.0),
            "continuation_candidate": len(tables) > 1,
            "ambiguous_continuation_candidate": False,
            "repeated_header_rows_removed": total_removed_headers > 0,
            "header_rows_removed_count": total_removed_headers,
            "merge_sanity_passed": True,
            "header_removal_passed": True,
            "source_segment_indices": [segment.segment_index for segment in merged_segments],
            "source_titles": [table.title for table in tables if table.title],
        }
    )
    if metadata_updates:
        metadata.update(metadata_updates)

    return ParsedTable(
        table_index=table_index,
        title=resolved_title,
        heading=resolved_heading,
        page_from=resolved_page_from,
        page_to=resolved_page_to,
        row_count=len(rows),
        col_count=max((len(row) for row in rows), default=0),
        rows=rows,
        search_text=_build_search_text(resolved_title, resolved_heading, rows),
        preview_text=_build_preview_text(rows),
        metadata=metadata,
        segments=merged_segments,
    )


def _group_tables_for_supplement_matcher(
    matcher: TableFamilyMatcher,
    tables: list[ParsedTable],
) -> dict[str, list[ParsedTable]]:
    if matcher.kind == TITLE_REGEX_FAMILY_MATCHER:
        return _group_tables_by_title_regex_family(tables, matcher=matcher)
    raise ValueError(f"Unsupported table supplement matcher: {matcher.kind}")


def _apply_table_family_overlays(
    tables: list[ParsedTable],
    supplement_tables: list[ParsedTable],
    *,
    family_matcher: TableFamilyMatcher,
    overlay_type: str = "clean_pdf_family_replacement",
    supplement_filename: str,
) -> list[ParsedTable]:
    current_families = _group_tables_for_supplement_matcher(family_matcher, tables)
    supplement_families = _group_tables_for_supplement_matcher(family_matcher, supplement_tables)
    if not current_families or not supplement_families:
        return tables

    table_to_family = {
        id(table): family_key
        for family_key, family_tables in current_families.items()
        for table in family_tables
    }
    replaced_families = {
        family_key for family_key in current_families if family_key in supplement_families
    }
    if not replaced_families:
        return tables

    result: list[ParsedTable] = []
    emitted_families: set[str] = set()
    for table in tables:
        family_key = table_to_family.get(id(table))
        if family_key not in replaced_families:
            result.append(table)
            continue
        if family_key in emitted_families:
            continue

        original_family = current_families[family_key]
        supplement_family = supplement_families[family_key]
        original_segments = [segment for item in original_family for segment in item.segments]
        overlay_table = _merge_table_family(
            supplement_family,
            table_index=0,
            page_from=min(
                (item.page_from for item in original_family if item.page_from is not None),
                default=None,
            ),
            page_to=max(
                (item.page_to for item in original_family if item.page_to is not None),
                default=None,
            ),
            heading=next((item.heading for item in original_family if item.heading), None),
            segments=original_segments,
            metadata_updates={
                "overlay_applied": True,
                "overlay_type": overlay_type,
                "overlay_family_key": family_key,
                "overlay_source_filename": supplement_filename,
                "overlay_source_table_indices": [item.table_index for item in supplement_family],
                "overlay_original_table_indices": [item.table_index for item in original_family],
            },
        )
        result.append(overlay_table)
        emitted_families.add(family_key)

    return [replace(table, table_index=index) for index, table in enumerate(result)]


def _supplement_search_roots() -> list[Path]:
    settings = get_settings()
    if settings.local_ingest_allowed_roots:
        roots = [
            Path(item).expanduser().resolve()
            for item in settings.local_ingest_allowed_roots.split(":")
            if item
        ]
    else:
        roots = default_local_ingest_roots()

    deduped: list[Path] = []
    for root in roots:
        if root not in deduped:
            deduped.append(root)
    return deduped


def _resolve_table_supplement_path(
    supplement_filename: str, *, source_path: Path | None
) -> Path | None:
    candidate_paths: list[Path] = []
    if source_path is not None:
        candidate_paths.append(source_path.with_name(supplement_filename))

    for root in _supplement_search_roots():
        if not root.exists():
            continue
        direct_candidate = root / supplement_filename
        if direct_candidate.is_file():
            candidate_paths.append(direct_candidate)
        if any(path.is_file() for path in candidate_paths):
            break
        recursive_matches = list(root.rglob(supplement_filename))
        candidate_paths.extend(path for path in recursive_matches if path.is_file())
        if recursive_matches:
            break

    return next((path for path in candidate_paths if path.is_file()), None)


def _apply_registered_table_supplements(
    source_path: Path | None,
    tables: list[ParsedTable],
    *,
    source_filename: str | None = None,
    registry_rules: tuple[TableSupplementRule, ...] | None = None,
    parser: DoclingParser | None = None,
) -> list[ParsedTable]:
    resolved_rules = (
        registry_rules if registry_rules is not None else get_table_supplement_registry()
    )
    normalized_source_filename = Path(source_filename).name if source_filename else None
    result = tables

    for rule in resolved_rules:
        if not rule.matches_document(normalized_source_filename):
            continue
        supplement_path = _resolve_table_supplement_path(
            rule.supplement_filename,
            source_path=source_path,
        )
        if supplement_path is None:
            continue
        supplement_parser = parser or DoclingParser()
        supplement_tables = supplement_parser.parse_pdf(supplement_path).tables
        result = _apply_table_family_overlays(
            result,
            supplement_tables,
            family_matcher=rule.matcher,
            overlay_type=rule.overlay_type,
            supplement_filename=supplement_path.name,
        )

    return result


def _build_logical_tables(raw_segments: list[ParsedTableSegment]) -> list[ParsedTable]:
    grouped_segments: list[list[ParsedTableSegment]] = []

    for segment in raw_segments:
        if grouped_segments and _should_merge_segments(grouped_segments[-1][-1], segment):
            grouped_segments[-1].append(segment)
        else:
            grouped_segments.append([segment])

    tables: list[ParsedTable] = []
    for table_index, segments in enumerate(grouped_segments):
        rows: list[list[str]] = []
        total_removed_headers = 0
        for position, segment in enumerate(segments):
            segment_rows = segment.rows
            if position > 0:
                segment_rows, removed = _strip_repeated_header_rows(rows, segment_rows)
                total_removed_headers += removed
                segment.metadata["header_rows_removed"] = removed
                segment.metadata["header_rows_retained"] = max(
                    len(segment.rows[: min(len(segment.rows), 3)]) - removed, 0
                )
            rows.extend(segment_rows)

        title = next((segment.title for segment in segments if segment.title), None)
        heading = next((segment.heading for segment in segments if segment.heading), None)
        page_from = min(
            (segment.page_from for segment in segments if segment.page_from is not None),
            default=None,
        )
        page_to = max(
            (segment.page_to for segment in segments if segment.page_to is not None), default=None
        )
        row_count = len(rows)
        col_count = max(
            (len(row) for row in rows),
            default=max((segment.col_count for segment in segments), default=0),
        )

        repeated_header_found = False
        if len(segments) > 1 and rows:
            first_row_key = _row_key(rows[0])
            repeated_header_found = _row_looks_like_header(rows[0]) and any(
                _row_key(row) == first_row_key for row in rows[1 : min(len(rows), 6)]
            )

        metadata = {
            "is_merged": len(segments) > 1,
            "source_segment_count": len(segments),
            "segment_count": len(segments),
            "merge_reason": (
                "|".join(
                    dict.fromkeys(
                        _segment_merge_reason(left, right) or "unknown"
                        for left, right in zip(segments, segments[1:], strict=False)
                    )
                )
                if len(segments) > 1
                else "single_segment"
            ),
            "merge_confidence": (
                0.8
                if any(
                    (left.col_count and right.col_count and left.col_count != right.col_count)
                    for left, right in zip(segments, segments[1:], strict=False)
                )
                else 0.95
            )
            if len(segments) > 1
            else 1.0,
            "continuation_candidate": len(segments) > 1,
            "ambiguous_continuation_candidate": False,
            "repeated_header_rows_removed": total_removed_headers > 0,
            "header_rows_removed_count": total_removed_headers,
            "title_resolution_source": segments[0].metadata.get("title_source"),
            "merge_sanity_passed": True,
            "header_removal_passed": not repeated_header_found,
            "source_segment_indices": [segment.segment_index for segment in segments],
            "source_titles": [segment.title for segment in segments if segment.title],
        }

        tables.append(
            ParsedTable(
                table_index=table_index,
                title=title,
                heading=heading,
                page_from=page_from,
                page_to=page_to,
                row_count=row_count,
                col_count=col_count,
                rows=rows,
                search_text=_build_search_text(title, heading, rows),
                preview_text=_build_preview_text(rows),
                metadata=metadata,
                segments=segments,
            )
        )

    return tables


def _annotate_ambiguous_continuations(
    raw_segments: list[ParsedTableSegment], tables: list[ParsedTable]
) -> None:
    segment_to_table = {
        segment.segment_index: table for table in tables for segment in table.segments
    }
    for left, right in zip(raw_segments, raw_segments[1:], strict=False):
        if not _pages_adjacent(left, right):
            continue
        if left.heading != right.heading:
            continue
        left_table = segment_to_table.get(left.segment_index)
        right_table = segment_to_table.get(right.segment_index)
        if left_table is None or right_table is None:
            continue
        if left_table.table_index == right_table.table_index:
            continue
        left_table.metadata["ambiguous_continuation_candidate"] = True
        right_table.metadata["ambiguous_continuation_candidate"] = True
        left_table.metadata["merge_reason"] = (
            left_table.metadata.get("merge_reason") or "split_due_to_ambiguity"
        )
        right_table.metadata["merge_reason"] = (
            right_table.metadata.get("merge_reason") or "split_due_to_ambiguity"
        )


def _validate_table_merge_assignments(
    raw_segments: list[ParsedTableSegment], tables: list[ParsedTable]
) -> None:
    segment_to_table: dict[int, int] = {}
    for table in tables:
        for segment in table.segments:
            segment_to_table[segment.segment_index] = table.table_index

    for left, right in zip(raw_segments, raw_segments[1:], strict=False):
        if _should_merge_segments(left, right) and segment_to_table.get(
            left.segment_index
        ) != segment_to_table.get(right.segment_index):
            raise ValueError(
                "Detected a continued table segment that was not merged "
                "into the same logical table."
            )


class DoclingParser:
    def __init__(
        self,
        converter: DocumentConverter | None = None,
        fallback_converter: DocumentConverter | None = None,
        timeout_rescue_converter: DocumentConverter | None = None,
    ) -> None:
        self.converter = converter or get_document_converter()
        self.fallback_converter = fallback_converter or get_fallback_document_converter()
        self.timeout_rescue_converter = (
            timeout_rescue_converter or get_timeout_rescue_document_converter()
        )

    def parse_pdf(self, source_path: Path, *, source_filename: str | None = None) -> ParsedDocument:
        result = self.converter.convert(source_path, raises_on_error=False)
        if not _conversion_succeeded(result):
            primary_result = result
            fallback_result = self.fallback_converter.convert(source_path, raises_on_error=False)
            result = fallback_result
            if _should_attempt_timeout_rescue(primary_result, fallback_result):
                result = self.timeout_rescue_converter.convert(source_path, raises_on_error=False)
            if not _conversion_succeeded(result):
                raise ValueError(
                    _conversion_error_message(
                        result,
                        source_path=source_path,
                        attempted_fallback=True,
                    )
                )
        document = result.document
        page_count = document.num_pages()
        exported_doc = document.export_to_dict()
        snapshots = _snapshot_items(document)
        headings_by_index = _heading_lookup_by_item_index(snapshots)
        chunks = _normalize_chunks(snapshots)
        title_fallback_name = Path(source_filename).stem if source_filename else document.name
        title = _infer_document_title(chunks, title_fallback_name)
        if not chunks and title != "Untitled document":
            chunks = [_synthetic_title_chunk(title, page_count=page_count)]
        raw_segments = _build_raw_table_segments(
            exported_doc,
            snapshots,
            headings_by_index=headings_by_index,
        )
        meaningful_segments = _meaningful_table_segments(raw_segments)
        tables = _build_logical_tables(meaningful_segments)
        _annotate_ambiguous_continuations(meaningful_segments, tables)
        _validate_table_merge_assignments(meaningful_segments, tables)
        tables = _apply_registered_table_supplements(
            source_path,
            tables,
            source_filename=source_filename
            or (source_path.name if source_path is not None else None),
        )
        figures = _build_figures(
            exported_doc,
            snapshots,
            headings_by_index=headings_by_index,
        )

        yaml_text = yaml.safe_dump(exported_doc, sort_keys=False, allow_unicode=True)
        docling_json = json.dumps(exported_doc, indent=2)

        return ParsedDocument(
            title=title,
            page_count=page_count,
            yaml_text=yaml_text,
            docling_json=docling_json,
            chunks=chunks,
            tables=tables,
            raw_table_segments=raw_segments,
            figures=figures,
        )
