from __future__ import annotations

import ast
from pathlib import Path

import app.services.audit_bundle_release_imports as release_imports
from app.services import audit_bundles

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_BUNDLES_PATH = PROJECT_ROOT / "app/services/audit_bundles.py"

AUDIT_BUNDLE_FACADE_ALIASES = {
    "canonical_json_bytes": release_imports.canonical_json_bytes,
    "create_retrieval_training_run_audit_bundle_row": (
        release_imports.create_retrieval_training_run_audit_bundle_row
    ),
    "ensure_audit_bundle_validation_receipts": (
        release_imports.ensure_audit_bundle_validation_receipts
    ),
    "ensure_retrieval_training_run_audit_bundles_for_release": (
        release_imports.ensure_retrieval_training_run_audit_bundles_for_release
    ),
    "release_payloads_module": release_imports.release_payloads_module,
    "release_shared_module": release_imports.release_shared_module,
    "validation_receipt_runtime": release_imports.validation_receipt_runtime,
    "validation_receipts_module": release_imports.validation_receipts_module,
}

ALLOWED_PUBLIC_FUNCTIONS = {
    "create_search_harness_release_audit_bundle",
    "create_retrieval_training_run_audit_bundle",
    "get_audit_bundle_export",
    "create_audit_bundle_validation_receipt",
    "list_audit_bundle_validation_receipts",
    "get_audit_bundle_validation_receipt",
    "get_latest_audit_bundle_validation_receipt",
    "get_latest_retrieval_training_run_audit_bundle",
    "get_latest_search_harness_release_audit_bundle",
}

ALLOWED_PRIVATE_FUNCTIONS = {
    "_audit_bundle_not_found",
    "_receipt_not_found",
    "_training_run_not_found",
    "_training_run_not_completed",
    "_signing_key",
    "_signature",
    "_bundle_without_bundle_sha256",
    "_bundle_sha256",
    "_signed_bundle",
    "_to_summary",
    "_verify_bundle",
    "_response",
    "_get_audit_bundle_row",
}


def _load_audit_bundles_tree() -> ast.Module:
    return ast.parse(AUDIT_BUNDLES_PATH.read_text(), filename=str(AUDIT_BUNDLES_PATH))


def test_audit_bundles_facade_reexports_release_payload_owner_helpers() -> None:
    assert (
        audit_bundles.SEARCH_RELEASE_AUDIT_BUNDLE_KIND
        == release_imports.SEARCH_RELEASE_AUDIT_BUNDLE_KIND
    )
    assert (
        audit_bundles.SEARCH_RELEASE_SOURCE_TABLE
        == release_imports.SEARCH_RELEASE_SOURCE_TABLE
    )
    assert (
        audit_bundles.TRAINING_RUN_AUDIT_BUNDLE_KIND
        == release_imports.TRAINING_RUN_AUDIT_BUNDLE_KIND
    )
    for facade_name, owner_symbol in AUDIT_BUNDLE_FACADE_ALIASES.items():
        assert getattr(audit_bundles, facade_name) is owner_symbol


def test_audit_bundles_facade_function_surface_is_exact() -> None:
    tree = _load_audit_bundles_tree()
    function_names = {
        node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert function_names == ALLOWED_PUBLIC_FUNCTIONS | ALLOWED_PRIVATE_FUNCTIONS


def test_audit_bundles_facade_private_helper_budget_is_exact() -> None:
    tree = _load_audit_bundles_tree()
    private_functions = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("_")
    ]

    assert set(private_functions) == ALLOWED_PRIVATE_FUNCTIONS
    assert len(private_functions) == 13


def test_audit_bundles_facade_has_no_top_level_classes() -> None:
    tree = _load_audit_bundles_tree()

    assert [node.name for node in tree.body if isinstance(node, ast.ClassDef)] == []
