from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0050_audit_bundle_source_consistency.py"
    )
    spec = importlib.util.spec_from_file_location(
        "revision_0050_audit_bundle_source_consistency",
        path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0050 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0050_enforces_audit_bundle_source_consistency(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def create_check_constraint(*args, **kwargs) -> None:
            calls.append(f"CREATE_CHECK:{args[0]}:{args[1]}:{args[2]}")

        @staticmethod
        def drop_constraint(*args, **kwargs) -> None:
            calls.append(f"DROP_CONSTRAINT:{args[0]}:{args[1]}")

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "CREATE_CHECK:ck_audit_bundle_exports_source_consistency:audit_bundle_exports" in joined
    assert "search_harness_release_id = source_id" in joined
    assert "retrieval_training_run_id = source_id" in joined
    assert "DROP_CONSTRAINT:ck_audit_bundle_exports_source_consistency" in joined
