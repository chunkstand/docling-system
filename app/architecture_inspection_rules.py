from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.api.main import create_app
from app.api.route_contracts import validate_api_route_capability_contracts
from app.architecture_decisions import validate_architecture_decisions
from app.architecture_inspection_rule_config import (
    ALLOWED_MAIN_SERVICE_IMPORTS,
    APP_ROUTE_DECORATORS,
    BOUNDARY_DIRS,
    FORBIDDEN_BOUNDARY_DATA_MODEL_IMPORTS,
    FORBIDDEN_BOUNDARY_SERVICE_IMPORTS,
    FORBIDDEN_CLI_IMPROVEMENT_INTAKE_SYMBOLS,
    FORBIDDEN_SERVICE_IMPORT_PREFIXES,
    REQUIRED_ARCHITECTURE_DOC_TOKENS,
)
from app.architecture_inspection_rule_config import (
    FORBIDDEN_CLI_IMPROVEMENT_INTAKE_MODULES as CLI_INTAKE_MODULES,
)
from app.architecture_inspection_types import ArchitectureRule, ArchitectureViolation
from app.capability_contracts import validate_capability_contracts
from app.services.agent_task_actions import validate_agent_task_action_contracts


@dataclass(frozen=True, slots=True)
class ArchitectureInspectionContext:
    project_root: Path
    expected_contracts: tuple[str, ...]
    current_map: dict[str, Any]
    map_path: str | Path | None
    default_map_path: Path


def resolve_architecture_contract_map_path(
    project_root: Path,
    default_path: Path,
    path: str | Path | None = None,
) -> Path:
    raw_path = Path(path) if path is not None else default_path
    return raw_path if raw_path.is_absolute() else project_root / raw_path


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


def _matches_module_or_submodule(target: str, module: str) -> bool:
    return target == module or target.startswith(f"{module}.")


