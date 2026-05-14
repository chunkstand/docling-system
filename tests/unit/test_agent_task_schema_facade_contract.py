from __future__ import annotations

import ast
from pathlib import Path

import app.schemas.agent_task_claim_support as agent_task_claim_support
import app.schemas.agent_task_core as agent_task_core
import app.schemas.agent_task_reports as agent_task_reports
import app.schemas.agent_task_search_workflows as agent_task_search_workflows
import app.schemas.agent_task_semantic_generation as agent_task_semantic_generation
import app.schemas.agent_task_semantic_graph as agent_task_semantic_graph
import app.schemas.agent_task_semantics as agent_task_semantics
import app.schemas.agent_tasks as agent_tasks

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FACADE_PATH = PROJECT_ROOT / "app/schemas/agent_tasks.py"
SCHEMA_DIR = PROJECT_ROOT / "app/schemas"
OWNER_MODULES = (
    agent_task_core,
    agent_task_claim_support,
    agent_task_reports,
    agent_task_search_workflows,
    agent_task_semantic_generation,
    agent_task_semantic_graph,
    agent_task_semantics,
)
OWNER_IMPORT_ALIASES = {
    "agent_task_core": "_agent_task_core",
    "agent_task_claim_support": "_agent_task_claim_support",
    "agent_task_reports": "_agent_task_reports",
    "agent_task_search_workflows": "_agent_task_search_workflows",
    "agent_task_semantic_generation": "_agent_task_semantic_generation",
    "agent_task_semantic_graph": "_agent_task_semantic_graph",
    "agent_task_semantics": "_agent_task_semantics",
}
FORBIDDEN_EXPORT_SINKS = (
    SCHEMA_DIR / "_agent_task_schema_exports.py",
    SCHEMA_DIR / "agent_task_export_catalog.py",
)


def _load_facade_tree(source: str | None = None) -> ast.Module:
    text = FACADE_PATH.read_text() if source is None else source
    filename = str(FACADE_PATH) if source is None else "<agent-task-facade-fixture>"
    return ast.parse(text, filename=filename)


def _owner_exports() -> dict[str, object]:
    exports: dict[str, object] = {}
    for module in OWNER_MODULES:
        for name in module.__all__:
            exports[name] = module
    return exports


def _collect_facade_contract_violations(tree: ast.Module) -> list[tuple[str, object]]:
    violations: list[tuple[str, object]] = []

    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                aliases = {(alias.name, alias.asname) for alias in node.names}
                if aliases != {("annotations", None)}:
                    violations.append(("unexpected_future_import", aliases))
                continue
            if node.module == "typing":
                aliases = {(alias.name, alias.asname) for alias in node.names}
                if aliases != {("Any", "_Any")}:
                    violations.append(("unexpected_typing_import", aliases))
                continue
            if node.module != "app.schemas":
                violations.append(("unexpected_import_from_module", node.module))
                continue
            aliases = [(alias.name, alias.asname) for alias in node.names]
            if len(aliases) != 1:
                violations.append(("unexpected_owner_import_shape", aliases))
                continue
            name, asname = aliases[0]
            if OWNER_IMPORT_ALIASES.get(name) != asname:
                violations.append(("unexpected_owner_import_alias", aliases[0]))
            continue

        if isinstance(node, ast.AnnAssign):
            if not isinstance(node.target, ast.Name) or node.target.id != "_OWNER_MODULES":
                violations.append(("unexpected_annotated_assignment_target", ast.dump(node)))
            continue

        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                violations.append(("unexpected_assignment_shape", ast.dump(node)))
                continue
            target_name = node.targets[0].id
            if target_name not in {"_EXPORT_REGISTRY", "__all__"}:
                violations.append(("unexpected_assignment_target", target_name))
            continue

        if isinstance(node, ast.FunctionDef):
            if node.name not in {"__getattr__", "__dir__"}:
                violations.append(("unexpected_function", node.name))
            continue

        if isinstance(node, ast.ClassDef):
            violations.append(("unexpected_class", node.name))
            continue

        violations.append(("unexpected_top_level_statement", type(node).__name__))

    return violations


def _collect_production_import_violations(root: Path) -> list[str]:
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "app.schemas.agent_tasks":
                violations.append(str(path.relative_to(root)))
                break
            if isinstance(node, ast.Import):
                if any(alias.name == "app.schemas.agent_tasks" for alias in node.names):
                    violations.append(str(path.relative_to(root)))
                    break
    return violations


def test_agent_task_schema_facade_public_surface_matches_owner_exports() -> None:
    expected_exports = _owner_exports()

    assert agent_tasks.__all__ == sorted(expected_exports)
    assert len(agent_tasks.__all__) == len(expected_exports)


def test_agent_task_schema_facade_exports_resolve_to_owner_objects() -> None:
    for name, module in _owner_exports().items():
        assert getattr(agent_tasks, name) is getattr(module, name)


def test_agent_task_schema_facade_contains_only_allowed_top_level_structure() -> None:
    violations = _collect_facade_contract_violations(_load_facade_tree())

    assert violations == []
    assert sum(1 for _ in FACADE_PATH.open(encoding="utf-8")) <= 160


def test_agent_task_schema_facade_has_no_export_sink_file() -> None:
    assert [path.name for path in FORBIDDEN_EXPORT_SINKS if path.exists()] == []


def test_agent_task_schema_facade_has_no_production_app_importers() -> None:
    assert _collect_production_import_violations(PROJECT_ROOT / "app") == []


def test_agent_task_schema_facade_flags_direct_production_import_fixture(
    tmp_path: Path,
) -> None:
    fixture_root = tmp_path / "app"
    fixture_root.mkdir()
    (fixture_root / "example.py").write_text(
        "from app.schemas.agent_tasks import AgentTaskCreateRequest\n",
        encoding="utf-8",
    )

    assert _collect_production_import_violations(fixture_root) == ["example.py"]


def test_agent_task_schema_facade_rejects_unexpected_public_export() -> None:
    tree = _load_facade_tree(
        FACADE_PATH.read_text()
        + "\nUnexpectedHelper = _agent_task_core.AgentTaskCreateRequest\n"
    )

    violations = _collect_facade_contract_violations(tree)

    assert ("unexpected_assignment_target", "UnexpectedHelper") in violations


def test_agent_task_schema_facade_rejects_direct_schema_growth() -> None:
    tree = _load_facade_tree(
        FACADE_PATH.read_text() + "\nclass NewTaskInput(BaseModel):\n    pass\n"
    )

    assert ("unexpected_class", "NewTaskInput") in _collect_facade_contract_violations(tree)
