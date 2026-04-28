from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0061_claim_support_impact_replay_lifecycle.py"
    )
    spec = importlib.util.spec_from_file_location(
        "revision_0061_claim_support_impact_replay",
        path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0061 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0061_adds_policy_change_impact_replay_lifecycle(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def add_column(table_name, column) -> None:
            calls.append(f"ADD_COLUMN:{table_name}:{column}")

        @staticmethod
        def create_check_constraint(name, table_name, condition) -> None:
            calls.append(f"CREATE_CHECK:{name}:{table_name}:{condition}")

        @staticmethod
        def create_index(name, table_name, columns, **kwargs) -> None:
            calls.append(f"CREATE_INDEX:{name}:{table_name}:{','.join(columns)}")

        @staticmethod
        def execute(statement) -> None:
            calls.append(f"EXECUTE:{statement}")

        @staticmethod
        def drop_index(name, **kwargs) -> None:
            calls.append(f"DROP_INDEX:{name}:{kwargs.get('table_name')}")

        @staticmethod
        def drop_constraint(name, table_name, **kwargs) -> None:
            calls.append(f"DROP_CONSTRAINT:{name}:{table_name}:{kwargs.get('type_')}")

        @staticmethod
        def drop_column(table_name, column_name) -> None:
            calls.append(f"DROP_COLUMN:{table_name}:{column_name}")

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "replay_status" in joined
    assert "replay_task_ids" in joined
    assert "replay_task_plan" in joined
    assert "replay_closure" in joined
    assert "replay_closure_sha256" in joined
    assert "ck_claim_support_policy_change_impacts_replay_status" in joined
    assert "ix_claim_support_policy_change_impacts_replay_status" in joined
    assert "no_action_required" in joined
    assert "DROP_COLUMN:claim_support_policy_change_impacts:replay_status" in joined
