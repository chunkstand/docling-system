from __future__ import annotations

from app.core.coercion import unique_strings as _unique_strings


def task_source_record_key(source_type, source_id) -> str | None:
    if source_type is None or source_id is None or source_id == "":
        return None
    source_type_value = str(source_type).strip().lower()
    if source_type_value not in {"chunk", "table"}:
        return None
    return f"source:{source_type_value}:{source_id}"


def _task_int_or_none(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def task_source_page_span(
    *,
    document_id,
    run_id,
    page_from,
    page_to,
) -> dict | None:
    page_from_value = _task_int_or_none(page_from)
    if page_from_value is None or document_id is None or run_id is None:
        return None
    page_to_value = _task_int_or_none(page_to) or page_from_value
    return {
        "document_id": str(document_id),
        "run_id": str(run_id),
        "page_from": page_from_value,
        "page_to": page_to_value,
        "key": (f"page:{document_id}:{run_id}:{page_from_value}:{page_to_value}"),
    }


def unique_page_spans(spans: list[dict]) -> list[dict]:
    return list({span["key"]: span for span in spans if span and span.get("key")}.values())


def task_page_spans_overlap(card_span: dict, source_span: dict) -> bool:
    if card_span.get("document_id") != source_span.get("document_id") or card_span.get(
        "run_id"
    ) != source_span.get("run_id"):
        return False
    return int(card_span["page_from"]) <= int(source_span["page_to"]) and int(
        source_span["page_from"]
    ) <= int(card_span["page_to"])


def source_export_summary(export) -> dict:
    package_payload = export.package_payload_json or {}
    search_request = package_payload.get("search_request") or {}
    source_evidence = list(package_payload.get("source_evidence") or [])
    result_payloads = list(package_payload.get("results") or [])
    source_document_run_keys = _unique_strings(
        f"{document_id}:{run_id}"
        for document_id in (export.document_ids_json or [])
        for run_id in (export.run_ids_json or [])
    )
    source_record_keys: list[str] = []
    source_page_spans: list[dict] = []
    source_results: list[dict] = []
    for source_item in source_evidence:
        document = source_item.get("document") or {}
        run = source_item.get("run") or {}
        item_record_keys: list[str] = []
        item_page_spans: list[dict] = []
        item_record_keys.append(
            task_source_record_key(source_item.get("result_type"), source_item.get("source_id"))
        )
        for source_type, payload_key in (("chunk", "chunk"), ("table", "table")):
            source_payload = source_item.get(payload_key) or {}
            item_record_keys.append(task_source_record_key(source_type, source_payload.get("id")))
            item_page_spans.append(
                task_source_page_span(
                    document_id=source_payload.get("document_id") or document.get("id"),
                    run_id=source_payload.get("run_id") or run.get("id"),
                    page_from=source_payload.get("page_from"),
                    page_to=source_payload.get("page_to"),
                )
            )
        for span in source_item.get("retrieval_evidence_spans") or []:
            item_record_keys.append(
                task_source_record_key(span.get("source_type"), span.get("source_id"))
            )
            item_page_spans.append(
                task_source_page_span(
                    document_id=document.get("id"),
                    run_id=run.get("id"),
                    page_from=span.get("page_from"),
                    page_to=span.get("page_to"),
                )
            )
        item_record_keys = _unique_strings(item_record_keys)
        item_page_spans = unique_page_spans(item_page_spans)
        source_record_keys.extend(item_record_keys)
        source_page_spans.extend(item_page_spans)
        if source_item.get("search_request_result_id"):
            source_results.append(
                {
                    "search_request_result_id": str(source_item["search_request_result_id"]),
                    "source_record_keys": item_record_keys,
                    "source_page_spans": item_page_spans,
                }
            )
    if not source_results:
        source_results = [
            {
                "search_request_result_id": str(result["search_request_result_id"]),
                "source_record_keys": [],
                "source_page_spans": [],
            }
            for result in result_payloads
            if result.get("search_request_result_id")
        ]
    return {
        "evidence_package_export_id": str(export.id),
        "search_request_id": str(export.search_request_id) if export.search_request_id else None,
        "harness_name": search_request.get("harness_name"),
        "package_sha256": export.package_sha256,
        "trace_sha256": export.trace_sha256,
        "query_text": search_request.get("query_text"),
        "mode": search_request.get("mode"),
        "document_ids": [str(value) for value in export.document_ids_json or []],
        "run_ids": [str(value) for value in export.run_ids_json or []],
        "source_document_run_keys": source_document_run_keys,
        "source_record_keys": _unique_strings(source_record_keys),
        "source_page_spans": unique_page_spans(source_page_spans),
        "source_search_request_result_ids": _unique_strings(
            result.get("search_request_result_id") for result in source_results
        ),
        "source_results": source_results,
        "source_result_count": len(source_evidence),
    }
