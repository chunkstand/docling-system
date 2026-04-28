from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0049_retrieval_training_audit_bundles.py"
    )
    spec = importlib.util.spec_from_file_location(
        "revision_0049_retrieval_training_audit_bundles",
        path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0049 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0049_extends_audit_bundle_exports(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def drop_constraint(*args, **kwargs) -> None:
            calls.append(f"DROP_CONSTRAINT:{args[0]}:{args[1]}")

        @staticmethod
        def create_check_constraint(*args, **kwargs) -> None:
            calls.append(f"CREATE_CHECK:{args[0]}:{args[1]}:{args[2]}")

        @staticmethod
        def add_column(*args, **kwargs) -> None:
            calls.append(f"ADD_COLUMN:{args[0]}:{args[1].name}")

        @staticmethod
        def create_foreign_key(*args, **kwargs) -> None:
            calls.append(f"CREATE_FK:{args[0]}:{args[1]}:{args[2]}")

        @staticmethod
        def create_index(*args, **kwargs) -> None:
            calls.append(f"CREATE_INDEX:{args[0]}")

        @staticmethod
        def drop_index(*args, **kwargs) -> None:
            calls.append(f"DROP_INDEX:{args[0]}")

        @staticmethod
        def drop_column(*args, **kwargs) -> None:
            calls.append(f"DROP_COLUMN:{args[0]}:{args[1]}")

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "retrieval_training_run_provenance" in joined
    assert "retrieval_training_runs" in joined
    assert "ADD_COLUMN:audit_bundle_exports:retrieval_training_run_id" in joined
    assert (
        "CREATE_FK:fk_audit_bundle_exports_retrieval_training_run:"
        "audit_bundle_exports:retrieval_training_runs"
    ) in joined
    assert "CREATE_INDEX:ix_audit_bundle_exports_training_run_created_at" in joined
    assert "DROP_COLUMN:audit_bundle_exports:retrieval_training_run_id" in joined
