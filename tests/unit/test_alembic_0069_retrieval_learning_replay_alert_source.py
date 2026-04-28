from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0069_retrieval_learning_replay_alert_source.py"
    )
    spec = importlib.util.spec_from_file_location(
        "revision_0069_retrieval_learning_replay_alert_source",
        path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0069 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0069_adds_replay_alert_corpus_learning_source(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def drop_constraint(*args, **kwargs) -> None:
            calls.append(f"DROP_CONSTRAINT:{args[0]}:{args[1]}:{kwargs.get('type_')}")

        @staticmethod
        def create_check_constraint(*args, **kwargs) -> None:
            calls.append(f"CREATE_CHECK:{args[0]}:{args[1]}:{args[2]}")

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "DROP_CONSTRAINT:ck_retrieval_judgment_sets_set_kind" in joined
    assert "DROP_CONSTRAINT:ck_retrieval_judgments_source_type" in joined
    assert "DROP_CONSTRAINT:ck_retrieval_hard_negatives_source_type" in joined
    assert "CREATE_CHECK:ck_retrieval_judgment_sets_set_kind" in joined
    assert "CREATE_CHECK:ck_retrieval_judgments_source_type" in joined
    assert "CREATE_CHECK:ck_retrieval_hard_negatives_source_type" in joined
    assert "claim_support_replay_alert_corpus" in joined
    assert "source_type IN ('feedback', 'replay')" in joined
