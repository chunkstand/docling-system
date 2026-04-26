from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from app.api.main import create_app
from app.api.route_contracts import validate_api_route_capability_contracts
from app.architecture_decisions import validate_architecture_decisions
from app.architecture_inspection_types import ArchitectureViolation
from app.capability_contracts import validate_capability_contracts
from app.services.agent_task_actions import validate_agent_task_action_contracts

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
FORBIDDEN_BOUNDARY_DATA_MODEL_IMPORTS = frozenset({"app.db.models"})
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
        "app.db.models",
        "app.architecture_decisions",
        "docs/architecture_decisions.yaml",
        "app.services.improvement_case_intake",
        "ImprovementCaseImportRequest",
        "ImprovementCaseImportResult",
    }
)


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
            if not _matches_module_or_submodule(node.module, "app.services.improvement_cases"):
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
            if not _matches_module_or_submodule(
                module_arg.value,
                "app.services.improvement_cases",
            ):
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


def collect_architecture_rule_violations(
    project_root: Path,
    *,
    expected_contracts: tuple[str, ...],
    current_map: dict[str, Any],
    map_path: str | Path | None,
    default_map_path: Path,
) -> list[ArchitectureViolation]:
    return [
        *_main_bootstrap_violations(project_root),
        *_main_service_import_violations(project_root),
        *_service_api_import_violations(project_root),
        *_boundary_service_import_violations(project_root),
        *_private_service_import_violations(project_root),
        *_cli_improvement_intake_violations(project_root),
        *_architecture_doc_violations(project_root),
        *_api_route_contract_violations(),
        *_agent_action_contract_violations(),
        *_architecture_decision_violations(project_root, expected_contracts=expected_contracts),
        *_capability_contract_violations(project_root),
        *_architecture_map_drift_violations(
            project_root,
            current_map=current_map,
            map_path=map_path,
            default_map_path=default_map_path,
        ),
    ]
