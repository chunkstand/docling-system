from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from app.api.main import create_app
from app.api.route_contracts import (
    build_api_route_capability_manifest,
    validate_api_route_capability_contracts,
)
from app.core.files import repo_root
from app.services.agent_task_actions import (
    build_agent_task_action_manifest,
    validate_agent_task_action_contracts,
)
from app.services.improvement_case_intake import (
    IMPROVEMENT_CASE_IMPORT_SCHEMA_NAME,
    IMPROVEMENT_CASE_IMPORT_SCHEMA_VERSION,
    list_improvement_case_import_sources,
)
from app.services.improvement_cases import (
    IMPROVEMENT_CASE_SCHEMA_NAME,
    IMPROVEMENT_CASE_SCHEMA_VERSION,
)

ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME = "architecture_contract_map"
ARCHITECTURE_INSPECTION_SCHEMA_NAME = "architecture_inspection"
ARCHITECTURE_INSPECTION_POLICY_SCHEMA_NAME = "architecture_inspection_policy"
ARCHITECTURE_MEASUREMENT_SCHEMA_NAME = "architecture_inspection_measurement"
ARCHITECTURE_CONTRACT_SCHEMA_VERSION = "1.0"
DEFAULT_ARCHITECTURE_CONTRACT_MAP_PATH = Path("docs") / "architecture_contract_map.json"
DEFAULT_ARCHITECTURE_POLICY_PATH = Path("config") / "architecture_inspection.yaml"
ARCHITECTURE_SEVERITIES = frozenset({"error", "warning", "info", "ignore"})
APP_ROUTE_DECORATORS = frozenset({"get", "post", "put", "delete", "patch"})
BOUNDARY_DIRS = ("app/api/routers", "app/workers")
FORBIDDEN_SERVICE_IMPORT_PREFIXES = ("app.api.main", "app.api.routers")
ALLOWED_MAIN_SERVICE_IMPORTS = frozenset({"app.services.runtime"})
FORBIDDEN_BOUNDARY_SERVICE_IMPORTS = frozenset(
    {
        "app.services.agent_task_artifacts",
        "app.services.agent_task_context",
        "app.services.agent_task_verifications",
        "app.services.agent_task_worker",
        "app.services.agent_tasks",
        "app.services.chat",
        "app.services.chunks",
        "app.services.documents",
        "app.services.eval_workbench",
        "app.services.evaluations",
        "app.services.figures",
        "app.services.runs",
        "app.services.search",
        "app.services.search_harness_evaluations",
        "app.services.search_history",
        "app.services.search_legibility",
        "app.services.search_replays",
        "app.services.semantic_backfill",
        "app.services.semantics",
        "app.services.tables",
    }
)
FORBIDDEN_CLI_IMPROVEMENT_INTAKE_SYMBOLS = frozenset(
    {
        "collect_eval_failure_case_observations",
        "collect_failed_agent_task_observations",
        "collect_failed_agent_verification_observations",
        "collect_hygiene_finding_observations",
        "import_improvement_case_observations",
    }
)
REQUIRED_ARCHITECTURE_DOC_TOKENS = frozenset(
    {
        "app.services.capabilities",
        "app.api.route_contracts",
        "tests/unit/test_api_architecture.py",
        "tests/unit/test_api_route_contracts.py",
        "tests/unit/test_agent_action_contracts.py",
        "app.services.improvement_case_intake",
        "ImprovementCaseImportRequest",
        "ImprovementCaseImportResult",
    }
)
CAPABILITY_FACADES = (
    "run_lifecycle",
    "retrieval",
    "evaluation",
    "semantics",
    "agent_orchestration",
)


@dataclass(frozen=True, slots=True)
class ArchitectureViolation:
    contract: str
    field: str
    message: str
    relative_path: str | None = None
    lineno: int | None = None
    symbol: str | None = None
    severity: str = "error"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ArchitectureInspectionPolicy:
    default_severity: str = "error"
    severity_overrides: dict[str, str] | None = None


