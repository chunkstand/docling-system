from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Document, DocumentChunk, DocumentFigure, DocumentRun, DocumentTable
from app.services.docling_parser import ParsedDocument, ParsedFigure, ParsedTable


@dataclass
class ValidationReport:
    passed: bool
    summary: str
    details: dict


def _table_validation_result(table: ParsedTable, json_path: Path, yaml_path: Path) -> dict:
    row_count_sane = table.row_count > 0 and table.col_count > 0
    search_text_present = bool(table.search_text.strip())
    preview_text_present = bool(table.preview_text.strip())
    merge_sanity_passed = bool(table.metadata.get("merge_sanity_passed"))
    header_removal_passed = bool(table.metadata.get("header_removal_passed"))

    return {
        "table_index": table.table_index,
        "title": table.title,
        "json_artifact_exists": json_path.exists(),
        "yaml_artifact_exists": yaml_path.exists(),
        "search_text_present": search_text_present,
        "preview_text_present": preview_text_present,
        "row_count_sane": row_count_sane,
        "continued_table_merge_sane": merge_sanity_passed,
        "repeated_header_row_removal_sane": header_removal_passed,
    }


def _figure_validation_result(figure: ParsedFigure, json_path: Path, yaml_path: Path) -> dict:
    metadata = figure.metadata
    provenance = metadata.get("provenance") or []
    return {
        "figure_index": figure.figure_index,
        "source_figure_ref": figure.source_figure_ref,
        "json_artifact_exists": json_path.exists(),
        "yaml_artifact_exists": yaml_path.exists(),
        "provenance_present": bool(provenance),
        "caption_resolution_source_present": "caption_resolution_source" in metadata,
        "confidence_field_present": "caption_attachment_confidence" in metadata
        and "source_confidence" in metadata,
    }


def validate_persisted_run(
    session: Session,
    document: Document,
    run: DocumentRun,
    parsed: ParsedDocument,
) -> ValidationReport:
    persisted_chunk_count = session.execute(
        select(func.count()).select_from(DocumentChunk).where(DocumentChunk.run_id == run.id)
    ).scalar_one()
    persisted_table_count = session.execute(
        select(func.count()).select_from(DocumentTable).where(DocumentTable.run_id == run.id)
    ).scalar_one()
    persisted_figure_count = session.execute(
        select(func.count()).select_from(DocumentFigure).where(DocumentFigure.run_id == run.id)
    ).scalar_one()

    document_checks = {
        "docling_json_exists": bool(run.docling_json_path and Path(run.docling_json_path).exists()),
        "yaml_exists": bool(run.yaml_path and Path(run.yaml_path).exists()),
        "chunk_count_matches": persisted_chunk_count == len(parsed.chunks),
        "title_present": bool(parsed.title),
        "page_count_sane": 0 < parsed.page_count <= get_settings().local_ingest_max_pages,
    }

    table_details: list[dict] = []
    figure_details: list[dict] = []
    table_checks = {
        "detected_count_matches_persisted": persisted_table_count == len(parsed.tables),
    }
    figure_checks = {
        "detected_count_matches_persisted": persisted_figure_count == len(parsed.figures),
    }

    persisted_tables = (
        session.execute(
            select(DocumentTable)
            .where(DocumentTable.run_id == run.id)
            .order_by(DocumentTable.table_index)
        )
        .scalars()
        .all()
    )
    persisted_figures = (
        session.execute(
            select(DocumentFigure)
            .where(DocumentFigure.run_id == run.id)
            .order_by(DocumentFigure.figure_index)
        )
        .scalars()
        .all()
    )

    for parsed_table, persisted_table in zip(parsed.tables, persisted_tables, strict=False):
        json_path = Path(persisted_table.json_path) if persisted_table.json_path else Path()
        yaml_path = Path(persisted_table.yaml_path) if persisted_table.yaml_path else Path()
        detail = _table_validation_result(parsed_table, json_path, yaml_path)
        table_details.append(detail)

    table_checks["all_table_checks_passed"] = all(
        all(
            detail[key]
            for key in (
                "json_artifact_exists",
                "yaml_artifact_exists",
                "search_text_present",
                "preview_text_present",
                "row_count_sane",
                "continued_table_merge_sane",
                "repeated_header_row_removal_sane",
            )
        )
        for detail in table_details
    )

    for parsed_figure, persisted_figure in zip(parsed.figures, persisted_figures, strict=False):
        json_path = Path(persisted_figure.json_path) if persisted_figure.json_path else Path()
        yaml_path = Path(persisted_figure.yaml_path) if persisted_figure.yaml_path else Path()
        figure_details.append(_figure_validation_result(parsed_figure, json_path, yaml_path))

    figure_checks["all_figure_checks_passed"] = all(
        all(
            detail[key]
            for key in (
                "json_artifact_exists",
                "yaml_artifact_exists",
                "provenance_present",
                "caption_resolution_source_present",
                "confidence_field_present",
            )
        )
        for detail in figure_details
    )

    passed = (
        all(document_checks.values()) and all(table_checks.values()) and all(figure_checks.values())
    )
    summary = "Validation passed." if passed else "Validation failed."
    details = {
        "document_checks": document_checks,
        "table_checks": table_checks,
        "table_details": table_details,
        "figure_checks": figure_checks,
        "figure_details": figure_details,
        "document_id": str(document.id),
        "run_id": str(run.id),
    }
    return ValidationReport(passed=passed, summary=summary, details=details)
