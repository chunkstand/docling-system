from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import Response
from fastapi.responses import FileResponse


def file_response_if_exists(
    path_value: str | None,
    *,
    media_type: str | None = None,
    path_type: type[Path] = Path,
    response_factory: Callable[..., FileResponse] = FileResponse,
):
    if not path_value:
        return Response(status_code=404)
    path = path_type(path_value)
    if not path.exists():
        return Response(status_code=404)
    return response_factory(path, media_type=media_type)
