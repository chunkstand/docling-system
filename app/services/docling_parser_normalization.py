from __future__ import annotations

import hashlib
import json
from typing import Any

from app.services.docling_parser_types import (
    HEADING_PATTERN,
    TABLE_LABEL_PATTERN,
    ItemSnapshot,
    ParsedChunk,
    ParsedFigure,
    ParsedTableSegment,
)


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

def _pages_adjacent(left: ParsedTableSegment, right: ParsedTableSegment) -> bool:
    left_page = left.page_to or left.page_from
    right_page = right.page_from or right.page_to
    if left_page is None or right_page is None:
        return False
    return right_page - left_page <= 1
