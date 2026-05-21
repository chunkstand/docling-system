# ruff: noqa: F401, I001
from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.public.audit_and_evidence import EvidencePackageExport
from app.services.evidence_common import (
    page_spans_overlap as _page_spans_overlap,
)
from app.services.evidence_common import (
    source_page_span as _source_page_span,
)
from app.services.evidence_common import (
    source_record_key as _source_record_key,
)
from app.services.evidence_common import (
    string_values as _string_values,
)
from app.services.evidence_common import (
    uuid_values as _uuid_values,
)
from app.services.evidence_search_trace_store import (
    ensure_search_evidence_package_trace_graph,
    search_evidence_trace_integrity_payload,
    search_evidence_trace_rows,
)
from app.services.evidence_records import select_by_ids as _select_by_ids

_ACCEPTABLE_REPORT_SOURCE_MATCH_STATUSES = {
    "matched_source_record",
    "matched_page_span",
}

def _card_source_record_keys(card: dict[str, Any]) -> list[str]:
    metadata = card.get("metadata") or {}
    source_type = str(card.get("source_type") or "").strip().lower()
    source_record_keys = [
        _source_record_key("chunk", card.get("chunk_id") or metadata.get("chunk_id")),
        _source_record_key("table", card.get("table_id") or metadata.get("table_id")),
    ]
    if source_type in {"chunk", "table"}:
        source_record_keys.append(
            _source_record_key(
                source_type,
                card.get("source_locator") or metadata.get("source_locator"),
            )
        )
    return _string_values(source_record_keys)


def _card_page_span(card: dict[str, Any]) -> dict[str, Any] | None:
    return _source_page_span(
        document_id=card.get("document_id"),
        run_id=card.get("run_id"),
        page_from=card.get("page_from"),
        page_to=card.get("page_to"),
    )


def _search_export_source_coverage(export: EvidencePackageExport) -> dict[str, Any]:
    source_record_keys: list[str] = []
    source_page_spans: list[dict[str, Any]] = []
    package = export.package_payload_json or {}
    for source_item in package.get("source_evidence") or []:
        document = source_item.get("document") or {}
        run = source_item.get("run") or {}
        source_record_keys.append(
            _source_record_key(source_item.get("result_type"), source_item.get("source_id"))
        )
        for source_type, payload_key in (("chunk", "chunk"), ("table", "table")):
            source_payload = source_item.get(payload_key) or {}
            source_record_keys.append(_source_record_key(source_type, source_payload.get("id")))
            source_page_spans.append(
                _source_page_span(
                    document_id=source_payload.get("document_id") or document.get("id"),
                    run_id=source_payload.get("run_id") or run.get("id"),
                    page_from=source_payload.get("page_from"),
                    page_to=source_payload.get("page_to"),
                )
            )
        for span in source_item.get("retrieval_evidence_spans") or []:
            source_record_keys.append(
                _source_record_key(span.get("source_type"), span.get("source_id"))
            )
            source_page_spans.append(
                _source_page_span(
                    document_id=document.get("id"),
                    run_id=run.get("id"),
                    page_from=span.get("page_from"),
                    page_to=span.get("page_to"),
                )
            )
    return {
        "source_record_keys": set(_string_values(source_record_keys)),
        "source_page_spans": [
            span
            for span in {
                span["key"]: span for span in source_page_spans if span and span.get("key")
            }.values()
        ],
        "source_result_count": len(package.get("source_evidence") or []),
    }


def _recomputed_card_source_coverage(
    card: dict[str, Any],
    exports_by_id: dict[UUID, EvidencePackageExport],
) -> dict[str, Any]:
    expected_record_keys = set(_card_source_record_keys(card))
    expected_page_span = _card_page_span(card)
    linked_export_ids = _uuid_values(card.get("source_evidence_package_export_ids") or [])
    matched_record_keys: set[str] = set()
    matched_page_span_keys: set[str] = set()
    matching_export_ids: set[str] = set()
    linked_export_count = 0
    for export_id in linked_export_ids:
        export = exports_by_id.get(export_id)
        if export is None or export.package_kind != "search_request":
            continue
        linked_export_count += 1
        coverage = _search_export_source_coverage(export)
        record_overlap = expected_record_keys & coverage["source_record_keys"]
        if record_overlap:
            matched_record_keys.update(record_overlap)
            matching_export_ids.add(str(export.id))
        if expected_page_span is not None:
            overlapping_spans = [
                span
                for span in coverage["source_page_spans"]
                if _page_spans_overlap(expected_page_span, span)
            ]
            if overlapping_spans:
                matched_page_span_keys.update(span["key"] for span in overlapping_spans)
                matching_export_ids.add(str(export.id))

    if expected_record_keys and matched_record_keys == expected_record_keys:
        recomputed_status = "matched_source_record"
    elif expected_page_span is not None and matched_page_span_keys:
        recomputed_status = "matched_page_span"
    else:
        recomputed_status = "missing"
    return {
        "evidence_card_id": str(card.get("evidence_card_id")),
        "reported_match_status": card.get("source_evidence_match_status"),
        "recomputed_match_status": recomputed_status,
        "expected_source_record_keys": sorted(expected_record_keys),
        "matched_source_record_keys": sorted(matched_record_keys),
        "expected_page_span": expected_page_span,
        "matched_page_span_keys": sorted(matched_page_span_keys),
        "linked_source_evidence_package_export_ids": [
            str(export_id) for export_id in linked_export_ids
        ],
        "matching_source_evidence_package_export_ids": sorted(matching_export_ids),
        "linked_search_export_count": linked_export_count,
        "complete": recomputed_status in _ACCEPTABLE_REPORT_SOURCE_MATCH_STATUSES,
    }


