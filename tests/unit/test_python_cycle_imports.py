from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SEARCH_CYCLE_PATHS = [
    ROOT / "app/services/search.py",
    ROOT / "app/services/search_execution_persistence.py",
    ROOT / "app/services/search_harnesses.py",
    ROOT / "app/services/search_hydration.py",
    ROOT / "app/services/search_metadata_supplement.py",
    ROOT / "app/services/search_retrieval_primitives.py",
]
SERVICE_CYCLE_IMPORT_PATHS = [
    ROOT / "app/services/docling_parser.py",
    ROOT / "app/services/docling_parser_tables.py",
    ROOT / "app/services/evaluation_scoring.py",
    ROOT / "app/services/evaluations.py",
    ROOT / "app/services/runs.py",
    ROOT / "app/services/semantic_governance.py",
    ROOT / "app/services/semantic_governance_audit.py",
    ROOT / "app/services/semantic_governance_context.py",
    ROOT / "app/services/semantic_governance_events.py",
]
CYCLE_BOUNDARY_PATHS = [
    ROOT / "app/services/evidence_provenance_export_graph_core.py",
    ROOT / "app/services/evidence_provenance_export_graph_report.py",
    ROOT / "app/services/evidence_search_packages.py",
    ROOT / "app/services/evidence_search_trace_store.py",
]


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(), filename=str(path))


def _import_targets(tree: ast.AST) -> set[str]:
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.add(node.module)
    return targets


def _nested_import_lines(tree: ast.AST) -> list[int]:
    lines: list[int] = []

    def visit(node: ast.AST, *, nested: bool = False) -> None:
        is_nested_scope = nested or isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda),
        )
        if is_nested_scope and isinstance(node, (ast.Import, ast.ImportFrom)):
            lines.append(node.lineno)
        for child in ast.iter_child_nodes(node):
            visit(child, nested=is_nested_scope)

    visit(tree)
    return lines


def test_search_cycle_modules_use_explicit_submodule_imports() -> None:
    for path in [*SEARCH_CYCLE_PATHS, *SERVICE_CYCLE_IMPORT_PATHS]:
        targets = _import_targets(_parse(path))
        assert "app.services" not in targets, path.name
        assert "app.core" not in targets, path.name


def test_cycle_boundary_modules_keep_imports_at_module_scope() -> None:
    for path in [*SEARCH_CYCLE_PATHS, *CYCLE_BOUNDARY_PATHS]:
        assert _nested_import_lines(_parse(path)) == [], path.name


def test_evidence_cycle_modules_do_not_back_import_each_other() -> None:
    report_path = ROOT / "app/services/evidence_provenance_export_graph_report.py"
    trace_store_path = ROOT / "app/services/evidence_search_trace_store.py"
    report_targets = _import_targets(_parse(report_path))
    trace_store_targets = _import_targets(_parse(trace_store_path))

    assert "app.services.evidence_provenance_export_graph_core" not in report_targets
    assert "app.services.evidence_search_packages" not in trace_store_targets


def test_cycle_import_helpers_reject_controlled_violations() -> None:
    package_import_tree = ast.parse("from app.services import search_ranking\n")
    nested_import_tree = ast.parse(
        "def build():\n"
        "    from app.services.evidence_search_packages import get_search_evidence_package\n"
    )

    assert "app.services" in _import_targets(package_import_tree)
    assert _nested_import_lines(nested_import_tree) == [2]
