from __future__ import annotations

import ast
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = PROJECT_ROOT / "config/production_trap_set_centrality_budget.yaml"


def _load_policy() -> dict[str, object]:
    return yaml.safe_load(POLICY_PATH.read_text())


def _collect_unique_internal_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app."):
                    imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("app."):
                imports.add(node.module)
    return imports


def test_trap_set_unique_internal_import_budgets_hold() -> None:
    policy = _load_policy()

    for relative_path, budget in policy["unique_internal_import_budgets"].items():
        imports = _collect_unique_internal_imports(PROJECT_ROOT / relative_path)

        assert len(imports) <= budget["max_unique_internal_import_count"]
        assert budget["max_unique_internal_import_count"] < budget[
            "baseline_unique_internal_import_count"
        ]


def test_trap_set_unique_internal_import_budget_detects_extra_owner_import() -> None:
    fixture = Path("<trap-set-budget-fixture>")
    imports = _collect_unique_internal_imports_from_text(
        fixture,
        "\n".join(
            [
                "from app.services.search_harnesses import get_search_harness",
                "from app.services.search_query_features import classify_query_intent",
            ]
        ),
    )

    assert len(imports) == 2
    assert len(imports) > 1


def _collect_unique_internal_imports_from_text(path: Path, source: str) -> set[str]:
    tree = ast.parse(source, filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app."):
                    imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("app."):
                imports.add(node.module)
    return imports
