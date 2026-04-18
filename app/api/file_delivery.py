from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import Response
from fastapi.responses import FileResponse


def file_response_if_exists(
    path_value: str | Path | None,
    *,
    media_type: str | None = None,
    path_type: type[Path] = Path,
    response_factory: Callable[..., FileResponse] = FileResponse,
):
    if not path_value:
        return Response(status_code=404)
    path = path_value if isinstance(path_value, Path) else path_type(path_value)
    if not path.is_file():
        return Response(status_code=404)
    return response_factory(path, media_type=media_type)
