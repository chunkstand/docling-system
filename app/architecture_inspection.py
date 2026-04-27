from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.api.main import create_app
from app.api.route_contracts import build_api_route_capability_manifest
from app.architecture_decisions import (
    ARCHITECTURE_DECISION_SCHEMA_NAME,
    build_architecture_decision_map,
)
from app.architecture_inspection_policy import (
    DEFAULT_ARCHITECTURE_POLICY_PATH,
    apply_architecture_policy,
    load_architecture_inspection_policy,
)
from app.architecture_inspection_rules import (
    BOUNDARY_DIRS,
    build_architecture_rule_manifest,
    collect_architecture_rule_violations,
    resolve_architecture_contract_map_path,
)
from app.architecture_inspection_types import (
    ARCHITECTURE_SEVERITIES,
    ArchitectureViolation,
)
from app.architecture_measurement_contracts import (
    ARCHITECTURE_GOVERNANCE_REPORT_FIELDS,
    ARCHITECTURE_GOVERNANCE_REPORT_SCHEMA_NAME,
    ARCHITECTURE_MEASUREMENT_DELTA_FIELDS,
    ARCHITECTURE_MEASUREMENT_FIELDS,
    ARCHITECTURE_MEASUREMENT_HISTORY_SCHEMA_NAME,
    ARCHITECTURE_MEASUREMENT_RECORD_SCHEMA_NAME,
    ARCHITECTURE_MEASUREMENT_SCHEMA_NAME,
    ARCHITECTURE_MEASUREMENT_SUMMARY_FIELDS,
    ARCHITECTURE_MEASUREMENT_SUMMARY_SCHEMA_NAME,
    DEFAULT_ARCHITECTURE_GOVERNANCE_REPORT_PATH,
    DEFAULT_ARCHITECTURE_MEASUREMENT_HISTORY_PATH,
)
from app.capability_contracts import (
    CAPABILITY_CONTRACT_MAP_SCHEMA_NAME,
    build_capability_contract_map,
)
from app.core.files import repo_root
from app.services.agent_task_actions import build_agent_task_action_manifest
from app.services.improvement_case_intake import (
    IMPROVEMENT_CASE_IMPORT_SCHEMA_NAME,
    IMPROVEMENT_CASE_IMPORT_SCHEMA_VERSION,
    list_improvement_case_import_source_specs,
    list_improvement_case_import_sources,
)
from app.services.improvement_cases import (
    IMPROVEMENT_CASE_SCHEMA_NAME,
    IMPROVEMENT_CASE_SCHEMA_VERSION,
)

ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME = "architecture_contract_map"
ARCHITECTURE_INSPECTION_SCHEMA_NAME = "architecture_inspection"
ARCHITECTURE_INSPECTION_POLICY_SCHEMA_NAME = "architecture_inspection_policy"
ARCHITECTURE_CONTRACT_SCHEMA_VERSION = "1.0"
DEFAULT_ARCHITECTURE_CONTRACT_MAP_PATH = Path("docs") / "architecture_contract_map.json"


def inspect_architecture_contracts(
    project_root: Path | None = None,
    *,
    policy_path: str | Path | None = None,
    map_path: str | Path | None = None,
) -> list[ArchitectureViolation]:
    root = project_root or repo_root()
    architecture_map = build_architecture_contract_map(root)
    expected_contracts = tuple(
        str(contract["name"])
        for contract in architecture_map["contracts"]
    )
    violations = collect_architecture_rule_violations(
        root,
        expected_contracts=expected_contracts,
        current_map=architecture_map,
        map_path=map_path,
        default_map_path=DEFAULT_ARCHITECTURE_CONTRACT_MAP_PATH,
    )
    policy = load_architecture_inspection_policy(policy_path, project_root=root)
    violations = [
        violation
        for violation in apply_architecture_policy(violations, policy)
        if violation.severity != "ignore"
    ]
    return sorted(
        violations,
        key=lambda row: (
            row.severity,
            row.contract,
            row.relative_path or "",
            row.lineno or 0,
            row.field,
            row.symbol or "",
        ),
    )


