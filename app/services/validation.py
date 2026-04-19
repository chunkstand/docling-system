from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentFigure,
    DocumentRun,
    DocumentTable,
    DocumentTableSegment,
)
from app.services.docling_parser import (
    FIGURE_ARTIFACT_SCHEMA_VERSION,
    TABLE_ARTIFACT_SCHEMA_VERSION,
    ParsedDocument,
    ParsedFigure,
    ParsedTable,
)


@dataclass
class ValidationReport:
    passed: bool
    summary: str
    details: dict
    warning_count: int = 0


def _table_has_ambiguous_structure(table: ParsedTable) -> bool:
    metadata = table.metadata
    return (
        bool(metadata.get("ambiguous_continuation_candidate"))
        or float(metadata.get("merge_confidence") or 1.0) < 0.9
    )


def _table_validation_findings(table: ParsedTable, detail: dict) -> tuple[list[dict], list[dict]]:
    warnings: list[dict] = []
    blocking_failures: list[dict] = []
    for check_name in (
        "continued_table_merge_sane",
        "repeated_header_row_removal_sane",
    ):
        if detail[check_name]:
            continue
        finding = {
            "scope": "table",
            "table_index": table.table_index,
            "title": table.title,
            "check": check_name,
        }
        if _table_has_ambiguous_structure(table):
            warnings.append({**finding, "severity": "warning"})
        else:
            blocking_failures.append({**finding, "severity": "error"})
    return warnings, blocking_failures


def _embeddings_match(
    persisted_embedding: list[float] | None,
    parsed_embedding: list[float] | None,
) -> bool:
    if parsed_embedding is None:
        return persisted_embedding is None
    if persisted_embedding is None:
        return False
    return list(persisted_embedding) == list(parsed_embedding)


def _artifact_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    return {key: value for key, value in metadata.items() if key != "audit"}


def _normalize_artifact_payload(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload
    normalized = dict(payload)
    normalized.pop("artifact_sha256", None)
    return normalized


def _load_json_artifact(path: Path) -> object | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _load_yaml_artifact(path: Path) -> object | None:
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError):
        return None


def _json_artifact_matches_expected(path: Path, expected_payload: object) -> bool:
    actual_payload = _normalize_artifact_payload(_load_json_artifact(path))
    return actual_payload == expected_payload


def _yaml_artifact_matches_expected(path: Path, expected_payload: object) -> bool:
    actual_payload = _normalize_artifact_payload(_load_yaml_artifact(path))
    return actual_payload == expected_payload


def _serialized_json_matches(path: Path, expected_text: str) -> bool:
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text()) == json.loads(expected_text)
    except (OSError, json.JSONDecodeError):
        try:
            return path.read_text() == expected_text
        except OSError:
            return False


def _serialized_yaml_matches(path: Path, expected_text: str) -> bool:
    if not path.exists():
        return False
    try:
        return yaml.safe_load(path.read_text()) == yaml.safe_load(expected_text)
    except (OSError, yaml.YAMLError):
        try:
            return path.read_text() == expected_text
        except OSError:
            return False


def _file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _artifact_hash_matches(path: Path, expected_sha256: str | None) -> bool:
    if not expected_sha256:
        return False
    return _file_sha256(path) == expected_sha256


def _expected_table_artifact_payload(table: ParsedTable, persisted_table: object) -> dict[str, Any]:
    return {
        "schema_version": TABLE_ARTIFACT_SCHEMA_VERSION,
        "document_id": str(persisted_table.document_id),
        "run_id": str(persisted_table.run_id),
        "table_id": str(persisted_table.id),
        "table_index": table.table_index,
        "logical_table_key": persisted_table.logical_table_key,
        "title": table.title,
        "heading": table.heading,
        "page_from": table.page_from,
        "page_to": table.page_to,
        "row_count": table.row_count,
        "col_count": table.col_count,
        "created_at": persisted_table.created_at.isoformat(),
        "search_text": table.search_text,
        "preview_text": table.preview_text,
        "metadata": _artifact_metadata(table.metadata),
        "rows": table.rows,
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
            for segment in table.segments
        ],
    }


