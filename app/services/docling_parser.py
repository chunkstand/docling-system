from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from docling.document_converter import DocumentConverter

HEADING_PATTERN = re.compile(r"^(Chapter\s+\d+|Part\s+[IVXLC]+|[0-9]+(?:\.[0-9]+)*\s)")
TABLE_LABEL_PATTERN = re.compile(r"^TABLE\s+[0-9A-Z().-]+", re.IGNORECASE)
TABLE_ARTIFACT_SCHEMA_VERSION = "1.0"
FIGURE_ARTIFACT_SCHEMA_VERSION = "1.0"


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
        artifact_sha256: str,
    ) -> dict[str, Any]:
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
            "artifact_sha256": artifact_sha256,
            "created_at": created_at,
            "search_text": self.search_text,
            "preview_text": self.preview_text,
            "metadata": self.metadata,
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
        artifact_sha256: str,
    ) -> dict[str, Any]:
        return {
            "schema_version": FIGURE_ARTIFACT_SCHEMA_VERSION,
            "document_id": document_id,
            "run_id": run_id,
            "figure_id": figure_id,
            "figure_index": self.figure_index,
            "page_from": self.page_from,
            "page_to": self.page_to,
            "artifact_sha256": artifact_sha256,
            "created_at": created_at,
            "source_figure_ref": self.source_figure_ref,
            "caption": self.caption,
            "heading": self.heading,
            "confidence": self.confidence,
            "metadata": self.metadata,
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


@lru_cache(maxsize=1)
def get_document_converter() -> DocumentConverter:
    return DocumentConverter()


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
    return " ".join((value or "").split()).strip()


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


def _structural_heading_at(snapshots: list[ItemSnapshot], item_index: int) -> str | None:
    for snapshot in reversed(snapshots[: item_index + 1]):
        if _is_structural_heading(snapshot):
            return snapshot.text
    return None


def _build_raw_table_segments(
    exported_doc: dict[str, Any], snapshots: list[ItemSnapshot]
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
        heading = _structural_heading_at(snapshots, table_snapshot.index)
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
                row_count=int(table_data.get("num_rows") or len(rows)),
                col_count=int(
                    table_data.get("num_cols") or max((len(row) for row in rows), default=0)
                ),
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


def _build_figures(
    exported_doc: dict[str, Any], snapshots: list[ItemSnapshot]
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
        heading = _structural_heading_at(snapshots, picture_snapshot.index)
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
            repeated_header_found = any(
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
        segment.segment_index: table.table_index for table in tables for segment in table.segments
    }
    for left, right in zip(raw_segments, raw_segments[1:], strict=False):
        if not _pages_adjacent(left, right):
            continue
        if left.heading != right.heading:
            continue
        if segment_to_table.get(left.segment_index) == segment_to_table.get(right.segment_index):
            continue
        left_table = next(
            table
            for table in tables
            if any(seg.segment_index == left.segment_index for seg in table.segments)
        )
        right_table = next(
            table
            for table in tables
            if any(seg.segment_index == right.segment_index for seg in table.segments)
        )
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
    def __init__(self, converter: DocumentConverter | None = None) -> None:
        self.converter = converter or get_document_converter()

    def parse_pdf(self, source_path: Path) -> ParsedDocument:
        result = self.converter.convert(source_path)
        document = result.document
        exported_doc = document.export_to_dict()
        snapshots = _snapshot_items(document)
        chunks = _normalize_chunks(snapshots)
        raw_segments = _build_raw_table_segments(exported_doc, snapshots)
        tables = _build_logical_tables(raw_segments)
        _annotate_ambiguous_continuations(raw_segments, tables)
        _validate_table_merge_assignments(raw_segments, tables)
        figures = _build_figures(exported_doc, snapshots)

        yaml_text = yaml.safe_dump(exported_doc, sort_keys=False, allow_unicode=True)
        docling_json = json.dumps(exported_doc, indent=2)
        title = (
            next((chunk.heading for chunk in chunks if chunk.heading), None)
            or document.name
        )

        return ParsedDocument(
            title=title,
            page_count=document.num_pages(),
            yaml_text=yaml_text,
            docling_json=docling_json,
            chunks=chunks,
            tables=tables,
            raw_table_segments=raw_segments,
            figures=figures,
        )
