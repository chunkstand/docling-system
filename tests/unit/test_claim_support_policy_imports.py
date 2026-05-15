from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROMOTIONS_PATH = ROOT / "app" / "services" / "claim_support_replay_alert_promotions.py"


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


def test_replay_alert_promotions_does_not_import_policy_impact_facade() -> None:
    targets = _iter_import_targets(PROMOTIONS_PATH)

    assert not any(
        _matches_module_or_submodule(target, "app.services.claim_support_policy_impacts")
        for target in targets
    )
