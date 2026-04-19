from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import Response
from fastapi.responses import FileResponse, JSONResponse


def file_response_if_exists(
    path_value: str | Path | None,
    *,
    media_type: str | None = None,
    path_type: type[Path] = Path,
    response_factory: Callable[..., FileResponse] = FileResponse,
    not_found_detail: str | None = None,
    not_found_error_code: str | None = None,
    not_found_context: dict[str, object] | None = None,
):
    if not path_value:
        if not_found_detail is not None and not_found_error_code is not None:
            payload = {"detail": not_found_detail, "error_code": not_found_error_code}
            if not_found_context:
                payload["error_context"] = not_found_context
            return JSONResponse(status_code=404, content=payload)
        return Response(status_code=404)
    path = path_value if isinstance(path_value, Path) else path_type(path_value)
    if not path.is_file():
        if not_found_detail is not None and not_found_error_code is not None:
            payload = {"detail": not_found_detail, "error_code": not_found_error_code}
            if not_found_context:
                payload["error_context"] = not_found_context
            return JSONResponse(status_code=404, content=payload)
        return Response(status_code=404)
    return response_factory(path, media_type=media_type)
