from __future__ import annotations


def collapse_whitespace(value: str | None) -> str:
    return " ".join((value or "").split()).strip()
