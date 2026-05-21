from __future__ import annotations

import ast
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = PROJECT_ROOT / "config/production_trap_set_centrality_budget.yaml"


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


def _collect_import_paths(target_module: str, *, root: Path = PROJECT_ROOT) -> dict[str, list[int]]:
    matches: dict[str, list[int]] = {}
    for path in root.rglob("*.py"):
        relative = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == target_module:
                        matches.setdefault(relative, []).append(node.lineno)
            elif isinstance(node, ast.ImportFrom) and node.module == target_module:
                matches.setdefault(relative, []).append(node.lineno)
    return matches


def test_trap_set_direct_import_allowlists_are_exact() -> None:
    policy = _load_policy()

    for module_name, budget in policy["direct_import_budgets"].items():
        actual_paths = _collect_import_paths(module_name)
        expected_paths = set(budget["allowlist"])
        expected_counts = budget["expected_direct_import_counts"]

        assert set(actual_paths) == expected_paths
        assert len(actual_paths) == expected_counts["total"]
        assert sum(1 for path in actual_paths if path.startswith("app/")) == expected_counts["app"]
        assert sum(1 for path in actual_paths if path.startswith("tests/")) == expected_counts[
            "tests"
        ]
        assert expected_counts["total"] <= budget["max_direct_import_count"]
        assert budget["max_direct_import_count"] < budget["baseline_direct_import_count"]


def test_trap_set_direct_import_policy_flags_non_allowlisted_fixture_import(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixture"
    fixture_root.mkdir()
    (fixture_root / "example.py").write_text(
        "from app.services.evidence import payload_sha256\n",
        encoding="utf-8",
    )

    assert _collect_import_paths("app.services.evidence", root=fixture_root) == {"example.py": [1]}
