from __future__ import annotations

import secrets
import time
from collections import deque
from functools import lru_cache
from pathlib import Path
from threading import Lock

from fastapi import Header, Request, status
from fastapi.responses import FileResponse

from app.api.capabilities import require_known_api_capability
from app.api.errors import api_error
from app.api.file_delivery import file_response_if_exists
from app.core.config import (
    get_settings,
    resolve_api_credentials,
    resolve_api_mode,
    resolve_remote_api_capabilities,
    semantics_feature_enabled,
)
from app.services.storage import StorageService

UI_DIR = Path(__file__).resolve().parent.parent / "ui"
PUBLIC_REMOTE_PATHS = frozenset({"/health"})
SEARCH_RATE_LIMIT = 300
SEARCH_RATE_WINDOW_SECONDS = 60.0
_search_rate_limit_lock = Lock()
_search_request_times: dict[str, deque[float]] = {}


def api_mode_metadata() -> dict[str, object]:
    settings = get_settings()
    resolved_mode = resolve_api_mode(settings)
    resolved_credentials = resolve_api_credentials(settings)
    payload = {
        "api_mode": resolved_mode,
        "api_mode_explicit": settings.api_mode is not None,
        "api_host": settings.api_host,
        "api_port": settings.api_port,
        "semantics_enabled": semantics_feature_enabled(settings),
    }
    if resolved_mode == "remote":
        payload["remote_api_auth_mode"] = (
            "actor_scoped"
            if getattr(settings, "api_credentials_json", None)
            else "legacy_single_key"
        )
        payload["remote_api_principals"] = [
            {"actor": credential.actor, "capabilities": sorted(credential.capabilities)}
            for credential in resolved_credentials
        ]
        if not getattr(settings, "api_credentials_json", None):
            payload["remote_api_capabilities"] = sorted(resolve_remote_api_capabilities(settings))
    return payload


def ensure_semantics_enabled() -> None:
    settings = get_settings()
    if semantics_feature_enabled(settings):
        return
    raise api_error(
        status.HTTP_409_CONFLICT,
        "semantics_disabled",
        "Semantic layer is disabled. Set DOCLING_SYSTEM_SEMANTICS_ENABLED=1 to enable it.",
    )


def require_api_key_for_mutations(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    settings = get_settings()
    if resolve_api_mode(settings) != "remote" and not api_auth_is_configured(settings):
        return

    credential = resolve_api_credential(
        settings=settings,
        x_api_key=x_api_key,
        authorization=authorization,
    )
    if credential is not None:
        request.state.api_credential = credential
        return

    raise api_error(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="auth_required",
        message="Valid API key required for mutating API access.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_api_capability(capability: str):
    capability = require_known_api_capability(capability)

    def dependency(
        request: Request,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> None:
        settings = get_settings()
        if resolve_api_mode(settings) != "remote":
            return
        credential = getattr(request.state, "api_credential", None) or resolve_api_credential(
            settings=settings,
            x_api_key=x_api_key,
            authorization=authorization,
        )
        if credential is None:
            raise api_error(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="auth_required",
                message="Valid API key required for remote API access.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        request.state.api_credential = credential
        allowed_capabilities = credential.capabilities
        if "*" in allowed_capabilities or capability in allowed_capabilities:
            return
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "capability_not_allowed",
            f"Remote API capability '{capability}' is not enabled.",
            capability=capability,
            actor=credential.actor,
        )

    dependency.api_capability = capability
    return dependency


require_api_key_for_mutations.api_mutation_key_required = True


def _bearer_token_from_header(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token
    return None


def api_auth_is_configured(settings) -> bool:
    return bool(resolve_api_credentials(settings))


def resolve_api_credential(
    *,
    settings,
    x_api_key: str | None,
    authorization: str | None,
) -> object | None:
    bearer_token = _bearer_token_from_header(authorization)
    provided_values = [value for value in (x_api_key, bearer_token) if value]
    for credential in resolve_api_credentials(settings):
        if any(secrets.compare_digest(value, credential.key) for value in provided_values):
            return credential
    return None


def _search_rate_limit_key(request: Request) -> str:
    credential = getattr(request.state, "api_credential", None)
    if credential is not None:
        return f"credential:{credential.actor}"
    client_host = request.client.host if request.client else "unknown"
    return f"client:{client_host}"


def enforce_search_rate_limit(request: Request) -> None:
    key = _search_rate_limit_key(request)
    now = time.monotonic()
    rate_window_seconds = SEARCH_RATE_WINDOW_SECONDS
    rate_limit = SEARCH_RATE_LIMIT
    window_start = now - rate_window_seconds
    with _search_rate_limit_lock:
        request_times = _search_request_times.setdefault(key, deque())
        while request_times and request_times[0] < window_start:
            request_times.popleft()
        if len(request_times) >= rate_limit:
            raise api_error(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "rate_limited",
                "Search request rate limit exceeded. Try again shortly.",
                headers={"Retry-After": str(int(rate_window_seconds))},
            )
        request_times.append(now)


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    return StorageService()


def storage_file_response(
    path_value: str | Path | None,
    *,
    media_type: str | None = None,
    not_found_detail: str | None = None,
    not_found_error_code: str | None = None,
    not_found_context: dict[str, object] | None = None,
):
    return file_response_if_exists(
        get_storage_service().resolve_existing_path(path_value),
        media_type=media_type,
        response_factory=FileResponse,
        not_found_detail=not_found_detail,
        not_found_error_code=not_found_error_code,
        not_found_context=not_found_context,
    )


def response_field(payload, field_name: str):
    value = getattr(payload, field_name, None)
    if value is None and isinstance(payload, dict):
        value = payload.get(field_name)
    return value
