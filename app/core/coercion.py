from __future__ import annotations

from typing import Any
from uuid import UUID


def uuid_or_none(value: Any | None) -> UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def maybe_uuid(value: Any | None) -> UUID | None:
    try:
        return uuid_or_none(value)
    except (TypeError, ValueError):
        return None


def uuid_text(value: UUID | None) -> str | None:
    return str(value) if value is not None else None


def compact_strings(values: Any) -> list[str]:
    return [str(value) for value in values or [] if value not in {None, ""}]


def unique_strings(values: Any) -> list[str]:
    return [str(value) for value in dict.fromkeys(values or []) if value not in {None, ""}]


def sorted_unique_strings(values: Any) -> list[str]:
    return sorted({str(value) for value in values or [] if value not in {None, ""}})


def string_list_value(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item not in {None, ""}]


def unique_uuids(values: Any) -> list[UUID]:
    ids: list[UUID] = []
    for value in values or []:
        parsed = maybe_uuid(value)
        if parsed is not None and parsed not in ids:
            ids.append(parsed)
    return ids