def _expected_figure_artifact_payload(
    figure: ParsedFigure, persisted_figure: object
) -> dict[str, Any]:
    return {
        "schema_version": FIGURE_ARTIFACT_SCHEMA_VERSION,
        "document_id": str(persisted_figure.document_id),
        "run_id": str(persisted_figure.run_id),
        "figure_id": str(persisted_figure.id),
        "figure_index": figure.figure_index,
        "page_from": figure.page_from,
        "page_to": figure.page_to,
        "created_at": persisted_figure.created_at.isoformat(),
        "source_figure_ref": figure.source_figure_ref,
        "caption": figure.caption,
        "heading": figure.heading,
        "confidence": figure.confidence,
        "metadata": _artifact_metadata(figure.metadata),
    }


def _table_segments_match(
    table: ParsedTable,
    persisted_segments: list[object],
) -> bool:
    expected_segments = [
        {
            "segment_index": segment.segment_index,
            "source_table_ref": segment.source_table_ref,
            "page_from": segment.page_from,
            "page_to": segment.page_to,
            "segment_order": segment.segment_order,
            "metadata": segment.metadata,
        }
        for segment in table.segments
    ]
    actual_segments = [
        {
            "segment_index": segment.segment_index,
            "source_table_ref": segment.source_table_ref,
            "page_from": segment.page_from,
            "page_to": segment.page_to,
            "segment_order": segment.segment_order,
            "metadata": segment.metadata_json,
        }
        for segment in persisted_segments
    ]
    return actual_segments == expected_segments


def _table_validation_result(
    table: ParsedTable,
    persisted_table: object,
    persisted_segments: list[object],
    json_path: Path,
    yaml_path: Path,
) -> dict:
    row_count_sane = table.row_count > 0 and table.col_count > 0
    search_text_present = bool(table.search_text.strip())
    preview_text_present = bool(table.preview_text.strip())
    merge_sanity_passed = bool(table.metadata.get("merge_sanity_passed"))
    header_removal_passed = bool(table.metadata.get("header_removal_passed"))
    expected_payload = _expected_table_artifact_payload(table, persisted_table)
    audit_metadata = (persisted_table.metadata_json or {}).get("audit") or {}

    return {
        "table_index": table.table_index,
        "title": table.title,
        "json_artifact_exists": json_path.exists(),
        "yaml_artifact_exists": yaml_path.exists(),
        "db_fields_match": all(
            (
                persisted_table.table_index == table.table_index,
                persisted_table.title == table.title,
                persisted_table.heading == table.heading,
                persisted_table.page_from == table.page_from,
                persisted_table.page_to == table.page_to,
                persisted_table.row_count == table.row_count,
                persisted_table.col_count == table.col_count,
                persisted_table.search_text == table.search_text,
                persisted_table.preview_text == table.preview_text,
                (persisted_table.metadata_json or {}) == (table.metadata or {}),
                _embeddings_match(persisted_table.embedding, table.embedding),
            )
        ),
        "segments_match": _table_segments_match(table, persisted_segments),
        "search_text_present": search_text_present,
        "preview_text_present": preview_text_present,
        "row_count_sane": row_count_sane,
        "json_artifact_hash_matches": _artifact_hash_matches(
            json_path,
            audit_metadata.get("json_artifact_sha256"),
        ),
        "yaml_artifact_hash_matches": _artifact_hash_matches(
            yaml_path,
            audit_metadata.get("yaml_artifact_sha256"),
        ),
        "json_artifact_content_matches": _json_artifact_matches_expected(json_path, expected_payload),
        "yaml_artifact_content_matches": _yaml_artifact_matches_expected(yaml_path, expected_payload),
        "continued_table_merge_sane": merge_sanity_passed,
        "repeated_header_row_removal_sane": header_removal_passed,
    }


