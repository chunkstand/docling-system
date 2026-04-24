from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN_PATH = ROOT / "app/api/main.py"
SERVICES_DIR = ROOT / "app/services"
APP_ROUTE_DECORATORS = {"get", "post", "put", "delete", "patch"}
FORBIDDEN_SERVICE_IMPORT_PREFIXES = ("app.api.main", "app.api.routers")


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


def test_service_modules_do_not_import_api_bootstrap_or_router_modules() -> None:
    violations: list[tuple[str, str]] = []
    for path in sorted(SERVICES_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for target in _iter_import_targets(tree):
            if target.startswith(FORBIDDEN_SERVICE_IMPORT_PREFIXES):
                violations.append((str(path.relative_to(ROOT)), target))
    assert violations == []
