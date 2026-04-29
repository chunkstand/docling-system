from __future__ import annotations

from typing import Any

from app.core.coercion import unique_strings


def source_evidence_match_status(statuses: list[str]) -> str | None:
    unique_statuses = unique_strings(statuses)
    if not unique_statuses:
        return None
    status_order = {
        "missing": 0,
        "matched_document_run_fallback": 1,
        "matched_page_span": 2,
        "matched_source_record": 3,
    }
    return min(unique_statuses, key=lambda value: status_order.get(value, -1))


def release_readiness_assessment_ready(ref: dict[str, Any]) -> bool:
    integrity = ref.get("integrity") if isinstance(ref.get("integrity"), dict) else {}
    return (
        ref.get("selection_status") == "ready_integrity_complete"
        and ref.get("ready") is True
        and ref.get("readiness_status") == "ready"
        and bool(ref.get("assessment_id"))
        and bool(ref.get("assessment_payload_sha256"))
        and integrity.get("complete") is True
    )
