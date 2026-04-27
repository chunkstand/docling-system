from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0047_retrieval_learning_traceability.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0047_retrieval_learning", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0047 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0047_adds_traceability_columns(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def add_column(*args, **kwargs) -> None:
            calls.append(f"ADD_COLUMN:{args[0]}:{args[1].name}")

        @staticmethod
        def create_index(*args, **kwargs) -> None:
            calls.append(f"CREATE_INDEX:{args[0]}")

        @staticmethod
        def create_foreign_key(*args, **kwargs) -> None:
            calls.append(f"CREATE_FK:{args[0]}:{args[1]}:{args[2]}")

        @staticmethod
        def drop_index(*args, **kwargs) -> None:
            calls.append(f"DROP_INDEX:{args[0]}")

        @staticmethod
        def drop_constraint(*args, **kwargs) -> None:
            calls.append(f"DROP_CONSTRAINT:{args[0]}")

        @staticmethod
        def drop_column(*args, **kwargs) -> None:
            calls.append(f"DROP_COLUMN:{args[0]}:{args[1]}")

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "ADD_COLUMN:retrieval_judgments:source_payload_sha256" in joined
    assert "ADD_COLUMN:retrieval_hard_negatives:evidence_refs" in joined
    assert "ADD_COLUMN:retrieval_hard_negatives:source_payload_sha256" in joined
    assert "ADD_COLUMN:retrieval_hard_negatives:source_search_request_id" in joined
    assert "CREATE_FK:fk_retrieval_hard_negatives_source_search_request" in joined
    assert "CREATE_INDEX:ix_retrieval_hard_negatives_source_payload_sha" in joined
    assert "DROP_COLUMN:retrieval_hard_negatives:evidence_refs" in joined
