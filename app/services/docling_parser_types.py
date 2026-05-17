from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
