from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0040_span_multivectors.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0040_span_multivectors", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0040 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0040_creates_indexed_span_multivector_table(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[tuple[str, object]] = []

    class FakeOp:
        @staticmethod
        def create_table(table_name, *columns_and_constraints) -> None:
            calls.append(("create_table", table_name, columns_and_constraints))

        @staticmethod
        def create_index(index_name, table_name, columns, **kwargs) -> None:
            calls.append(("create_index", index_name, table_name, tuple(columns), kwargs))

        @staticmethod
        def drop_index(index_name, *, table_name) -> None:
            calls.append(("drop_index", index_name, table_name))

        @staticmethod
        def drop_table(table_name) -> None:
            calls.append(("drop_table", table_name))

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    assert any(
        call[0] == "create_table" and call[1] == "retrieval_evidence_span_multivectors"
        for call in calls
    )
    assert (
        "create_index",
        "ix_retrieval_span_multivectors_embedding_hnsw",
        "retrieval_evidence_span_multivectors",
        ("embedding",),
        {
            "postgresql_using": "hnsw",
            "postgresql_with": {"m": 16, "ef_construction": 64},
            "postgresql_ops": {"embedding": "vector_cosine_ops"},
        },
    ) in calls
    assert (
        "drop_table",
        "retrieval_evidence_span_multivectors",
    ) in calls
