from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from app.core.coercion import uuid_or_none as _uuid_or_none


def payload_sha256(payload: Any | None) -> str | None:
    if payload is None:
        return None
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def uuid_values(values: Iterable[Any]) -> list[UUID]:
    result: list[UUID] = []
    seen: set[UUID] = set()
    for value in values:
        try:
            uuid_value = _uuid_or_none(value)
        except (TypeError, ValueError):
            continue
        if uuid_value is not None and uuid_value not in seen:
            result.append(uuid_value)
            seen.add(uuid_value)
    return result


def string_values(values: Iterable[Any]) -> list[str]:
    return [str(value) for value in dict.fromkeys(values) if value is not None and value != ""]


def clean_mapping(value: dict[str, Any], *, drop_fields: set[str]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in drop_fields}


def id_str_values(values: Iterable[Any]) -> list[str]:
    return string_values(uuid_values(values))


def source_record_key(source_type: Any, source_id: Any) -> str | None:
    if source_type is None or source_id is None or source_id == "":
        return None
    source_type_value = str(source_type).strip().lower()
    if source_type_value not in {"chunk", "table"}:
        return None
    return f"source:{source_type_value}:{source_id}"


def int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def source_page_span(
    *,
    document_id: Any,
    run_id: Any,
    page_from: Any,
    page_to: Any,
) -> dict[str, Any] | None:
    page_from_value = int_or_none(page_from)
    if page_from_value is None or document_id is None or run_id is None:
        return None
    page_to_value = int_or_none(page_to) or page_from_value
    return {
        "document_id": str(document_id),
        "run_id": str(run_id),
        "page_from": page_from_value,
        "page_to": page_to_value,
        "key": f"page:{document_id}:{run_id}:{page_from_value}:{page_to_value}",
    }


def page_spans_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("document_id") != right.get("document_id"):
        return False
    if left.get("run_id") != right.get("run_id"):
        return False
    return int(left["page_from"]) <= int(right["page_to"]) and int(right["page_from"]) <= int(
        left["page_to"]
    )
