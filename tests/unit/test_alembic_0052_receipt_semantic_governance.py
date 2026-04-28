from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0052_receipt_semantic_governance.py"
    )
    spec = importlib.util.spec_from_file_location(
        "revision_0052_receipt_semantic_governance",
        path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0052 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0052_adds_receipt_semantic_governance_check(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def add_column(*args, **kwargs) -> None:
            calls.append(f"ADD_COLUMN:{args[0]}:{args[1].name}:{args[1].nullable}")

        @staticmethod
        def alter_column(*args, **kwargs) -> None:
            calls.append(f"ALTER_COLUMN:{args[0]}:{args[1]}:{kwargs}")

        @staticmethod
        def drop_column(*args, **kwargs) -> None:
            calls.append(f"DROP_COLUMN:{args[0]}:{args[1]}")

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "ADD_COLUMN:audit_bundle_validation_receipts:semantic_governance_valid:False" in joined
    assert "ALTER_COLUMN:audit_bundle_validation_receipts:semantic_governance_valid" in joined
    assert "server_default': None" in joined
    assert "DROP_COLUMN:audit_bundle_validation_receipts:semantic_governance_valid" in joined
