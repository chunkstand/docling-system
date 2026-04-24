from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN_PATH = ROOT / "app/api/main.py"
SERVICES_DIR = ROOT / "app/services"
BOUNDARY_DIRS = (ROOT / "app/api/routers", ROOT / "app/workers")
APP_ROUTE_DECORATORS = {"get", "post", "put", "delete", "patch"}
FORBIDDEN_SERVICE_IMPORT_PREFIXES = ("app.api.main", "app.api.routers")
ALLOWED_MAIN_SERVICE_IMPORTS = {"app.services.runtime"}
FORBIDDEN_BOUNDARY_SERVICE_IMPORTS = (
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
)


def _iter_import_targets(tree: ast.AST) -> list[str]:
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.append(node.module)
    return targets


def test_main_is_bootstrap_only_and_defines_no_feature_routes() -> None:
    tree = ast.parse(MAIN_PATH.read_text())
    offenders: list[tuple[str, int]] = []
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
                offenders.append((node.name, node.lineno))
    assert offenders == []


def test_main_imports_no_feature_service_modules() -> None:
    tree = ast.parse(MAIN_PATH.read_text(), filename=str(MAIN_PATH))
    service_imports = sorted(
        {
            target
            for target in _iter_import_targets(tree)
            if target.startswith("app.services") and target not in ALLOWED_MAIN_SERVICE_IMPORTS
        }
    )
    assert service_imports == []


def test_service_modules_do_not_import_api_bootstrap_or_router_modules() -> None:
    violations: list[tuple[str, str]] = []
    for path in sorted(SERVICES_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for target in _iter_import_targets(tree):
            if target.startswith(FORBIDDEN_SERVICE_IMPORT_PREFIXES):
                violations.append((str(path.relative_to(ROOT)), target))
    assert violations == []


def test_api_and_worker_boundaries_use_capability_interfaces_for_core_domains() -> None:
    violations: list[tuple[str, str]] = []
    for boundary_dir in BOUNDARY_DIRS:
        for path in sorted(boundary_dir.rglob("*.py")):
            tree = ast.parse(path.read_text(), filename=str(path))
            for target in _iter_import_targets(tree):
                if target in FORBIDDEN_BOUNDARY_SERVICE_IMPORTS:
                    violations.append((str(path.relative_to(ROOT)), target))
    assert violations == []


def test_service_modules_do_not_import_private_symbols_from_other_service_modules() -> None:
    violations: list[tuple[str, str, str]] = []
    for path in sorted(SERVICES_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module is None or not node.module.startswith("app.services"):
                continue
            for alias in node.names:
                if alias.name.startswith("_"):
                    violations.append((str(path.relative_to(ROOT)), node.module, alias.name))
    assert violations == []
