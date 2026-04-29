from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0074_claim_feedback_set_kind.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0074_claim_feedback_set_kind", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0074 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0074_allows_claim_feedback_set_kind(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
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
    assert "DROP_CONSTRAINT:ck_retrieval_judgment_sets_set_kind" in joined
    assert "CREATE_CHECK:ck_retrieval_judgment_sets_set_kind" in joined
    assert "technical_report_claim_feedback" in joined
    assert "claim_support_replay_alert_corpus" in joined
