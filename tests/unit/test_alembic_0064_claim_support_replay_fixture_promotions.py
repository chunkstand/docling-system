from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0064_claim_support_replay_fixture_promotions.py"
    )
    spec = importlib.util.spec_from_file_location(
        "revision_0064_claim_support_replay_fixture_promotions",
        path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0064 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0064_adds_replay_fixture_promotion_governance_event(
    monkeypatch,
) -> None:
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
    assert "DROP_CONSTRAINT:ck_semantic_governance_events_event_kind" in joined
    assert "CREATE_CHECK:ck_semantic_governance_events_event_kind" in joined
    assert "claim_support_policy_impact_fixture_promoted" in joined
    assert "claim_support_policy_impact_fixture_promotion" in joined
    assert "frozen governance artifacts are immutable" in joined
