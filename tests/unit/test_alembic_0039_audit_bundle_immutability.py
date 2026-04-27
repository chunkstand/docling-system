from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0039_audit_bundle_immutability.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0039_audit_bundle_immutability", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0039 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0039_installs_and_removes_append_only_trigger(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def execute(sql) -> None:
            calls.append(str(sql))

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "CREATE OR REPLACE FUNCTION prevent_audit_bundle_export_mutation" in joined
    assert "CREATE TRIGGER trg_audit_bundle_exports_prevent_update_delete" in joined
    assert "BEFORE UPDATE OR DELETE ON audit_bundle_exports" in joined
    assert "DROP TRIGGER IF EXISTS trg_audit_bundle_exports_prevent_update_delete" in joined
    assert "DROP FUNCTION IF EXISTS prevent_audit_bundle_export_mutation" in joined
