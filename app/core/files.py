from __future__ import annotations

from pathlib import Path


def path_exists(path_value: str | None) -> bool:
    return bool(path_value and Path(path_value).exists())


def normalized_source_filename(value: str | None) -> str | None:
    if not value:
        return None
    return Path(value).name.lower()


def source_filename_matches(actual: str | None, expected: str | None) -> bool:
    normalized_expected = normalized_source_filename(expected)
    if normalized_expected is None:
        return True
    return normalized_source_filename(actual) == normalized_expected