def build_architecture_contract_map(project_root: Path | None = None) -> dict[str, Any]:
    root = project_root or repo_root()
    route_manifest = build_api_route_capability_manifest(create_app())
    agent_action_manifest = build_agent_task_action_manifest()
    capability_contract_map = build_capability_contract_map(root)
    architecture_decision_map = build_architecture_decision_map(root)
    inspection_rules = build_architecture_rule_manifest()
    decision_ids_by_contract = {
        row["contract"]: row["decision_ids"]
        for row in architecture_decision_map["contract_decision_links"]
    }
    return {
        "schema_name": ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME,
        "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
        "system_style": "modular_monolith",
        "source_documents": [
            "SYSTEM_PLAN.md",
            "README.md",
            "docs/architecture_boundaries.md",
            "docs/architecture_decisions.yaml",
            "docs/improvement_loop.md",
        ],
        "boundary_modules": {
            "api_bootstrap": "app/api/main.py",
            "boundary_dirs": list(BOUNDARY_DIRS),
            "service_dir": "app/services",
        },
        "capability_facades": [
            {
                "name": facade["name"],
                "module": facade["module"],
                "function_count": facade["function_count"],
            }
            for facade in capability_contract_map["facades"]
        ],
        "contracts": [
            {
                "name": ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME,
                "source": "docs/architecture_contract_map.json",
                "schema_name": ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME,
                "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
                "decision_ids": decision_ids_by_contract.get(
                    ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME,
                    [],
                ),
            },
            {
                "name": "api_route_capabilities",
                "source": "app.api.route_contracts",
                "item_count": len(route_manifest),
                "decision_ids": decision_ids_by_contract.get("api_route_capabilities", []),
            },
            {
                "name": "agent_action_catalog",
                "source": "app.services.agent_actions",
                "item_count": len(agent_action_manifest),
                "decision_ids": decision_ids_by_contract.get("agent_action_catalog", []),
            },
            {
                "name": "capability_surface_contracts",
                "source": "docs/capability_contract_map.json",
                "schema_name": CAPABILITY_CONTRACT_MAP_SCHEMA_NAME,
                "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
                "item_count": capability_contract_map["function_count"],
                "decision_ids": decision_ids_by_contract.get("capability_surface_contracts", []),
            },
            {
                "name": "improvement_case_registry",
                "source": "config/improvement_cases.yaml",
                "schema_name": IMPROVEMENT_CASE_SCHEMA_NAME,
                "schema_version": IMPROVEMENT_CASE_SCHEMA_VERSION,
                "decision_ids": decision_ids_by_contract.get("improvement_case_registry", []),
            },
            {
                "name": "improvement_case_intake",
                "source": "app.services.improvement_case_intake",
                "schema_name": IMPROVEMENT_CASE_IMPORT_SCHEMA_NAME,
                "schema_version": IMPROVEMENT_CASE_IMPORT_SCHEMA_VERSION,
                "import_sources": list(list_improvement_case_import_sources()),
                "import_source_specs": list(list_improvement_case_import_source_specs()),
                "decision_ids": decision_ids_by_contract.get("improvement_case_intake", []),
            },
            {
                "name": "improvement_case_lifecycle",
                "source": "app.services.improvement_case_lifecycle",
                "schema_name": "improvement_case_update",
                "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
                "decision_ids": decision_ids_by_contract.get("improvement_case_lifecycle", []),
            },
            {
                "name": "architecture_decisions",
                "source": "docs/architecture_decisions.yaml",
                "map_source": "docs/architecture_decision_map.json",
                "schema_name": ARCHITECTURE_DECISION_SCHEMA_NAME,
                "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
                "item_count": architecture_decision_map["decision_count"],
                "decision_ids": decision_ids_by_contract.get("architecture_decisions", []),
            },
            {
                "name": "architecture_measurement_history",
                "source": "app.architecture_measurements",
                "schema_name": ARCHITECTURE_MEASUREMENT_HISTORY_SCHEMA_NAME,
                "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
                "history_path": DEFAULT_ARCHITECTURE_MEASUREMENT_HISTORY_PATH.as_posix(),
                "record_schema_name": ARCHITECTURE_MEASUREMENT_RECORD_SCHEMA_NAME,
                "measurement_schema_name": ARCHITECTURE_MEASUREMENT_SCHEMA_NAME,
                "summary_schema_name": ARCHITECTURE_MEASUREMENT_SUMMARY_SCHEMA_NAME,
                "report_schema_name": ARCHITECTURE_GOVERNANCE_REPORT_SCHEMA_NAME,
                "measurement_fields": list(ARCHITECTURE_MEASUREMENT_FIELDS),
                "summary_fields": list(ARCHITECTURE_MEASUREMENT_SUMMARY_FIELDS),
                "delta_fields": list(ARCHITECTURE_MEASUREMENT_DELTA_FIELDS),
                "report_fields": list(ARCHITECTURE_GOVERNANCE_REPORT_FIELDS),
                "ci_report_path": DEFAULT_ARCHITECTURE_GOVERNANCE_REPORT_PATH.as_posix(),
                "ci_history_path": (
                    "build/architecture-governance/architecture_measurement_history.jsonl"
                ),
                "ci_workflow": ".github/workflows/architecture-governance.yml",
                "decision_ids": decision_ids_by_contract.get(
                    "architecture_measurement_history",
                    [],
                ),
            },
        ],
        "inspection_sources": [
            "API route capability contracts",
            "agent action contracts",
            "service capability surface contracts",
            "capability facade boundary imports",
            "boundary data model import checks",
            "service-to-API import boundaries",
            "private service symbol imports",
            "improvement intake CLI delegation",
            "architecture boundary documentation",
            "architecture decision registry",
            "committed architecture contract map drift",
            "architecture measurement history",
        ],
        "inspection_rules": inspection_rules,
    }