def _matches_any_module_or_submodule(
    target: str,
    modules: frozenset[str] | tuple[str, ...],
) -> bool:
    return any(_matches_module_or_submodule(target, module) for module in modules)


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
        if not _matches_module_or_submodule(
            target,
            "app.services",
        ) or _matches_any_module_or_submodule(target, ALLOWED_MAIN_SERVICE_IMPORTS):
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
            if not _matches_any_module_or_submodule(target, FORBIDDEN_SERVICE_IMPORT_PREFIXES):
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
                if target in FORBIDDEN_BOUNDARY_SERVICE_IMPORTS:
                    violations.append(
                        ArchitectureViolation(
                            contract="capability_facade_boundary",
                            field="service_import",
                            relative_path=relative_path,
                            lineno=lineno,
                            symbol=target,
                            message=(
                                "Boundary modules must use app.services.capabilities facades."
                            ),
                        )
                    )
                if target in FORBIDDEN_BOUNDARY_DATA_MODEL_IMPORTS:
                    violations.append(
                        ArchitectureViolation(
                            contract="capability_facade_boundary",
                            field="data_model_import",
                            relative_path=relative_path,
                            lineno=lineno,
                            symbol=target,
                            message="Boundary modules must not import ORM models directly.",
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
            if node.module is None or not _matches_module_or_submodule(
                node.module,
                "app.services",
            ):
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
    tree = _parse_python(project_root, "app/cli.py")
    violations: list[ArchitectureViolation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            if not _matches_any_module_or_submodule(node.module, CLI_INTAKE_MODULES):
                continue
            for alias in node.names:
                if alias.name not in FORBIDDEN_CLI_IMPROVEMENT_INTAKE_SYMBOLS:
                    continue
                violations.append(
                    ArchitectureViolation(
                        contract="improvement_intake_boundary",
                        field="cli_import",
                        relative_path="app/cli.py",
                        lineno=node.lineno,
                        symbol=f"{node.module}.{alias.name}",
                        message="CLI must delegate improvement imports to the intake facade.",
                    )
                )
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id != "_lazy_service_attr":
                continue
            if len(node.args) < 2:
                continue
            module_arg, symbol_arg = node.args[:2]
            if not (
                isinstance(module_arg, ast.Constant)
                and isinstance(module_arg.value, str)
                and isinstance(symbol_arg, ast.Constant)
                and isinstance(symbol_arg.value, str)
            ):
                continue
            if not _matches_any_module_or_submodule(module_arg.value, CLI_INTAKE_MODULES):
                continue
            if symbol_arg.value not in FORBIDDEN_CLI_IMPROVEMENT_INTAKE_SYMBOLS:
                continue
            violations.append(
                ArchitectureViolation(
                    contract="improvement_intake_boundary",
                    field="cli_import",
                    relative_path="app/cli.py",
                    lineno=node.lineno,
                    symbol=f"{module_arg.value}.{symbol_arg.value}",
                    message="CLI must delegate improvement imports to the intake facade.",
                )
            )
    return violations


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


def _architecture_decision_violations(
    project_root: Path,
    *,
    expected_contracts: tuple[str, ...],
) -> list[ArchitectureViolation]:
    return [
        ArchitectureViolation(**issue.to_dict())
        for issue in validate_architecture_decisions(
            project_root,
            expected_contracts=expected_contracts,
        )
    ]


def _capability_contract_violations(project_root: Path) -> list[ArchitectureViolation]:
    return [
        ArchitectureViolation(**issue.to_dict())
        for issue in validate_capability_contracts(project_root)
    ]


def _architecture_map_drift_violations(
    project_root: Path,
    *,
    current_map: dict[str, Any],
    map_path: str | Path | None,
    default_map_path: Path,
) -> list[ArchitectureViolation]:
    resolved_path = resolve_architecture_contract_map_path(
        project_root,
        default_map_path,
        map_path,
    )
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


def check_main_bootstrap_rule(
    context: ArchitectureInspectionContext,
) -> list[ArchitectureViolation]:
    return _main_bootstrap_violations(context.project_root)


def check_main_service_import_rule(
    context: ArchitectureInspectionContext,
) -> list[ArchitectureViolation]:
    return _main_service_import_violations(context.project_root)


def check_service_api_import_rule(
    context: ArchitectureInspectionContext,
) -> list[ArchitectureViolation]:
    return _service_api_import_violations(context.project_root)


def check_boundary_service_import_rule(
    context: ArchitectureInspectionContext,
) -> list[ArchitectureViolation]:
    return [
        violation
        for violation in _boundary_service_import_violations(context.project_root)
        if violation.field == "service_import"
    ]


def check_boundary_data_model_import_rule(
    context: ArchitectureInspectionContext,
) -> list[ArchitectureViolation]:
    return [
        violation
        for violation in _boundary_service_import_violations(context.project_root)
        if violation.field == "data_model_import"
    ]


def check_private_service_import_rule(
    context: ArchitectureInspectionContext,
) -> list[ArchitectureViolation]:
    return _private_service_import_violations(context.project_root)


def check_cli_improvement_intake_rule(
    context: ArchitectureInspectionContext,
) -> list[ArchitectureViolation]:
    return _cli_improvement_intake_violations(context.project_root)


def check_architecture_doc_rule(
    context: ArchitectureInspectionContext,
) -> list[ArchitectureViolation]:
    return _architecture_doc_violations(context.project_root)


def check_api_route_contract_rule(
    _context: ArchitectureInspectionContext,
) -> list[ArchitectureViolation]:
    return _api_route_contract_violations()


def check_agent_action_contract_rule(
    _context: ArchitectureInspectionContext,
) -> list[ArchitectureViolation]:
    return _agent_action_contract_violations()


def check_architecture_decision_rule(
    context: ArchitectureInspectionContext,
) -> list[ArchitectureViolation]:
    return _architecture_decision_violations(
        context.project_root,
        expected_contracts=context.expected_contracts,
    )


def check_capability_contract_rule(
    context: ArchitectureInspectionContext,
) -> list[ArchitectureViolation]:
    return _capability_contract_violations(context.project_root)


def check_architecture_map_drift_rule(
    context: ArchitectureInspectionContext,
) -> list[ArchitectureViolation]:
    return _architecture_map_drift_violations(
        context.project_root,
        current_map=context.current_map,
        map_path=context.map_path,
        default_map_path=context.default_map_path,
    )


def _validate_architecture_rule_registry(
    rules: tuple[ArchitectureRule, ...],
) -> tuple[ArchitectureRule, ...]:
    rule_ids = [rule.rule_id for rule in rules]
    duplicate_ids = sorted({rule_id for rule_id in rule_ids if rule_ids.count(rule_id) > 1})
    if duplicate_ids:
        raise ValueError(f"Duplicate architecture rule IDs: {', '.join(duplicate_ids)}")
    return rules

BOUNDARY_DOC_PATH = "docs/architecture_boundaries.md"
_ARCHITECTURE_RULE_DEFINITIONS = (
    (
        "api-bootstrap-no-feature-routes",
        "api_bootstrap_boundary",
        "API bootstrap must not define feature routes.",
        BOUNDARY_DOC_PATH,
        check_main_bootstrap_rule,
    ),
    (
        "api-bootstrap-no-feature-service-imports",
        "api_bootstrap_boundary",
        "API bootstrap must not import feature service modules.",
        BOUNDARY_DOC_PATH,
        check_main_service_import_rule,
    ),
    (
        "service-layer-no-api-imports",
        "service_layer_boundary",
        "Service modules must not import API bootstrap or router modules.",
        BOUNDARY_DOC_PATH,
        check_service_api_import_rule,
    ),
    (
        "boundary-modules-use-capability-facades",
        "capability_facade_boundary",
        "Boundary modules must use capability facades for core domains.",
        BOUNDARY_DOC_PATH,
        check_boundary_service_import_rule,
    ),
    (
        "boundary-modules-no-orm-model-imports",
        "capability_facade_boundary",
        "Boundary modules must not import ORM models directly.",
        BOUNDARY_DOC_PATH,
        check_boundary_data_model_import_rule,
    ),
    (
        "service-layer-no-private-service-imports",
        "service_layer_boundary",
        "Service modules must not import private service symbols.",
        BOUNDARY_DOC_PATH,
        check_private_service_import_rule,
    ),
    (
        "cli-delegates-improvement-intake",
        "improvement_intake_boundary",
        "CLI improvement imports must delegate to the intake facade.",
        BOUNDARY_DOC_PATH,
        check_cli_improvement_intake_rule,
    ),
    (
        "architecture-doc-required-tokens",
        "architecture_documentation",
        "Architecture documentation must name required boundary contracts.",
        BOUNDARY_DOC_PATH,
        check_architecture_doc_rule,
    ),
    (
        "api-route-capability-contracts",
        "api_route_capabilities",
        "API routes must satisfy the route capability contract.",
        "app/api/route_contracts.py",
        check_api_route_contract_rule,
    ),
    (
        "agent-action-catalog-contracts",
        "agent_action_catalog",
        "Agent actions must satisfy the machine-readable action catalog.",
        "app/services/agent_task_actions.py",
        check_agent_action_contract_rule,
    ),
    (
        "architecture-decision-contracts",
        "architecture_decisions",
        "Architecture decisions must be valid and linked to contracts.",
        "app/architecture_decisions.py",
        check_architecture_decision_rule,
    ),
    (
        "capability-surface-contracts",
        "capability_surface_contracts",
        "Capability facades must match their generated public surface.",
        "app/capability_contracts.py",
        check_capability_contract_rule,
    ),
    (
        "architecture-contract-map-drift",
        "architecture_contract_map",
        "Committed architecture contract map must match generated state.",
        "docs/architecture_contract_map.json",
        check_architecture_map_drift_rule,
    ),
)
ARCHITECTURE_RULES = _validate_architecture_rule_registry(
    tuple(
        ArchitectureRule(
            rule_id=rule_id,
            contract=contract,
            description=description,
            source_path=source_path,
            checker=checker,
        )
        for rule_id, contract, description, source_path, checker in _ARCHITECTURE_RULE_DEFINITIONS
    )
)


def list_architecture_rules() -> tuple[ArchitectureRule, ...]:
    return ARCHITECTURE_RULES


def build_architecture_rule_manifest() -> list[dict[str, object]]:
    return [rule.to_manifest() for rule in ARCHITECTURE_RULES]


def collect_architecture_rule_violations(
    project_root: Path,
    *,
    expected_contracts: tuple[str, ...],
    current_map: dict[str, Any],
    map_path: str | Path | None,
    default_map_path: Path,
) -> list[ArchitectureViolation]:
    context = ArchitectureInspectionContext(
        project_root=project_root,
        expected_contracts=expected_contracts,
        current_map=current_map,
        map_path=map_path,
        default_map_path=default_map_path,
    )
    return [violation for rule in ARCHITECTURE_RULES for violation in rule.check(context)]
