from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import Any

from app.core.json_utils import stable_json_bytes


def payload_sha256(payload: Any) -> str:
    return hashlib.sha256(stable_json_bytes(payload)).hexdigest()


def optional_payload_sha256(payload: Any | None) -> str | None:
    if payload is None:
        return None
    return payload_sha256(payload)


def embedded_payload_hash_matches(payload: dict[str, Any], *, hash_field: str) -> bool:
    expected_hash = str(payload.get(hash_field) or "")
    if not expected_hash:
        return False
    basis = dict(payload)
    basis.pop(hash_field, None)
    return payload_sha256(basis) == expected_hash


def file_sha256(path: str | Path | None) -> str | None:
    if path is None:
        return None
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hmac_sha256_hex(message: str, signing_key: str) -> str:
    return hmac.new(
        signing_key.encode("utf-8"),
        message.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
