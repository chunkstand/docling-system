"""DB model contract fragment for platform support."""

from __future__ import annotations

MODEL_SYMBOLS = ("ApiIdempotencyKey",)

PLATFORM_SUPPORT_TABLE_COLUMNS = {
    "api_idempotency_keys": frozenset(
        {
            "created_at",
            "id",
            "idempotency_key",
            "request_fingerprint",
            "response",
            "scope",
            "status_code",
        }
    )
}

REQUIRED_TABLE_INDEX_NAMES = {
    "api_idempotency_keys": frozenset({"ix_api_idempotency_keys_created_at"})
}

REQUIRED_TABLE_INDEX_COLUMNS = {
    "api_idempotency_keys": {"ix_api_idempotency_keys_created_at": ("created_at",)}
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    "api_idempotency_keys": frozenset({"uq_api_idempotency_keys_scope_key"})
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    "api_idempotency_keys": {"uq_api_idempotency_keys_scope_key": ("scope", "idempotency_key")}
}

REQUIRED_VECTOR_DIMENSIONS = {}

REQUIRED_COMPUTED_SQL = {}
