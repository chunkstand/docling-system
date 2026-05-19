from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.api.main import create_app
from app.api.route_contracts import validate_api_route_capability_contracts
from app.architecture_decisions import validate_architecture_decisions
from app.architecture_inspection_types import ArchitectureViolation
from app.capability_contracts import validate_capability_contracts
from app.services.agent_task_actions import validate_agent_task_action_contracts


def api_route_contract_violations() -> list[ArchitectureViolation]:
    return [
        ArchitectureViolation(
            contract="api_route_capabilities",
            field=issue.field,
            symbol=f"{issue.method} {issue.path}",
            message=issue.message,
        )
        for issue in validate_api_route_capability_contracts(create_app())
    ]


def agent_action_contract_violations() -> list[ArchitectureViolation]:
    return [
        ArchitectureViolation(
            contract="agent_action_catalog",
            field=issue.field,
            symbol=issue.task_type,
            message=issue.message,
        )
        for issue in validate_agent_task_action_contracts()
    ]


def architecture_decision_violations(
    project_root: Path,
    *,
    expected_contracts: tuple[str, ...],
) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    for issue in validate_architecture_decisions(
        project_root,
        expected_contracts=expected_contracts,
    ):
        payload = issue.to_dict()
        payload["contract"] = "architecture_decisions"
        violations.append(ArchitectureViolation(**payload))
    return violations


def capability_contract_violations(project_root: Path) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    for issue in validate_capability_contracts(project_root):
        payload = issue.to_dict()
        payload["contract"] = "capability_surface_contracts"
        violations.append(ArchitectureViolation(**payload))
    return violations


def architecture_map_drift_violations(
    *,
    project_root: Path,
    resolved_path: Path,
    current_map: dict[str, Any],
) -> list[ArchitectureViolation]:
    try:
        relative_path = resolved_path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        relative_path = str(resolved_path)

    if not resolved_path.exists():
        return [
            ArchitectureViolation(
                contract="architecture_contract_map",
                field="persisted_map",
                relative_path=relative_path,
                message=(
                    "Committed architecture contract map is missing; run "
                    "`uv run docling-system-architecture-inspect --write-map`."
                ),
            )
        ]

    persisted_map = json.loads(resolved_path.read_text())
    if persisted_map == current_map:
        return []
    return [
        ArchitectureViolation(
            contract="architecture_contract_map",
            field="persisted_map",
            relative_path=relative_path,
            message=(
                "Committed architecture contract map is stale; run "
                "`uv run docling-system-architecture-inspect --write-map`."
            ),
        )
    ]
