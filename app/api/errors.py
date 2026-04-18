from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.exception_handlers import http_exception_handler as fastapi_http_exception_handler
from fastapi.responses import JSONResponse


def api_error(
    status_code: int,
    code: str,
    message: str,
    *,
    headers: dict[str, str] | None = None,
    **context: Any,
) -> HTTPException:
    detail: dict[str, Any] = {"code": code, "message": message}
    if context:
        detail["context"] = context
    return HTTPException(status_code=status_code, detail=detail, headers=headers)


async def structured_http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        payload: dict[str, Any] = {
            "detail": detail["message"],
            "error_code": detail["code"],
        }
        if "context" in detail:
            payload["error_context"] = detail["context"]
        return JSONResponse(status_code=exc.status_code, content=payload, headers=exc.headers)
    return await fastapi_http_exception_handler(request, exc)
