from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import yaml
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

import app.services.docling_parser_types as _docling_parser_types
from app.core.config import get_settings
from app.services import docling_parser_conversion as _docling_parser_conversion
from app.services import docling_parser_normalization as _docling_parser_normalization
from app.services import docling_parser_tables as _docling_parser_tables

FIGURE_ARTIFACT_SCHEMA_VERSION = _docling_parser_types.FIGURE_ARTIFACT_SCHEMA_VERSION
TABLE_ARTIFACT_SCHEMA_VERSION = _docling_parser_types.TABLE_ARTIFACT_SCHEMA_VERSION
ParsedChunk = _docling_parser_types.ParsedChunk
ParsedDocument = _docling_parser_types.ParsedDocument
ParsedFigure = _docling_parser_types.ParsedFigure
ParsedTable = _docling_parser_types.ParsedTable
ParsedTableSegment = _docling_parser_types.ParsedTableSegment
TableFamilyMatcher = _docling_parser_types.TableFamilyMatcher
TableSupplementRule = _docling_parser_types.TableSupplementRule
_snapshot_items = _docling_parser_normalization._snapshot_items
_normalize_chunks = _docling_parser_normalization._normalize_chunks
_meaningful_table_segments = _docling_parser_normalization._meaningful_table_segments
_load_table_supplement_registry = _docling_parser_conversion._load_table_supplement_registry
_group_tables_by_title_regex_family = _docling_parser_tables._group_tables_by_title_regex_family
_apply_table_family_overlays = _docling_parser_tables._apply_table_family_overlays
_build_logical_tables = _docling_parser_tables._build_logical_tables
_resolve_table_supplement_path = _docling_parser_tables._resolve_table_supplement_path


def _apply_registered_table_supplements(
    source_path: Path | None,
    tables: list[ParsedTable],
    *,
    source_filename: str | None = None,
    registry_rules: tuple[TableSupplementRule, ...] | None = None,
    parser=None,
) -> list[ParsedTable]:
    resolved_rules = (
        registry_rules
        if registry_rules is not None
        else _docling_parser_tables.get_table_supplement_registry()
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
        if not _docling_parser_conversion._conversion_succeeded(result):
            primary_result = result
            fallback_result = self.fallback_converter.convert(source_path, raises_on_error=False)
            result = fallback_result
            if _docling_parser_conversion._should_attempt_timeout_rescue(
                primary_result, fallback_result
            ):
                result = self.timeout_rescue_converter.convert(source_path, raises_on_error=False)
            if not _docling_parser_conversion._conversion_succeeded(result):
                raise ValueError(
                    _docling_parser_conversion._conversion_error_message(
                        result,
                        source_path=source_path,
                        attempted_fallback=True,
                    )
                )
        document = result.document
        page_count = document.num_pages()
        exported_doc = document.export_to_dict()
        snapshots = _docling_parser_normalization._snapshot_items(document)
        headings_by_index = _docling_parser_normalization._heading_lookup_by_item_index(snapshots)
        chunks = _docling_parser_normalization._normalize_chunks(snapshots)
        title_fallback_name = Path(source_filename).stem if source_filename else document.name
        title = _docling_parser_conversion._infer_document_title(chunks, title_fallback_name)
        if not chunks and title != "Untitled document":
            chunks = [
                _docling_parser_conversion._synthetic_title_chunk(title, page_count=page_count)
            ]
        raw_segments = _docling_parser_normalization._build_raw_table_segments(
            exported_doc,
            snapshots,
            headings_by_index=headings_by_index,
        )
        meaningful_segments = _docling_parser_normalization._meaningful_table_segments(raw_segments)
        tables = _docling_parser_tables._build_logical_tables(meaningful_segments)
        _docling_parser_tables._annotate_ambiguous_continuations(meaningful_segments, tables)
        _docling_parser_tables._validate_table_merge_assignments(meaningful_segments, tables)
        tables = _apply_registered_table_supplements(
            source_path,
            tables,
            source_filename=source_filename
            or (source_path.name if source_path is not None else None),
        )
        figures = _docling_parser_normalization._build_figures(
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
