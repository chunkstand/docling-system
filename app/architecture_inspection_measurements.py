from __future__ import annotations

from typing import Any

from app.architecture_inspection_types import (
    ARCHITECTURE_SEVERITIES,
    ArchitectureViolation,
)
from app.architecture_measurement_contracts import ARCHITECTURE_MEASUREMENT_SCHEMA_NAME


def build_architecture_measurement_snapshot(
    violations: list[ArchitectureViolation],
    architecture_map: dict[str, Any],
    *,
    schema_version: str,
) -> dict[str, Any]:
    severity_counts = {
        severity: sum(1 for violation in violations if violation.severity == severity)
        for severity in sorted(ARCHITECTURE_SEVERITIES - {"ignore"})
    }
    contracts = architecture_map["contracts"]
    inspection_rules = architecture_map.get("inspection_rules", [])
    rule_ids = [str(rule["rule_id"]) for rule in inspection_rules]
    rule_violation_counts = {rule_id: 0 for rule_id in rule_ids}
    for violation in violations:
        rule_id = violation.rule_id or "unattributed"
        rule_violation_counts[rule_id] = rule_violation_counts.get(rule_id, 0) + 1

    contract_names = list(
        dict.fromkeys(
            [str(contract["name"]) for contract in contracts]
            + [str(rule["contract"]) for rule in inspection_rules]
            + [violation.contract for violation in violations]
        )
    )
    contract_violation_counts = {contract_name: 0 for contract_name in contract_names}
    for violation in violations:
        contract_violation_counts[violation.contract] = (
            contract_violation_counts.get(violation.contract, 0) + 1
        )
    return {
        "schema_name": ARCHITECTURE_MEASUREMENT_SCHEMA_NAME,
        "schema_version": schema_version,
        "severity_counts": severity_counts,
        "non_ignored_violation_count": len(violations),
        "contract_count": len(contracts),
        "inspection_rule_count": len(rule_ids),
        "rule_violation_counts": rule_violation_counts,
        "contract_violation_counts": contract_violation_counts,
        "api_route_count": next(
            contract["item_count"]
            for contract in contracts
            if contract["name"] == "api_route_capabilities"
        ),
        "agent_action_count": next(
            contract["item_count"]
            for contract in contracts
            if contract["name"] == "agent_action_catalog"
        ),
    }
