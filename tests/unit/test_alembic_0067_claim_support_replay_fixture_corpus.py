from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0067_claim_support_replay_fixture_corpus.py"
    )
    spec = importlib.util.spec_from_file_location(
        "revision_0067_claim_support_replay_fixture_corpus",
        path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0067 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0067_adds_replay_fixture_corpus_tables(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def create_table(table_name, *elements, **_kwargs) -> None:
            calls.append(f"CREATE_TABLE:{table_name}")
            calls.extend(str(element) for element in elements)

        @staticmethod
        def create_index(index_name, table_name, columns, **_kwargs) -> None:
            calls.append(f"CREATE_INDEX:{index_name}:{table_name}:{','.join(columns)}")

        @staticmethod
        def drop_index(index_name, *, table_name, **_kwargs) -> None:
            calls.append(f"DROP_INDEX:{index_name}:{table_name}")

        @staticmethod
        def drop_table(table_name) -> None:
            calls.append(f"DROP_TABLE:{table_name}")

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "CREATE_TABLE:claim_support_replay_alert_fixture_corpus_snapshots" in joined
    assert "CREATE_TABLE:claim_support_replay_alert_fixture_corpus_rows" in joined
    assert "source_promotion_event_ids" in joined
    assert "source_fixture_set_ids" in joined
    assert "case_identity_sha256" in joined
    assert "replay_alert_source" in joined
    assert "CREATE_INDEX:ix_cs_replay_fixture_corpus_snapshots_status_created" in joined
    assert "CREATE_INDEX:ix_cs_replay_fixture_corpus_rows_snapshot" in joined
    assert "DROP_TABLE:claim_support_replay_alert_fixture_corpus_rows" in joined
    assert "DROP_TABLE:claim_support_replay_alert_fixture_corpus_snapshots" in joined
