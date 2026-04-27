from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0041_multivector_hashes.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0041_multivector_hashes", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0041 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0041_adds_indexed_embedding_hash_column(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[tuple[str, object]] = []

    class FakeOp:
        @staticmethod
        def add_column(table_name, column) -> None:
            calls.append(("add_column", table_name, column.name))

        @staticmethod
        def create_index(index_name, table_name, columns, **_kwargs) -> None:
            calls.append(("create_index", index_name, table_name, tuple(columns)))

        @staticmethod
        def drop_index(index_name, *, table_name) -> None:
            calls.append(("drop_index", index_name, table_name))

        @staticmethod
        def drop_column(table_name, column_name) -> None:
            calls.append(("drop_column", table_name, column_name))

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    assert (
        "add_column",
        "retrieval_evidence_span_multivectors",
        "embedding_sha256",
    ) in calls
    assert (
        "create_index",
        "ix_retrieval_span_multivectors_embedding_sha256",
        "retrieval_evidence_span_multivectors",
        ("embedding_sha256",),
    ) in calls
    assert (
        "drop_column",
        "retrieval_evidence_span_multivectors",
        "embedding_sha256",
    ) in calls
