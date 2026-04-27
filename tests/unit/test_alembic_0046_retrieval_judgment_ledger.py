from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0046_retrieval_judgment_ledger.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0046_retrieval_judgment", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0046 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0046_adds_retrieval_learning_ledger(monkeypatch) -> None:
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
        def drop_index(*args, **kwargs) -> None:
            calls.append(f"DROP_INDEX:{args[0]}")

        @staticmethod
        def drop_table(*args, **kwargs) -> None:
            calls.append(f"DROP_TABLE:{args[0]}")

        @staticmethod
        def drop_constraint(*args, **kwargs) -> None:
            calls.append(f"DROP_CONSTRAINT:{args[0]}:{args[1]}")

        @staticmethod
        def create_check_constraint(*args, **kwargs) -> None:
            calls.append(f"CREATE_CHECK:{args[0]}:{args[1]}:{args[2]}")

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "DROP_CONSTRAINT:ck_semantic_governance_events_event_kind" in joined
    assert "CREATE_CHECK:ck_semantic_governance_events_event_kind" in joined
    assert "retrieval_training_run_materialized" in joined
    assert "CREATE_TABLE:retrieval_judgment_sets" in joined
    assert "CREATE_TABLE:retrieval_judgments" in joined
    assert "CREATE_TABLE:retrieval_hard_negatives" in joined
    assert "CREATE_TABLE:retrieval_training_runs" in joined
    assert "CREATE_INDEX:ix_retrieval_judgments_source" in joined
    assert "CREATE_INDEX:ix_retrieval_hard_negatives_source" in joined
    assert "CREATE_INDEX:ix_retrieval_training_runs_governance" in joined
    assert "DROP_TABLE:retrieval_training_runs" in joined
    assert "DROP_TABLE:retrieval_judgment_sets" in joined