def _figure_validation_result(
    figure: ParsedFigure,
    persisted_figure: object,
    json_path: Path,
    yaml_path: Path,
) -> dict:
    metadata = figure.metadata
    provenance = metadata.get("provenance") or []
    expected_payload = _expected_figure_artifact_payload(figure, persisted_figure)
    audit_metadata = (persisted_figure.metadata_json or {}).get("audit") or {}
    return {
        "figure_index": figure.figure_index,
        "source_figure_ref": figure.source_figure_ref,
        "json_artifact_exists": json_path.exists(),
        "yaml_artifact_exists": yaml_path.exists(),
        "db_fields_match": all(
            (
                persisted_figure.figure_index == figure.figure_index,
                persisted_figure.source_figure_ref == figure.source_figure_ref,
                persisted_figure.caption == figure.caption,
                persisted_figure.heading == figure.heading,
                persisted_figure.page_from == figure.page_from,
                persisted_figure.page_to == figure.page_to,
                persisted_figure.confidence == figure.confidence,
                (persisted_figure.metadata_json or {}) == (figure.metadata or {}),
            )
        ),
        "provenance_present": bool(provenance),
        "caption_resolution_source_present": "caption_resolution_source" in metadata,
        "confidence_field_present": "caption_attachment_confidence" in metadata
        and "source_confidence" in metadata,
        "json_artifact_hash_matches": _artifact_hash_matches(
            json_path,
            audit_metadata.get("json_artifact_sha256"),
        ),
        "yaml_artifact_hash_matches": _artifact_hash_matches(
            yaml_path,
            audit_metadata.get("yaml_artifact_sha256"),
        ),
        "json_artifact_content_matches": _json_artifact_matches_expected(json_path, expected_payload),
        "yaml_artifact_content_matches": _yaml_artifact_matches_expected(yaml_path, expected_payload),
    }


