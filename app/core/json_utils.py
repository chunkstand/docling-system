from __future__ import annotations

import json
from typing import Any


def stable_json_default(value: Any) -> str:
    return str(value)


def canonical_json_value(payload: Any) -> Any:
    return json.loads(json.dumps(payload, default=stable_json_default, sort_keys=True))


def json_object_payload(payload: Any | None) -> dict:
    if payload is None:
        return {}
    value = payload if isinstance(payload, dict) else {"value": payload}
    return canonical_json_value(value)


def stable_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=stable_json_default,
    ).encode("utf-8")
