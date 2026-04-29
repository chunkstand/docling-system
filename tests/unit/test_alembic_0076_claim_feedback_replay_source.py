from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0076_claim_feedback_replay_source.py"
    )
    spec = importlib.util.spec_from_file_location(
        "revision_0076_claim_feedback_replay_source",
        path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0076 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0076_allows_claim_feedback_replay_source(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def drop_constraint(*args, **kwargs) -> None:
            calls.append(f"DROP_CONSTRAINT:{args[0]}:{args[1]}:{kwargs.get('type_')}")

        @staticmethod
        def create_check_constraint(*args, **kwargs) -> None:
            calls.append(f"CREATE_CHECK:{args[0]}:{args[1]}:{args[2]}")

        @staticmethod
        def execute(sql) -> None:
            calls.append(str(sql))

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "DROP_CONSTRAINT:ck_search_replay_runs_source_type" in joined
    assert "DROP_CONSTRAINT:ck_search_harness_evaluation_sources_source_type" in joined
    assert "CREATE_CHECK:ck_search_replay_runs_source_type" in joined
    assert "CREATE_CHECK:ck_search_harness_evaluation_sources_source_type" in joined
    assert "technical_report_claim_feedback" in joined
    assert "WHERE source_type = 'technical_report_claim_feedback'" in joined
