from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0045_semantic_governance_events.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0045_semantic_governance", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0045 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0045_installs_append_only_semantic_governance_ledger(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def create_table(*args, **kwargs) -> None:
            calls.append(f"CREATE_TABLE:{args[0]}:{args!r}")
            calls.extend(str(getattr(arg, "sqltext", "")) for arg in args)

        @staticmethod
        def create_index(*args, **kwargs) -> None:
            calls.append(f"CREATE_INDEX:{args[0]}")

        @staticmethod
        def execute(sql) -> None:
            calls.append(str(sql))

        @staticmethod
        def drop_index(*args, **kwargs) -> None:
            calls.append(f"DROP_INDEX:{args[0]}")

        @staticmethod
        def drop_table(*args, **kwargs) -> None:
            calls.append(f"DROP_TABLE:{args[0]}")

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "CREATE_TABLE:semantic_governance_events" in joined
    assert "CREATE_INDEX:ix_semantic_governance_events_scope_created" in joined
    assert "CREATE_INDEX:ix_semantic_governance_events_artifact" in joined
    assert "technical_report_prov_export_frozen" in joined
    assert "CREATE OR REPLACE FUNCTION prevent_semantic_governance_event_mutation" in joined
    assert "trg_semantic_governance_events_prevent_update_delete" in joined
    assert "BEFORE UPDATE OR DELETE ON semantic_governance_events" in joined
    assert "semantic_governance_events rows are immutable" in joined
    assert "DROP TRIGGER IF EXISTS trg_semantic_governance_events_prevent_update_delete" in joined
    assert "DROP_TABLE:semantic_governance_events" in joined
