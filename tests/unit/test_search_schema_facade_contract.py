from __future__ import annotations

import ast
from pathlib import Path

import app.schemas.search as search
import app.schemas.search_core as search_core
import app.schemas.search_explanations as search_explanations
import app.schemas.search_harness as search_harness
import app.schemas.search_history as search_history
import app.schemas.search_learning as search_learning
import app.schemas.search_replays as search_replays

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FACADE_PATH = PROJECT_ROOT / "app/schemas/search.py"
SCHEMA_DIR = PROJECT_ROOT / "app/schemas"
OWNER_MODULES = (
    search_core,
    search_history,
    search_explanations,
    search_replays,
    search_harness,
    search_learning,
)
OWNER_IMPORT_ALIASES = {
    "search_core": "_search_core",
    "search_history": "_search_history",
    "search_explanations": "_search_explanations",
    "search_replays": "_search_replays",
    "search_harness": "_search_harness",
    "search_learning": "_search_learning",
}
FORBIDDEN_EXPORT_SINKS = (
    SCHEMA_DIR / "_search_schema_exports.py",
    SCHEMA_DIR / "search_export_catalog.py",
)


def _load_facade_tree(source: str | None = None) -> ast.Module:
    text = FACADE_PATH.read_text() if source is None else source
    filename = str(FACADE_PATH) if source is None else "<search-facade-fixture>"
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
            if node.targets[0].id not in {"_EXPORT_REGISTRY", "__all__"}:
                violations.append(("unexpected_assignment_target", node.targets[0].id))
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


def test_search_schema_facade_public_surface_matches_owner_exports() -> None:
    expected_exports = _owner_exports()
    assert search.__all__ == sorted(expected_exports)
    assert len(search.__all__) == len(expected_exports)


def test_search_schema_facade_exports_resolve_to_owner_objects() -> None:
    for name, module in _owner_exports().items():
        assert getattr(search, name) is getattr(module, name)


def test_search_schema_facade_contains_only_allowed_top_level_structure() -> None:
    assert _collect_facade_contract_violations(_load_facade_tree()) == []
    assert sum(1 for _ in FACADE_PATH.open(encoding="utf-8")) <= 120


def test_search_schema_facade_has_no_export_sink_file() -> None:
    assert [path.name for path in FORBIDDEN_EXPORT_SINKS if path.exists()] == []


def test_search_schema_facade_rejects_unexpected_public_export() -> None:
    tree = _load_facade_tree(
        FACADE_PATH.read_text() + "\nUnexpectedHelper = _search_core.SearchRequest\n"
    )
    violations = _collect_facade_contract_violations(tree)

    assert ("unexpected_assignment_target", "UnexpectedHelper") in violations


def test_search_schema_facade_rejects_direct_schema_growth() -> None:
    tree = _load_facade_tree(
        FACADE_PATH.read_text() + "\nclass NewSearchSchema(BaseModel):\n    pass\n"
    )
    assert ("unexpected_class", "NewSearchSchema") in _collect_facade_contract_violations(tree)
