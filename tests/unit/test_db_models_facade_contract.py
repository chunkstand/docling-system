from __future__ import annotations

import ast
from pathlib import Path

import app.db.models as model_module
from tests.db_model_contract import (
    ALLOWED_DB_MODELS_SUPPORT_SYMBOLS,
    PUBLIC_DB_MODELS_EXPORT_SYMBOLS,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PACKAGE_ROOT = (PROJECT_ROOT / "app/db").resolve()
MODELS_PATH = PROJECT_ROOT / "app/db/models.py"
ALLOWED_IMPORT_MODULES = frozenset(
    {
        "__future__",
        "app.db._model_enums",
        "app.db.model_domains",
        "app.db.model_domains.document_artifacts",
        "app.db.model_domains.ingest",
        "app.db.model_domains.platform",
    }
)
ALLOWED_PRIVATE_SUPPORT_IMPORTERS = frozenset(
    {
        (PROJECT_ROOT / "tests/unit/test_db_model_import_compatibility.py").resolve(),
    }
)
ALLOWED_DELAYED_IMPORTS = {
    "_audit_and_evidence_domain": "app.db.model_domains.audit_and_evidence",
    "_semantic_memory_domain": "app.db.model_domains.semantic_memory",
}


def _load_models_tree(source: str | None = None) -> ast.Module:
    text = MODELS_PATH.read_text() if source is None else source
    filename = str(MODELS_PATH) if source is None else "<db-models-facade-fixture>"
    return ast.parse(text, filename=filename)


def _collect_facade_contract_violations(tree: ast.Module) -> list[dict[str, object]]:
    violations: list[dict[str, object]] = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            aliases = {(alias.name, alias.asname) for alias in node.names}
            if aliases != {("importlib", "_importlib")}:
                violations.append(
                    {
                        "category": "unexpected_import",
                        "line": node.lineno,
                        "detail": aliases,
                    }
                )
            continue

        if isinstance(node, ast.ImportFrom):
            if node.module not in ALLOWED_IMPORT_MODULES:
                violations.append(
                    {
                        "category": "unexpected_import_from_module",
                        "line": node.lineno,
                        "detail": node.module,
                    }
                )
                continue
            if node.module == "__future__":
                aliases = {(alias.name, alias.asname) for alias in node.names}
                if aliases != {("annotations", None)}:
                    violations.append(
                        {
                            "category": "unexpected_future_import",
                            "line": node.lineno,
                            "detail": aliases,
                        }
                )
                continue
            for alias in node.names:
                exported_name = alias.asname or alias.name
                if alias.asname is not None:
                    if (
                        alias.asname == alias.name
                        and exported_name in PUBLIC_DB_MODELS_EXPORT_SYMBOLS
                    ):
                        continue
                    if not alias.asname.startswith("_"):
                        violations.append(
                            {
                                "category": "non_private_support_import",
                                "line": node.lineno,
                                "detail": alias.asname,
                            }
                        )
                    continue
                if exported_name not in PUBLIC_DB_MODELS_EXPORT_SYMBOLS:
                    violations.append(
                        {
                            "category": "unexpected_direct_public_import",
                            "line": node.lineno,
                            "detail": exported_name,
                        }
                    )
            continue

        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                violations.append(
                    {
                        "category": "unexpected_assignment_shape",
                        "line": node.lineno,
                        "detail": ast.dump(node, include_attributes=False),
                    }
                )
                continue
            target_name = node.targets[0].id
            if target_name in ALLOWED_DELAYED_IMPORTS:
                if not (
                    isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Attribute)
                    and isinstance(node.value.func.value, ast.Name)
                    and node.value.func.value.id == "_importlib"
                    and node.value.func.attr == "import_module"
                    and len(node.value.args) == 1
                    and isinstance(node.value.args[0], ast.Constant)
                    and node.value.args[0].value == ALLOWED_DELAYED_IMPORTS[target_name]
                    and not node.value.keywords
                ):
                    violations.append(
                        {
                            "category": "unexpected_delayed_import",
                            "line": node.lineno,
                            "detail": target_name,
                        }
                    )
                continue
            if target_name not in PUBLIC_DB_MODELS_EXPORT_SYMBOLS:
                violations.append(
                    {
                        "category": "unexpected_assignment_target",
                        "line": node.lineno,
                        "detail": target_name,
                    }
                )
                continue
            if not (
                isinstance(node.value, ast.Attribute)
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id.startswith("_")
                and node.value.attr == target_name
            ):
                violations.append(
                    {
                        "category": "unexpected_forwarder_assignment",
                        "line": node.lineno,
                        "detail": target_name,
                    }
                )
            continue

        if isinstance(node, ast.ClassDef):
            violations.append(
                {
                    "category": "unexpected_class",
                    "line": node.lineno,
                    "detail": node.name,
                }
            )
            continue

        violations.append(
            {
                "category": "unexpected_top_level_statement",
                "line": getattr(node, "lineno", 0),
                "detail": type(node).__name__,
            }
        )

    return violations


def test_db_models_facade_public_surface_is_exact() -> None:
    public_names = {name for name in vars(model_module) if not name.startswith("_")}

    assert public_names == set(PUBLIC_DB_MODELS_EXPORT_SYMBOLS) | set(
        ALLOWED_DB_MODELS_SUPPORT_SYMBOLS
    )


def test_db_models_facade_contains_only_allowed_structure() -> None:
    violations = _collect_facade_contract_violations(_load_models_tree())

    assert violations == []


def test_db_models_private_enum_support_module_is_not_a_second_public_surface() -> None:
    violations: list[str] = []

    for path in PROJECT_ROOT.rglob("*.py"):
        if ".venv" in path.parts:
            continue
        resolved_path = path.resolve()
        if resolved_path.is_relative_to(DB_PACKAGE_ROOT):
            continue
        if resolved_path in ALLOWED_PRIVATE_SUPPORT_IMPORTERS:
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "app.db._model_enums":
                violations.append(str(path.relative_to(PROJECT_ROOT)))
                break
            if isinstance(node, ast.Import):
                if any(alias.name == "app.db._model_enums" for alias in node.names):
                    violations.append(str(path.relative_to(PROJECT_ROOT)))
                    break

    assert violations == []


def test_db_models_facade_rejects_unexpected_public_export() -> None:
    tree = _load_models_tree(
        MODELS_PATH.read_text()
        + "\nUnexpectedHelper = _agent_tasks_domain.AgentTask\n"
    )

    violations = _collect_facade_contract_violations(tree)

    assert ("unexpected_assignment_target", "UnexpectedHelper") in {
        (violation["category"], violation["detail"]) for violation in violations
    }


def test_db_models_facade_rejects_direct_orm_class_growth() -> None:
    tree = _load_models_tree(
        MODELS_PATH.read_text()
        + "\nclass NewRuntimeRow(Base):\n    pass\n"
    )

    violations = _collect_facade_contract_violations(tree)

    assert ("unexpected_class", "NewRuntimeRow") in {
        (violation["category"], violation["detail"]) for violation in violations
    }


def test_db_models_facade_rejects_schema_call_growth() -> None:
    tree = _load_models_tree(
        MODELS_PATH.read_text()
        + "\nmetadata_column = mapped_column(Integer)\n"
    )

    violations = _collect_facade_contract_violations(tree)

    assert ("unexpected_assignment_target", "metadata_column") in {
        (violation["category"], violation["detail"]) for violation in violations
    }
