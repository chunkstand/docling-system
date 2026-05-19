from __future__ import annotations

from pathlib import Path

from app.architecture_inspection_rules import (
    ArchitectureInspectionContext,
    list_architecture_rules,
)
from app.architecture_inspection_types import ArchitectureRule

EXPECTED_ARCHITECTURE_RULE_IDS = {
    "agent-action-catalog-contracts",
    "api-bootstrap-no-feature-routes",
    "api-bootstrap-no-feature-service-imports",
    "api-route-capability-contracts",
    "architecture-contract-map-drift",
    "architecture-decision-contracts",
    "architecture-doc-required-tokens",
    "boundary-modules-no-orm-model-imports",
    "boundary-modules-use-capability-facades",
    "capability-surface-contracts",
    "cli-delegates-improvement-intake",
    "service-layer-no-api-imports",
    "service-layer-no-private-service-imports",
}


def write_python(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


def rule(rule_id: str) -> ArchitectureRule:
    return next(row for row in list_architecture_rules() if row.rule_id == rule_id)


def inspection_context(project_root: Path) -> ArchitectureInspectionContext:
    return ArchitectureInspectionContext(
        project_root=project_root,
        expected_contracts=(),
        current_map={},
        map_path=None,
        default_map_path=Path("docs") / "architecture_contract_map.json",
    )
