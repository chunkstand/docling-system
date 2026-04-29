from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0071_technical_report_readiness_db_gates.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0071_tr_readiness_gate", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0071 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0071_adds_persisted_technical_report_readiness_db_gate(
    monkeypatch,
) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def create_table(*args, **kwargs) -> None:
            calls.append(f"CREATE_TABLE:{args[0]}:{args!r}")
            calls.extend(str(getattr(arg, "sqltext", "")) for arg in args)

        @staticmethod
        def create_index(*args, **kwargs) -> None:
            calls.append(f"CREATE_INDEX:{args[0]}:{args[1]}:{args[2]}")

        @staticmethod
        def create_check_constraint(*args, **kwargs) -> None:
            calls.append(f"CREATE_CHECK:{args[0]}:{args[1]}:{args[2]}")

        @staticmethod
        def drop_constraint(*args, **kwargs) -> None:
            calls.append(f"DROP_CONSTRAINT:{args[0]}:{args[1]}")

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
    assert "CREATE_TABLE:technical_report_release_readiness_db_gates" in joined
    assert "technical_report_readiness_db_gate_recorded" in joined
    assert "release_readiness_assessment_db_integrity" in joined
    assert "source_search_request_count >= 0" in joined
    assert "technical_report_verification_task_id" in joined
    assert "CREATE_INDEX:ix_tr_readiness_db_gates_verification_task" in joined
    assert "CREATE_INDEX:ix_tr_readiness_db_gates_source_verification" in joined
    assert "CREATE_INDEX:ix_tr_readiness_db_gates_prov_artifact" in joined
    assert "CREATE_INDEX:ix_tr_readiness_db_gates_governance" in joined
    assert "CREATE_INDEX:ix_tr_readiness_db_gates_payload_sha" in joined
    assert "DROP_TABLE:technical_report_release_readiness_db_gates" in joined
    assert "DELETE FROM semantic_governance_events" in joined
