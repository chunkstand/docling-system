from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0060_claim_support_policy_change_impacts.py"
    )
    spec = importlib.util.spec_from_file_location(
        "revision_0060_claim_support_policy_change_impacts",
        path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0060 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0060_adds_policy_change_impact_table(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def create_table(name, *columns, **kwargs) -> None:
            calls.append(f"CREATE_TABLE:{name}")
            for column in columns:
                calls.append(str(column))
            calls.extend(str(value) for value in kwargs.values())

        @staticmethod
        def create_index(name, table_name, columns, **kwargs) -> None:
            calls.append(f"CREATE_INDEX:{name}:{table_name}:{','.join(columns)}")

        @staticmethod
        def drop_index(name, **kwargs) -> None:
            calls.append(f"DROP_INDEX:{name}:{kwargs.get('table_name')}")

        @staticmethod
        def drop_table(name) -> None:
            calls.append(f"DROP_TABLE:{name}")

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "CREATE_TABLE:claim_support_policy_change_impacts" in joined
    assert "activation_task_id" in joined
    assert "activated_policy_id" in joined
    assert "semantic_governance_event_id" in joined
    assert "governance_artifact_id" in joined
    assert "impact_payload_sha256" in joined
    assert "impacted_claim_derivation_ids" in joined
    assert "ix_claim_support_policy_change_impacts_activation_task" in joined
    assert "ix_claim_support_policy_change_impacts_scope_created" in joined
    assert "DROP_TABLE:claim_support_policy_change_impacts" in joined
