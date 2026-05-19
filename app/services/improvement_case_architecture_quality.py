from __future__ import annotations

import json
from pathlib import Path

from app.core.files import repo_root
from app.services.improvement_case_contracts import (
    ARCHITECTURE_QUALITY_REPORT_SCHEMA_NAME,
    DEFAULT_ARCHITECTURE_QUALITY_REPORT_PATH,
)
from app.services.improvement_cases import ImprovementCaseObservation


def resolve_architecture_quality_report_path(
    source_path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> Path:
    raw_path = (
        Path(source_path)
        if source_path is not None
        else DEFAULT_ARCHITECTURE_QUALITY_REPORT_PATH
    )
    return raw_path if raw_path.is_absolute() else (project_root or repo_root()) / raw_path


def _architecture_quality_artifact_type(target_path: str) -> str | None:
    if not target_path:
        return None
    if target_path.startswith("tests/"):
        return "test"
    return "contract"


def collect_architecture_quality_report_observations(
    *,
    source_path: str | Path | None = None,
    limit: int = 50,
    workflow_version: str = "improvement_v1",
    project_root: Path | None = None,
    require_existing: bool = False,
) -> list[ImprovementCaseObservation]:
    report_path = resolve_architecture_quality_report_path(
        source_path,
        project_root=project_root,
    )
    if not report_path.exists():
        if require_existing:
            raise ValueError(f"Architecture quality report not found: {report_path}")
        return []

    try:
        report = json.loads(report_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid architecture quality report JSON: {exc}") from exc

    if not isinstance(report, dict):
        raise ValueError("Architecture quality report must be a JSON object.")
    if report.get("schema_name") != ARCHITECTURE_QUALITY_REPORT_SCHEMA_NAME:
        raise ValueError(
            "Architecture quality report has unexpected schema_name "
            f"{report.get('schema_name')!r}."
        )

    observations: list[ImprovementCaseObservation] = []
    candidates = report.get("improvement_case_candidates")
    if not isinstance(candidates, list):
        candidates = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        source_ref = str(candidate.get("source_ref") or "")
        if not source_ref:
            continue
        artifact_target_path = str(candidate.get("artifact_target_path") or "")
        verification_command = str(candidate.get("verification_command") or "")
        stop_condition = str(candidate.get("stop_condition") or "")
        route_to_case_ids = ",".join(
            str(case_id).strip()
            for case_id in (candidate.get("route_to_case_ids") or [])
            if str(case_id).strip()
        )
        route_to_paths = ",".join(
            str(path).strip()
            for path in (candidate.get("route_to_paths") or [])
            if str(path).strip()
        )
        routing_status = str(candidate.get("routing_status") or "")
        route_reason = str(candidate.get("route_reason") or "")
        observations.append(
            ImprovementCaseObservation(
                title=str(candidate.get("title") or "Architecture quality hotspot"),
                observed_failure=str(
                    candidate.get("observed_failure")
                    or "Architecture quality report identified a hotspot."
                ),
                cause_class=str(candidate.get("cause_class") or "unclear_ownership"),
                source_type="architecture_governance",
                source_ref=source_ref,
                source_notes=(
                    f"report_path={report_path.as_posix()}; "
                    f"artifact_target_path={candidate.get('artifact_target_path') or 'unknown'}; "
                    f"verification_command={candidate.get('verification_command') or 'unknown'}; "
                    f"stop_condition={candidate.get('stop_condition') or 'unknown'}; "
                    f"routing_status={routing_status or 'unknown'}; "
                    f"route_reason={route_reason or 'none'}; "
                    f"route_to_case_ids={route_to_case_ids or 'none'}; "
                    f"route_to_paths={route_to_paths or 'none'}"
                ),
                artifact_type=_architecture_quality_artifact_type(artifact_target_path),
                artifact_target_path=artifact_target_path or None,
                artifact_description=(
                    f"Architecture quality owner surface for {artifact_target_path}."
                    if artifact_target_path
                    else None
                ),
                verification_commands=[verification_command] if verification_command else [],
                acceptance_conditions=[stop_condition] if stop_condition else [],
                workflow_version=workflow_version,
            )
        )
    return observations[:limit]
