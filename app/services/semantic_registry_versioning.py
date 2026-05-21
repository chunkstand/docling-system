from __future__ import annotations


def next_semantic_registry_version(base_version: str) -> str:
    prefix, separator, suffix = base_version.rpartition(".")
    if separator and suffix.isdigit():
        return f"{prefix}.{int(suffix) + 1}"
    return f"{base_version}.1"


__all__ = ["next_semantic_registry_version"]
