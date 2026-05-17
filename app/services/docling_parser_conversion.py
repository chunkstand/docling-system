from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from app.core.config import get_settings
from app.services.docling_parser_types import (
    DEFAULT_CONTINUATION_TITLE_PATTERN,
    TITLE_REGEX_FAMILY_MATCHER,
    UUID_LIKE_PATTERN,
    ParsedChunk,
    TableFamilyMatcher,
    TableSupplementRule,
)


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


def _load_table_supplement_registry(registry_path: str) -> tuple[TableSupplementRule, ...]:
    path = Path(registry_path)
    if not path.is_file():
        return ()
    stat = path.stat()
    return _load_table_supplement_registry_cached(
        str(path),
        stat.st_mtime_ns,
        stat.st_size,
    )


@lru_cache(maxsize=4)
def _load_table_supplement_registry_cached(
    registry_path: str,
    _mtime_ns: int,
    _size: int,
) -> tuple[TableSupplementRule, ...]:
    path = Path(registry_path)
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
