from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ArchitectureInspectionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_name: str
    schema_version: str
    valid: bool
    violation_count: int
    violations: list[dict[str, Any]]
    measurement: dict[str, Any]
    architecture_map: dict[str, Any]


class ArchitectureMeasurementSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_name: str
    schema_version: str
    history_schema_name: str
    history_path: str
    record_count: int
    current_commit_sha: str | None = None
    latest_recorded_commit_sha: str | None = None
    latest_recorded_at: str | None = None
    is_current: bool
    recording_required: bool
    latest: dict[str, Any] | None = None
    previous: dict[str, Any] | None = None
    latest_rule_violation_counts: dict[str, int | float] | None = None
    latest_contract_violation_counts: dict[str, int | float] | None = None
    deltas: dict[str, Any]
