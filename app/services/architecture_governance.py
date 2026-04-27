from __future__ import annotations

from pathlib import Path
from typing import Any


def get_architecture_inspection_report(
    project_root: Path | None = None,
) -> dict[str, Any]:
    from app.architecture_inspection import build_architecture_inspection_report

    return build_architecture_inspection_report(project_root)


def summarize_architecture_measurements(
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    from app.architecture_measurements import summarize_architecture_measurements

    return summarize_architecture_measurements(path, project_root=project_root)
