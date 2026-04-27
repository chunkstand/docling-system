from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0044_prov_artifact_immutability.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0044_prov_artifact_immutability", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0044 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0044_installs_frozen_prov_artifact_immutability(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def create_table(*args, **kwargs) -> None:
            calls.append(f"CREATE_TABLE:{args[0]}")

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
    assert "CREATE_TABLE:agent_task_artifact_immutability_events" in joined
    assert "CREATE OR REPLACE FUNCTION prevent_frozen_agent_task_artifact_mutation" in joined
    assert "trg_agent_task_artifacts_prevent_frozen_prov_mutation" in joined
    assert "BEFORE UPDATE OR DELETE ON agent_task_artifacts" in joined
    assert "technical_report_prov_export artifacts are immutable" in joined
    assert (
        "CREATE OR REPLACE FUNCTION prevent_agent_task_artifact_immutability_event_mutation"
        in joined
    )
    assert "DROP TRIGGER IF EXISTS trg_agent_task_artifacts_prevent_frozen_prov_mutation" in joined
    assert "DROP_TABLE:agent_task_artifact_immutability_events" in joined
