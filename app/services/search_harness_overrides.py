from __future__ import annotations

import json
from pathlib import Path


def get_search_harness_override_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "search_harness_overrides.json"


def load_applied_search_harness_overrides() -> dict[str, dict]:
    path = get_search_harness_override_path()
    if not path.exists():
        return {}

    payload = json.loads(path.read_text() or "{}")
    harnesses = payload.get("harnesses") or {}
    if not isinstance(harnesses, dict):
        msg = "Search harness override file must contain a top-level 'harnesses' object."
        raise ValueError(msg)
    return harnesses


def write_applied_search_harness_overrides(overrides: dict[str, dict]) -> Path:
    path = get_search_harness_override_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "harnesses": overrides,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return path


def upsert_applied_search_harness_override(harness_name: str, spec: dict) -> Path:
    overrides = load_applied_search_harness_overrides()
    overrides[harness_name] = spec
    return write_applied_search_harness_overrides(overrides)
