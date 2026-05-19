from __future__ import annotations

import re
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Any

import app.services.docling_parser_normalization as _docling_parser_normalization
from app.core.config import default_local_ingest_roots, get_settings
from app.services.docling_parser_types import (
    TABLE_LABEL_PATTERN,
    TITLE_REGEX_FAMILY_MATCHER,
    ParsedTable,
    ParsedTableSegment,
    TableFamilyMatcher,
)


def _normalized_title_key(title: str | None) -> str | None:
    if not title:
        return None
    return re.sub(r"\s+", " ", title).strip().lower()


def _segment_merge_reason(previous: ParsedTableSegment, current: ParsedTableSegment) -> str | None:
    if not _docling_parser_normalization._pages_adjacent(previous, current):
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
    return " | ".join(
        _docling_parser_normalization._normalize_text(cell).lower() for cell in row
    ).strip()


def _row_looks_like_header(row: list[str]) -> bool:
    normalized_cells = [
        _docling_parser_normalization._normalize_text(cell) for cell in row
    ]
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
        normalized = _docling_parser_normalization._normalize_text(title)
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
    normalized = _docling_parser_normalization._normalize_text(value)
    if not normalized:
        return None
    normalized = re.sub(r"\s*([()[\]{}])\s*", r"\1", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.upper()


def _extract_title_regex_family_key(title: str | None, matcher: TableFamilyMatcher) -> str | None:
    normalized = _docling_parser_normalization._normalize_text(title)
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
        normalized_title = _docling_parser_normalization._normalize_text(table.title)
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
        if not _docling_parser_normalization._pages_adjacent(left, right):
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