def load_architecture_inspection_policy(
    policy_path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> ArchitectureInspectionPolicy:
    root = project_root or repo_root()
    raw_path = Path(policy_path) if policy_path is not None else DEFAULT_ARCHITECTURE_POLICY_PATH
    resolved_path = raw_path if raw_path.is_absolute() else root / raw_path
    if not resolved_path.exists():
        return ArchitectureInspectionPolicy()

    payload = yaml.safe_load(resolved_path.read_text()) or {}
    default_severity = str(payload.get("default_severity", "error"))
    if default_severity not in ARCHITECTURE_SEVERITIES:
        raise ValueError(f"Unknown architecture severity '{default_severity}'.")

    overrides: dict[str, str] = {}
    for row in payload.get("severity_overrides") or []:
        key = str(row["match"]).strip()
        severity = str(row["severity"]).strip()
        if severity not in ARCHITECTURE_SEVERITIES:
            raise ValueError(f"Unknown architecture severity '{severity}'.")
        overrides[key] = severity

    return ArchitectureInspectionPolicy(
        default_severity=default_severity,
        severity_overrides=overrides,
    )


def _severity_for_violation(
    violation: ArchitectureViolation,
    policy: ArchitectureInspectionPolicy,
) -> str:
    overrides = policy.severity_overrides or {}
    return (
        overrides.get(f"{violation.contract}.{violation.field}.{violation.symbol}")
        or overrides.get(f"{violation.contract}.{violation.field}")
        or overrides.get(violation.contract)
        or policy.default_severity
    )


def _apply_architecture_policy(
    violations: list[ArchitectureViolation],
    policy: ArchitectureInspectionPolicy,
) -> list[ArchitectureViolation]:
    return [
        replace(violation, severity=_severity_for_violation(violation, policy))
        for violation in violations
    ]


def _parse_python(project_root: Path, relative_path: str) -> ast.Module:
    path = project_root / relative_path
    return ast.parse(path.read_text(), filename=str(path))


def _iter_import_targets(tree: ast.AST) -> list[tuple[str, int]]:
    targets: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.append((node.module, node.lineno))
    return targets


def _main_bootstrap_violations(project_root: Path) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    tree = _parse_python(project_root, "app/api/main.py")
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not isinstance(func, ast.Attribute):
                continue
            if not isinstance(func.value, ast.Name) or func.value.id != "app":
                continue
            if func.attr in APP_ROUTE_DECORATORS:
                violations.append(
                    ArchitectureViolation(
                        contract="api_bootstrap_boundary",
                        field="route_definition",
                        relative_path="app/api/main.py",
                        lineno=node.lineno,
                        symbol=node.name,
                        message="API bootstrap must not define feature routes.",
                    )
                )
    return violations


def _main_service_import_violations(project_root: Path) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    for target, lineno in _iter_import_targets(_parse_python(project_root, "app/api/main.py")):
        if not target.startswith("app.services") or target in ALLOWED_MAIN_SERVICE_IMPORTS:
            continue
        violations.append(
            ArchitectureViolation(
                contract="api_bootstrap_boundary",
                field="service_import",
                relative_path="app/api/main.py",
                lineno=lineno,
                symbol=target,
                message="API bootstrap must not import feature service modules.",
            )
        )
    return violations


def _service_api_import_violations(project_root: Path) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    for path in sorted((project_root / "app/services").rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        relative_path = path.resolve().relative_to(project_root.resolve()).as_posix()
        for target, lineno in _iter_import_targets(tree):
            if not target.startswith(FORBIDDEN_SERVICE_IMPORT_PREFIXES):
                continue
            violations.append(
                ArchitectureViolation(
                    contract="service_layer_boundary",
                    field="api_import",
                    relative_path=relative_path,
                    lineno=lineno,
                    symbol=target,
                    message="Service modules must not import API bootstrap or router modules.",
                )
            )
    return violations


def _boundary_service_import_violations(project_root: Path) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    for boundary_dir in BOUNDARY_DIRS:
        for path in sorted((project_root / boundary_dir).rglob("*.py")):
            tree = ast.parse(path.read_text(), filename=str(path))
            relative_path = path.resolve().relative_to(project_root.resolve()).as_posix()
            for target, lineno in _iter_import_targets(tree):
                if target not in FORBIDDEN_BOUNDARY_SERVICE_IMPORTS:
                    continue
                violations.append(
                    ArchitectureViolation(
                        contract="capability_facade_boundary",
                        field="service_import",
                        relative_path=relative_path,
                        lineno=lineno,
                        symbol=target,
                        message="Boundary modules must use app.services.capabilities facades.",
                    )
                )
    return violations


def _private_service_import_violations(project_root: Path) -> list[ArchitectureViolation]:
    violations: list[ArchitectureViolation] = []
    for path in sorted((project_root / "app/services").rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        relative_path = path.resolve().relative_to(project_root.resolve()).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module is None or not node.module.startswith("app.services"):
                continue
            for alias in node.names:
                if not alias.name.startswith("_"):
                    continue
                violations.append(
                    ArchitectureViolation(
                        contract="service_layer_boundary",
                        field="private_import",
                        relative_path=relative_path,
                        lineno=node.lineno,
                        symbol=f"{node.module}.{alias.name}",
                        message="Service modules must not import private service symbols.",
                    )
                )
    return violations


def _cli_improvement_intake_violations(project_root: Path) -> list[ArchitectureViolation]:
    cli_source = (project_root / "app/cli.py").read_text()
    return [
        ArchitectureViolation(
            contract="improvement_intake_boundary",
            field="cli_import",
            relative_path="app/cli.py",
            symbol=symbol,
            message="CLI must delegate improvement imports to the intake facade.",
        )
        for symbol in sorted(FORBIDDEN_CLI_IMPROVEMENT_INTAKE_SYMBOLS)
        if symbol in cli_source
    ]


def _architecture_doc_violations(project_root: Path) -> list[ArchitectureViolation]:
    relative_path = "docs/architecture_boundaries.md"
    document = (project_root / relative_path).read_text()
    return [
        ArchitectureViolation(
            contract="architecture_documentation",
            field="required_token",
            relative_path=relative_path,
            symbol=token,
            message="Architecture boundary documentation is missing a required contract token.",
        )
        for token in sorted(REQUIRED_ARCHITECTURE_DOC_TOKENS)
        if token not in document
    ]


def _api_route_contract_violations() -> list[ArchitectureViolation]:
    return [
        ArchitectureViolation(
            contract="api_route_capabilities",
            field=issue.field,
            symbol=f"{issue.method} {issue.path}",
            message=issue.message,
        )
        for issue in validate_api_route_capability_contracts(create_app())
    ]


def _agent_action_contract_violations() -> list[ArchitectureViolation]:
    return [
        ArchitectureViolation(
            contract="agent_action_catalog",
            field=issue.field,
            symbol=issue.task_type,
            message=issue.message,
        )
        for issue in validate_agent_task_action_contracts()
    ]


def _architecture_contract_map_path(
    project_root: Path,
    path: str | Path | None = None,
) -> Path:
    raw_path = Path(path) if path is not None else DEFAULT_ARCHITECTURE_CONTRACT_MAP_PATH
    return raw_path if raw_path.is_absolute() else project_root / raw_path


def _architecture_map_drift_violations(
    project_root: Path,
    *,
    map_path: str | Path | None = None,
) -> list[ArchitectureViolation]:
    resolved_path = _architecture_contract_map_path(project_root, map_path)
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

    current_map = build_architecture_contract_map(project_root)
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


def inspect_architecture_contracts(
    project_root: Path | None = None,
    *,
    policy_path: str | Path | None = None,
    map_path: str | Path | None = None,
) -> list[ArchitectureViolation]:
    root = project_root or repo_root()
    violations = [
        *_main_bootstrap_violations(root),
        *_main_service_import_violations(root),
        *_service_api_import_violations(root),
        *_boundary_service_import_violations(root),
        *_private_service_import_violations(root),
        *_cli_improvement_intake_violations(root),
        *_architecture_doc_violations(root),
        *_api_route_contract_violations(),
        *_agent_action_contract_violations(),
        *_architecture_map_drift_violations(root, map_path=map_path),
    ]
    policy = load_architecture_inspection_policy(policy_path, project_root=root)
    violations = [
        violation
        for violation in _apply_architecture_policy(violations, policy)
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
    del project_root
    route_manifest = build_api_route_capability_manifest(create_app())
    agent_action_manifest = build_agent_task_action_manifest()
    return {
        "schema_name": ARCHITECTURE_CONTRACT_MAP_SCHEMA_NAME,
        "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
        "system_style": "modular_monolith",
        "source_documents": [
            "SYSTEM_PLAN.md",
            "README.md",
            "docs/architecture_boundaries.md",
            "docs/improvement_loop.md",
        ],
        "boundary_modules": {
            "api_bootstrap": "app/api/main.py",
            "boundary_dirs": list(BOUNDARY_DIRS),
            "service_dir": "app/services",
        },
        "capability_facades": [
            {
                "name": name,
                "module": f"app.services.capabilities.{name}",
            }
            for name in CAPABILITY_FACADES
        ],
        "contracts": [
            {
                "name": "api_route_capabilities",
                "source": "app.api.route_contracts",
                "item_count": len(route_manifest),
            },
            {
                "name": "agent_action_catalog",
                "source": "app.services.agent_actions",
                "item_count": len(agent_action_manifest),
            },
            {
                "name": "improvement_case_registry",
                "source": "config/improvement_cases.yaml",
                "schema_name": IMPROVEMENT_CASE_SCHEMA_NAME,
                "schema_version": IMPROVEMENT_CASE_SCHEMA_VERSION,
            },
            {
                "name": "improvement_case_intake",
                "source": "app.services.improvement_case_intake",
                "schema_name": IMPROVEMENT_CASE_IMPORT_SCHEMA_NAME,
                "schema_version": IMPROVEMENT_CASE_IMPORT_SCHEMA_VERSION,
                "import_sources": list(list_improvement_case_import_sources()),
            },
        ],
        "inspection_sources": [
            "API route capability contracts",
            "agent action contracts",
            "capability facade boundary imports",
            "service-to-API import boundaries",
            "private service symbol imports",
            "improvement intake CLI delegation",
            "architecture boundary documentation",
            "committed architecture contract map drift",
        ],
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
    return {
        "schema_name": ARCHITECTURE_MEASUREMENT_SCHEMA_NAME,
        "schema_version": ARCHITECTURE_CONTRACT_SCHEMA_VERSION,
        "severity_counts": severity_counts,
        "non_ignored_violation_count": len(violations),
        "contract_count": len(contracts),
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
    resolved_path = _architecture_contract_map_path(root, path)
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
