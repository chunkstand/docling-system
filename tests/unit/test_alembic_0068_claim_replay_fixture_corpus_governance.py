from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0068_claim_replay_fixture_corpus_governance.py"
    )
    spec = importlib.util.spec_from_file_location(
        "revision_0068_claim_replay_fixture_corpus_governance",
        path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0068 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0068_governs_replay_fixture_corpus_snapshots(monkeypatch) -> None:
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
        def add_column(table_name, column, **_kwargs) -> None:
            calls.append(f"ADD_COLUMN:{table_name}:{column.name}")

        @staticmethod
        def drop_column(table_name, column_name, **_kwargs) -> None:
            calls.append(f"DROP_COLUMN:{table_name}:{column_name}")

        @staticmethod
        def create_foreign_key(name, source, referent, local_cols, remote_cols, **_kwargs):
            calls.append(
                "CREATE_FK:"
                f"{name}:{source}:{referent}:{','.join(local_cols)}:{','.join(remote_cols)}"
            )

        @staticmethod
        def create_index(index_name, table_name, columns, **_kwargs) -> None:
            calls.append(f"CREATE_INDEX:{index_name}:{table_name}:{','.join(columns)}")

        @staticmethod
        def drop_index(index_name, *, table_name, **_kwargs) -> None:
            calls.append(f"DROP_INDEX:{index_name}:{table_name}")

        @staticmethod
        def execute(sql) -> None:
            calls.append(str(sql))

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "claim_support_replay_alert_fixture_corpus_snapshot_activated" in joined
    assert "claim_support_replay_alert_fixture_corpus_snapshot" in joined
    assert (
        "ADD_COLUMN:claim_support_replay_alert_fixture_corpus_snapshots:"
        "semantic_governance_event_id"
    ) in joined
    assert (
        "ADD_COLUMN:claim_support_replay_alert_fixture_corpus_snapshots:"
        "governance_artifact_id"
    ) in joined
    assert (
        "ADD_COLUMN:claim_support_replay_alert_fixture_corpus_snapshots:"
        "governance_receipt_sha256"
    ) in joined
    assert "CREATE_FK:fk_cs_replay_fixture_corpus_snapshot_governance_event" in joined
    assert "CREATE_FK:fk_cs_replay_fixture_corpus_snapshot_governance_artifact" in joined
    assert "frozen governance artifacts are immutable" in joined
