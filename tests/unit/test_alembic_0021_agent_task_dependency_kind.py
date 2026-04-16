from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0021_agent_task_dependency_kind.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0021_agent_task_dependency_kind", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0021 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0021_upgrade_and_downgrade(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[tuple[str, object]] = []

    class FakeOp:
        @staticmethod
        def add_column(table_name, column) -> None:
            calls.append(("add_column", table_name, column.name, str(column.server_default.arg)))

        @staticmethod
        def create_check_constraint(name, table_name, condition) -> None:
            calls.append(("create_check_constraint", name, table_name, condition))

        @staticmethod
        def drop_constraint(name, table_name, type_=None) -> None:
            calls.append(("drop_constraint", name, table_name, type_))

        @staticmethod
        def drop_column(table_name, column_name) -> None:
            calls.append(("drop_column", table_name, column_name))

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    assert (
        "add_column",
        "agent_task_dependencies",
        "dependency_kind",
        "'explicit'",
    ) in calls
    assert any(
        call[0] == "create_check_constraint"
        and call[1] == "ck_agent_task_dependencies_dependency_kind"
        for call in calls
    )
    assert (
        "drop_constraint",
        "ck_agent_task_dependencies_dependency_kind",
        "agent_task_dependencies",
        "check",
    ) in calls
    assert ("drop_column", "agent_task_dependencies", "dependency_kind") in calls