def build_architecture_measurement_snapshot(
    violations: list[ArchitectureViolation],
    architecture_map: dict[str, Any],
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
        "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
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


def build_architecture_inspection_report(
    project_root: Path | None = None,
    *,
    policy_path: str | Path | None = None,
    map_path: str | Path | None = None,
) -> dict[str, Any]:
    root = project_root or repo_root()
    violations = inspect_architecture_contracts(
        root,
        policy_path=policy_path,
        map_path=map_path,
    )
    architecture_map = build_architecture_contract_map(root)
    return {
        "schema_name": ARCHITECTURE_INSPECTION_SCHEMA_NAME,
        "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
        "valid": all(violation.severity != "error" for violation in violations),
        "violation_count": len(violations),
        "violations": [violation.to_dict() for violation in violations],
        "measurement": build_architecture_measurement_snapshot(violations, architecture_map),
        "architecture_map": architecture_map,
    }


def write_architecture_contract_map(
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> Path:
    root = project_root or repo_root()
    resolved_path = resolve_architecture_contract_map_path(
        root,
        DEFAULT_ARCHITECTURE_CONTRACT_MAP_PATH,
        path,
    )
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(
        json.dumps(build_architecture_contract_map(root), indent=2, sort_keys=True) + "\n"
    )
    return resolved_path


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect the repo architecture contracts and emit a machine-readable map."
    )
    parser.add_argument(
        "--map-only",
        action="store_true",
        help="Print only the architecture contract map.",
    )
    parser.add_argument(
        "--write-map",
        action="store_true",
        help="Write the current architecture contract map to docs/architecture_contract_map.json.",
    )
    parser.add_argument(
        "--map-path",
        default=str(DEFAULT_ARCHITECTURE_CONTRACT_MAP_PATH),
        help="Path to the persisted architecture contract map.",
    )
    parser.add_argument(
        "--policy-path",
        default=str(DEFAULT_ARCHITECTURE_POLICY_PATH),
        help="Path to the architecture inspection policy.",
    )
    args = parser.parse_args(argv)

    if args.write_map:
        path = write_architecture_contract_map(args.map_path)
        try:
            display_path = path.relative_to(repo_root()).as_posix()
        except ValueError:
            display_path = path.as_posix()
        print(
            json.dumps(
                {
                    "schema_name": "architecture_contract_map_write",
                    "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
                    "path": display_path,
                },
                sort_keys=True,
            )
        )
        return 0

    payload = (
        build_architecture_contract_map()
        if args.map_only
        else build_architecture_inspection_report(
            policy_path=args.policy_path,
            map_path=args.map_path,
        )
    )
    print(json.dumps(payload, sort_keys=True))
    if args.map_only:
        return 0
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(run())
