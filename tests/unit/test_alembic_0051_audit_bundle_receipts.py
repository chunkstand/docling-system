from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0051_audit_bundle_receipts.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0051_audit_bundle_receipts", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0051 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0051_adds_immutable_audit_bundle_validation_receipts(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def create_table(*args, **kwargs) -> None:
            calls.append(f"CREATE_TABLE:{args[0]}")
            calls.extend(str(arg) for arg in args[1:])

        @staticmethod
        def create_index(*args, **kwargs) -> None:
            calls.append(f"CREATE_INDEX:{args[0]}:{args[1]}:{args[2]}")

        @staticmethod
        def execute(sql) -> None:
            calls.append(str(sql))

        @staticmethod
        def drop_index(*args, **kwargs) -> None:
            calls.append(f"DROP_INDEX:{args[0]}:{kwargs.get('table_name')}")

        @staticmethod
        def drop_table(*args, **kwargs) -> None:
            calls.append(f"DROP_TABLE:{args[0]}")

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    revision_source = Path(revision.__file__).read_text()
    assert "CREATE_TABLE:audit_bundle_validation_receipts" in joined
    assert "fk_audit_bundle_validation_receipts_export" in joined
    assert "retrieval_training_run_provenance" in revision_source
    assert "search_harness_release_provenance" in revision_source
    assert "CREATE_INDEX:ix_audit_bundle_validation_receipts_bundle_created" in joined
    assert "CREATE_INDEX:ix_audit_bundle_validation_receipts_receipt_sha" in joined
    assert "CREATE OR REPLACE FUNCTION prevent_audit_bundle_validation_receipt_mutation" in joined
    assert "trg_audit_bundle_validation_receipts_prevent_update_delete" in joined
    assert "BEFORE UPDATE OR DELETE ON audit_bundle_validation_receipts" in joined
    assert "DROP FUNCTION IF EXISTS prevent_audit_bundle_validation_receipt_mutation" in joined
    assert "DROP_TABLE:audit_bundle_validation_receipts" in joined
