from __future__ import annotations

import ast
import importlib
from pathlib import Path

import yaml

from tests.db_model_contract import PUBLIC_DB_FACADE_EXPORT_SYMBOLS, PUBLIC_DB_MODELS_EXPORT_SYMBOLS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DB_PACKAGE_ROOT = PROJECT_ROOT / "app/db/public"
POLICY_PATH = PROJECT_ROOT / "config/db_model_import_policy.yaml"


def _iter_project_python_paths() -> list[Path]:
    paths: list[Path] = []
    for path in PROJECT_ROOT.rglob("*.py"):
        relative = path.relative_to(PROJECT_ROOT)
        if any(part in {".venv", "__pycache__", "build", "storage"} for part in relative.parts):
            continue
        paths.append(path)
    return sorted(paths)


def _load_policy() -> dict[str, object]:
    return yaml.safe_load(POLICY_PATH.read_text())


def _collect_import_paths(target_module: str) -> dict[str, list[int]]:
    matches: dict[str, list[int]] = {}
    for path in _iter_project_python_paths():
        tree = ast.parse(path.read_text(), filename=str(path))
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == target_module:
                        matches.setdefault(relative, []).append(node.lineno)
            elif isinstance(node, ast.ImportFrom) and node.module == target_module:
                matches.setdefault(relative, []).append(node.lineno)
    return matches


def _collect_prefixed_import_paths(target_prefix: str) -> dict[str, list[int]]:
    matches: dict[str, list[int]] = {}
    for path in _iter_project_python_paths():
        tree = ast.parse(path.read_text(), filename=str(path))
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                targets = (alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                targets = (node.module,)
            else:
                continue
            for target in targets:
                if target == target_prefix or target.startswith(f"{target_prefix}."):
                    matches.setdefault(relative, []).append(node.lineno)
    return matches


def test_public_db_facades_export_exact_domain_symbols() -> None:
    for module_name, expected_symbols in PUBLIC_DB_FACADE_EXPORT_SYMBOLS.items():
        module = __import__(f"app.db.public.{module_name}", fromlist=["__all__"])

        assert module.__all__ == expected_symbols


def test_public_db_facades_preserve_legacy_symbol_identity() -> None:
    legacy_model_module = importlib.import_module("app.db.models")

    for module_name, exported_symbols in PUBLIC_DB_FACADE_EXPORT_SYMBOLS.items():
        module = __import__(f"app.db.public.{module_name}", fromlist=["__all__"])
        for symbol_name in exported_symbols:
            assert getattr(module, symbol_name) is getattr(legacy_model_module, symbol_name)


def test_public_db_package_root_does_not_regrow_a_broad_symbol_surface() -> None:
    module = __import__("app.db.public", fromlist=["__all__"])
    root_public_names = {
        name for name in vars(module) if not name.startswith("_") and name != "annotations"
    }

    assert root_public_names.isdisjoint(PUBLIC_DB_MODELS_EXPORT_SYMBOLS)


def test_db_models_direct_import_allowlist_is_exact() -> None:
    policy = _load_policy()
    actual_paths = _collect_import_paths("app.db.models")
    expected_paths = set(policy["legacy_db_models_allowlist"])

    assert set(actual_paths) == expected_paths

    total_count = len(actual_paths)
    app_count = sum(1 for path in actual_paths if path.startswith("app/"))
    tests_count = sum(1 for path in actual_paths if path.startswith("tests/"))
    expected_counts = policy["expected_direct_import_counts"]

    assert total_count == expected_counts["total"]
    assert app_count == expected_counts["app"]
    assert tests_count == expected_counts["tests"]


def test_db_models_direct_import_prefix_counts_match_policy() -> None:
    policy = _load_policy()
    actual_paths = _collect_import_paths("app.db.models")

    for prefix, expected_count in policy["expected_direct_import_prefix_counts"].items():
        actual_count = sum(1 for path in actual_paths if path.startswith(prefix))

        assert actual_count == expected_count


def test_model_domains_imports_stay_internal_to_app_db_and_compatibility_tests() -> None:
    policy = _load_policy()
    allowed_prefixes = tuple(policy["allowed_model_domain_import_roots"])
    allowed_files = set(policy["allowed_model_domain_import_files"])
    actual_paths = _collect_prefixed_import_paths("app.db.model_domains")

    violations = [
        path
        for path in actual_paths
        if not path.startswith(allowed_prefixes) and path not in allowed_files
    ]

    assert violations == []


def test_direct_db_models_import_policy_rejects_non_allowlisted_import() -> None:
    fixture = ast.parse("from app.db.models import Document\n")
    violations: list[int] = []

    for node in ast.walk(fixture):
        if isinstance(node, ast.ImportFrom) and node.module == "app.db.models":
            violations.append(node.lineno)

    assert violations == [1]


def test_direct_model_domains_import_policy_rejects_external_import() -> None:
    fixture = ast.parse("from app.db.model_domains.claim_support import ClaimSupportEvaluation\n")
    violations: list[int] = []

    for node in ast.walk(fixture):
        if isinstance(node, ast.ImportFrom) and node.module == "app.db.model_domains.claim_support":
            violations.append(node.lineno)

    assert violations == [1]