def _report_card_requires_source_match(card: dict[str, Any]) -> bool:
    source_type = str(card.get("source_type") or "").strip().lower()
    evidence_kind = str(card.get("evidence_kind") or "").strip().lower()
    return (
        source_type in {"chunk", "table", "figure"}
        or evidence_kind in {"source_evidence", "semantic_fact"}
        or bool(card.get("evidence_ids"))
    )


def technical_report_search_evidence_closure_payload(
    session: Session,
    draft_payload: dict[str, Any],
) -> dict[str, Any]:
    claims = list(draft_payload.get("claims") or [])
    evidence_cards = list(draft_payload.get("evidence_cards") or [])
    package_exports = list(draft_payload.get("source_evidence_package_exports") or [])
    expected_export_ids = _uuid_values(
        [
            *(row.get("evidence_package_export_id") for row in package_exports),
            *(
                value
                for card in evidence_cards
                for value in (card.get("source_evidence_package_export_ids") or [])
            ),
            *(
                value
                for claim in claims
                for value in (claim.get("source_evidence_package_export_ids") or [])
            ),
        ]
    )
    exports_by_id = _select_by_ids(session, EvidencePackageExport, set(expected_export_ids))
    missing_export_ids = [
        str(export_id) for export_id in expected_export_ids if export_id not in exports_by_id
    ]
    non_search_export_ids: list[str] = []
    trace_summaries: list[dict[str, Any]] = []
    incomplete_trace_export_ids: list[str] = []
    for export_id in expected_export_ids:
        export = exports_by_id.get(export_id)
        if export is None:
            continue
        if export.package_kind != "search_request":
            non_search_export_ids.append(str(export.id))
            continue
        ensure_search_evidence_package_trace_graph(session, export)
        nodes, edges = search_evidence_trace_rows(session, export.id)
        integrity = search_evidence_trace_integrity_payload(session, export, nodes, edges)
        if not integrity["complete"]:
            incomplete_trace_export_ids.append(str(export.id))
        trace_summaries.append(
            {
                "evidence_package_export_id": str(export.id),
                "search_request_id": str(export.search_request_id)
                if export.search_request_id
                else None,
                "package_sha256": export.package_sha256,
                "trace_sha256": export.trace_sha256,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "trace_integrity": integrity,
            }
        )

    claims_missing_source_exports = sorted(
        str(claim.get("claim_id"))
        for claim in claims
        if not claim.get("source_evidence_package_export_ids")
    )
    cited_card_ids = {
        str(card_id) for claim in claims for card_id in (claim.get("evidence_card_ids") or [])
    }
    cited_source_cards = [
        card
        for card in evidence_cards
        if str(card.get("evidence_card_id")) in cited_card_ids
        and _report_card_requires_source_match(card)
    ]
    card_source_coverages = [
        _recomputed_card_source_coverage(card, exports_by_id) for card in cited_source_cards
    ]
    cited_cards_missing_source_exports = sorted(
        str(card.get("evidence_card_id"))
        for card in cited_source_cards
        if not card.get("source_evidence_package_export_ids")
    )
    cited_cards_without_acceptable_source_match = sorted(
        str(card.get("evidence_card_id"))
        for card in cited_source_cards
        if card.get("source_evidence_match_status") not in _ACCEPTABLE_REPORT_SOURCE_MATCH_STATUSES
    )
    cited_cards_without_source_record_match = sorted(
        str(card.get("evidence_card_id"))
        for card in cited_source_cards
        if card.get("source_evidence_match_status") != "matched_source_record"
    )
    cited_cards_with_document_run_fallback = sorted(
        str(card.get("evidence_card_id"))
        for card in cited_source_cards
        if card.get("source_evidence_match_status") == "matched_document_run_fallback"
    )
    cited_cards_without_recomputed_source_coverage = sorted(
        row["evidence_card_id"]
        for row in card_source_coverages
        if row["recomputed_match_status"] not in _ACCEPTABLE_REPORT_SOURCE_MATCH_STATUSES
    )
    cited_cards_with_expected_record_without_recomputed_record_match = sorted(
        row["evidence_card_id"]
        for row in card_source_coverages
        if row["expected_source_record_keys"]
        and row["recomputed_match_status"] != "matched_source_record"
    )
    reported_recomputed_match_mismatches = sorted(
        row["evidence_card_id"]
        for row in card_source_coverages
        if row["reported_match_status"] != row["recomputed_match_status"]
    )
    source_evidence_match_status_counts: dict[str, int] = {}
    for card in cited_source_cards:
        status = str(card.get("source_evidence_match_status") or "missing")
        source_evidence_match_status_counts[status] = (
            source_evidence_match_status_counts.get(status, 0) + 1
        )
    recomputed_source_evidence_match_status_counts: dict[str, int] = {}
    for coverage in card_source_coverages:
        status = str(coverage["recomputed_match_status"] or "missing")
        recomputed_source_evidence_match_status_counts[status] = (
            recomputed_source_evidence_match_status_counts.get(status, 0) + 1
        )
    expected_source_record_keys = {
        key for coverage in card_source_coverages for key in coverage["expected_source_record_keys"]
    }
    matched_source_record_keys = {
        key for coverage in card_source_coverages for key in coverage["matched_source_record_keys"]
    }
    source_record_recall = (
        round(len(matched_source_record_keys) / len(expected_source_record_keys), 4)
        if expected_source_record_keys
        else 1.0
    )
    complete = (
        bool(claims)
        and bool(expected_export_ids)
        and not missing_export_ids
        and not non_search_export_ids
        and not incomplete_trace_export_ids
        and not claims_missing_source_exports
        and not cited_cards_missing_source_exports
        and not cited_cards_without_acceptable_source_match
        and not cited_cards_without_recomputed_source_coverage
        and not cited_cards_with_expected_record_without_recomputed_record_match
        and not reported_recomputed_match_mismatches
    )
    return {
        "schema_name": "technical_report_search_evidence_closure",
        "schema_version": "1.0",
        "complete": complete,
        "claim_count": len(claims),
        "cited_source_card_count": len(cited_source_cards),
        "card_source_coverage": card_source_coverages,
        "expected_source_evidence_package_export_count": len(expected_export_ids),
        "persisted_source_evidence_package_export_count": len(trace_summaries),
        "trace_complete_count": sum(
            1 for row in trace_summaries if row["trace_integrity"]["complete"]
        ),
        "expected_source_record_key_count": len(expected_source_record_keys),
        "matched_source_record_key_count": len(matched_source_record_keys),
        "source_record_recall": source_record_recall,
        "missing_source_evidence_package_export_count": len(missing_export_ids),
        "non_search_source_evidence_package_export_count": len(non_search_export_ids),
        "incomplete_trace_count": len(incomplete_trace_export_ids),
        "claims_missing_source_evidence_package_export_count": len(claims_missing_source_exports),
        "cited_cards_missing_source_evidence_package_export_count": len(
            cited_cards_missing_source_exports
        ),
        "cited_cards_without_acceptable_source_evidence_match_count": len(
            cited_cards_without_acceptable_source_match
        ),
        "cited_cards_without_source_record_match_count": len(
            cited_cards_without_source_record_match
        ),
        "cited_cards_with_document_run_fallback_match_count": len(
            cited_cards_with_document_run_fallback
        ),
        "cited_cards_without_recomputed_source_coverage_count": len(
            cited_cards_without_recomputed_source_coverage
        ),
        "cited_cards_with_expected_record_without_recomputed_record_match_count": len(
            cited_cards_with_expected_record_without_recomputed_record_match
        ),
        "reported_recomputed_match_mismatch_count": len(reported_recomputed_match_mismatches),
        "source_evidence_match_status_counts": source_evidence_match_status_counts,
        "recomputed_source_evidence_match_status_counts": (
            recomputed_source_evidence_match_status_counts
        ),
        "expected_source_evidence_package_export_ids": [
            str(export_id) for export_id in expected_export_ids
        ],
        "missing_source_evidence_package_export_ids": missing_export_ids,
        "non_search_source_evidence_package_export_ids": non_search_export_ids,
        "incomplete_trace_export_ids": sorted(incomplete_trace_export_ids),
        "claims_missing_source_evidence_package_export_ids": claims_missing_source_exports,
        "cited_cards_missing_source_evidence_package_export_ids": (
            cited_cards_missing_source_exports
        ),
        "cited_cards_without_acceptable_source_evidence_match_ids": (
            cited_cards_without_acceptable_source_match
        ),
        "cited_cards_without_source_record_match_ids": cited_cards_without_source_record_match,
        "cited_cards_with_document_run_fallback_match_ids": (
            cited_cards_with_document_run_fallback
        ),
        "cited_cards_without_recomputed_source_coverage_ids": (
            cited_cards_without_recomputed_source_coverage
        ),
        "cited_cards_with_expected_record_without_recomputed_record_match_ids": (
            cited_cards_with_expected_record_without_recomputed_record_match
        ),
        "reported_recomputed_match_mismatch_ids": reported_recomputed_match_mismatches,
        "trace_summaries": trace_summaries,
    }
