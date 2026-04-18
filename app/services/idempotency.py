from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.time import utcnow
from app.db.models import ApiIdempotencyKey


def _load_idempotency_row(
    session: Session,
    *,
    scope: str,
    idempotency_key: str,
) -> ApiIdempotencyKey | None:
    return session.execute(
        select(ApiIdempotencyKey).where(
            ApiIdempotencyKey.scope == scope,
            ApiIdempotencyKey.idempotency_key == idempotency_key,
        )
    ).scalar_one_or_none()


def _validate_fingerprint(
    row: ApiIdempotencyKey,
    *,
    request_fingerprint: str,
) -> None:
    if row.request_fingerprint == request_fingerprint:
        return
    raise api_error(
        409,
        "idempotency_key_reused",
        "Idempotency key has already been used for a different request.",
    )


def get_idempotent_response(
    session: Session,
    *,
    scope: str,
    idempotency_key: str | None,
    request_fingerprint: str,
) -> tuple[dict[str, Any], int] | None:
    if not idempotency_key:
        return None
    row = _load_idempotency_row(session, scope=scope, idempotency_key=idempotency_key)
    if row is None:
        return None
    _validate_fingerprint(row, request_fingerprint=request_fingerprint)
    return row.response_json or {}, row.status_code


def store_idempotent_response(
    session: Session,
    *,
    scope: str,
    idempotency_key: str | None,
    request_fingerprint: str,
    response_payload: dict[str, Any],
    status_code: int,
    created_at: datetime | None = None,
) -> None:
    if not idempotency_key:
        return
    payload = jsonable_encoder(response_payload)
    row = _load_idempotency_row(session, scope=scope, idempotency_key=idempotency_key)
    if row is not None:
        _validate_fingerprint(row, request_fingerprint=request_fingerprint)
        row.status_code = status_code
        row.response_json = payload
        return

    row = ApiIdempotencyKey(
        scope=scope,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
        status_code=status_code,
        response_json=payload,
        created_at=created_at or utcnow(),
    )
    try:
        with session.begin_nested():
            session.add(row)
            session.flush()
    except IntegrityError:
        existing = _load_idempotency_row(session, scope=scope, idempotency_key=idempotency_key)
        if existing is None:
            raise
        _validate_fingerprint(existing, request_fingerprint=request_fingerprint)