def validate_persisted_run(
    session: Session,
    document: Document,
    run: DocumentRun,
    parsed: ParsedDocument,
) -> ValidationReport:
    docling_json_path = Path(run.docling_json_path) if run.docling_json_path else Path()
    yaml_path = Path(run.yaml_path) if run.yaml_path else Path()
    persisted_chunk_count = session.execute(
        select(func.count()).select_from(DocumentChunk).where(DocumentChunk.run_id == run.id)
    ).scalar_one()
    persisted_table_count = session.execute(
        select(func.count()).select_from(DocumentTable).where(DocumentTable.run_id == run.id)
    ).scalar_one()
    persisted_figure_count = session.execute(
        select(func.count()).select_from(DocumentFigure).where(DocumentFigure.run_id == run.id)
    ).scalar_one()
    persisted_chunks = (
        session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.run_id == run.id)
            .order_by(DocumentChunk.chunk_index)
        )
        .scalars()
        .all()
    )

    document_checks = {
        "docling_json_exists": bool(run.docling_json_path and docling_json_path.exists()),
        "yaml_exists": bool(run.yaml_path and yaml_path.exists()),
        "docling_json_matches": _serialized_json_matches(docling_json_path, parsed.docling_json),
        "yaml_matches": _serialized_yaml_matches(yaml_path, parsed.yaml_text),
        "chunk_count_matches": persisted_chunk_count == len(parsed.chunks),
        "title_present": bool(parsed.title),
        "page_count_sane": 0 < parsed.page_count <= get_settings().local_ingest_max_pages,
    }

    chunk_details: list[dict] = []
    table_details: list[dict] = []
    figure_details: list[dict] = []
    warnings: list[dict] = []
    blocking_failures: list[dict] = []
    chunk_checks = {
        "detected_count_matches_persisted": persisted_chunk_count == len(parsed.chunks),
    }
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
    persisted_segments = (
        session.execute(
            select(DocumentTableSegment)
            .where(DocumentTableSegment.run_id == run.id)
            .order_by(DocumentTableSegment.table_id, DocumentTableSegment.segment_index)
        )
        .scalars()
        .all()
    )
    persisted_segments_by_table_id: dict[object, list[object]] = {}
    for segment in persisted_segments:
        persisted_segments_by_table_id.setdefault(segment.table_id, []).append(segment)
    persisted_figures = (
        session.execute(
            select(DocumentFigure)
            .where(DocumentFigure.run_id == run.id)
            .order_by(DocumentFigure.figure_index)
        )
        .scalars()
        .all()
    )

    for parsed_chunk, persisted_chunk in zip(parsed.chunks, persisted_chunks, strict=False):
        chunk_details.append(
            {
                "chunk_index": parsed_chunk.chunk_index,
                "text_matches": persisted_chunk.text == parsed_chunk.text,
                "heading_matches": persisted_chunk.heading == parsed_chunk.heading,
                "page_from_matches": persisted_chunk.page_from == parsed_chunk.page_from,
                "page_to_matches": persisted_chunk.page_to == parsed_chunk.page_to,
                "metadata_matches": (persisted_chunk.metadata_json or {})
                == (parsed_chunk.metadata or {}),
                "embedding_matches": _embeddings_match(
                    persisted_chunk.embedding,
                    parsed_chunk.embedding,
                ),
            }
        )
    chunk_checks["all_chunk_checks_passed"] = all(
        all(
            detail[key]
            for key in (
                "text_matches",
                "heading_matches",
                "page_from_matches",
                "page_to_matches",
                "metadata_matches",
                "embedding_matches",
            )
        )
        for detail in chunk_details
    )

    for parsed_table, persisted_table in zip(parsed.tables, persisted_tables, strict=False):
        json_path = Path(persisted_table.json_path) if persisted_table.json_path else Path()
        yaml_path = Path(persisted_table.yaml_path) if persisted_table.yaml_path else Path()
        detail = _table_validation_result(
            parsed_table,
            persisted_table,
            persisted_segments_by_table_id.get(persisted_table.id, []),
            json_path,
            yaml_path,
        )
        table_warnings, table_failures = _table_validation_findings(parsed_table, detail)
        detail["warning_checks"] = [finding["check"] for finding in table_warnings]
        detail["blocking_failure_checks"] = [finding["check"] for finding in table_failures]
        table_details.append(detail)
        warnings.extend(table_warnings)
        blocking_failures.extend(table_failures)

    table_checks["all_table_checks_passed"] = all(
        all(
            detail[key]
            for key in (
                "json_artifact_exists",
                "yaml_artifact_exists",
                "db_fields_match",
                "segments_match",
                "search_text_present",
                "preview_text_present",
                "row_count_sane",
                "json_artifact_hash_matches",
                "yaml_artifact_hash_matches",
                "json_artifact_content_matches",
                "yaml_artifact_content_matches",
            )
        )
        and not detail["blocking_failure_checks"]
        for detail in table_details
    )
    table_checks["warning_count"] = len(warnings)
    table_checks["blocking_failure_count"] = len(blocking_failures)

    for parsed_figure, persisted_figure in zip(parsed.figures, persisted_figures, strict=False):
        json_path = Path(persisted_figure.json_path) if persisted_figure.json_path else Path()
        yaml_path = Path(persisted_figure.yaml_path) if persisted_figure.yaml_path else Path()
        figure_details.append(
            _figure_validation_result(parsed_figure, persisted_figure, json_path, yaml_path)
        )

    figure_checks["all_figure_checks_passed"] = all(
        all(
            detail[key]
            for key in (
                "json_artifact_exists",
                "yaml_artifact_exists",
                "db_fields_match",
                "provenance_present",
                "caption_resolution_source_present",
                "confidence_field_present",
                "json_artifact_hash_matches",
                "yaml_artifact_hash_matches",
                "json_artifact_content_matches",
                "yaml_artifact_content_matches",
            )
        )
        for detail in figure_details
    )

    passed = (
        all(document_checks.values())
        and chunk_checks["detected_count_matches_persisted"]
        and chunk_checks["all_chunk_checks_passed"]
        and table_checks["detected_count_matches_persisted"]
        and table_checks["all_table_checks_passed"]
        and figure_checks["detected_count_matches_persisted"]
        and figure_checks["all_figure_checks_passed"]
    )
    summary = (
        "Validation passed with warnings."
        if passed and warnings
        else ("Validation passed." if passed else "Validation failed.")
    )
    details = {
        "summary": summary,
        "document_checks": document_checks,
        "chunk_checks": chunk_checks,
        "chunk_details": chunk_details,
        "table_checks": table_checks,
        "table_details": table_details,
        "figure_checks": figure_checks,
        "figure_details": figure_details,
        "warnings": warnings,
        "warning_count": len(warnings),
        "blocking_failures": blocking_failures,
        "blocking_failure_count": len(blocking_failures),
        "document_id": str(document.id),
        "run_id": str(run.id),
    }
    return ValidationReport(
        passed=passed,
        summary=summary,
        details=details,
        warning_count=len(warnings),
    )
