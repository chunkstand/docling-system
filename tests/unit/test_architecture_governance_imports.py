from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURE_DECISIONS_PATH = ROOT / "app" / "architecture_decisions.py"
ARCHITECTURE_INSPECTION_PATH = ROOT / "app" / "architecture_inspection.py"


def _iter_import_targets(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.add(node.module)
    return targets


def _matches_module_or_submodule(target: str, module: str) -> bool:
    return target == module or target.startswith(f"{module}.")


def test_architecture_decisions_does_not_import_inspection_module() -> None:
    targets = _iter_import_targets(ARCHITECTURE_DECISIONS_PATH)

    assert not any(
        _matches_module_or_submodule(target, "app.architecture_inspection")
        for target in targets
    )


def test_architecture_inspection_uses_contract_only_metadata_imports() -> None:
    targets = _iter_import_targets(ARCHITECTURE_INSPECTION_PATH)

    assert "app.services.agent_actions.contracts" in targets
    assert "app.services.improvement_case_contracts" in targets
    assert not any(
        _matches_module_or_submodule(target, "app.services.agent_task_actions")
        for target in targets
    )
    assert not any(
        _matches_module_or_submodule(target, "app.services.improvement_case_intake")
        for target in targets
    )
