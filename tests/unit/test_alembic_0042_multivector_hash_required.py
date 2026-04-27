from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

from app.services.retrieval_spans import _embedding_sha256


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0042_multivector_hash_required.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0042_multivector_hash_required", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0042 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0042_backfill_hash_matches_runtime_policy() -> None:
    revision = _load_revision_module()

    assert revision._embedding_sha256_from_text("[1,0.5,0]") == _embedding_sha256(
        [1.0, 0.5, 0.0]
    )


def test_revision_0042_backfills_before_setting_not_null(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[tuple[str, object]] = []

    class FakeBind:
        def execute(self, statement, params=None):
            calls.append(("execute", str(statement), params))
            if params is None:
                return [SimpleNamespace(id="vector-id", embedding_text="[1,0]")]
            return []

    class FakeOp:
        bind = FakeBind()

        @classmethod
        def get_bind(cls):
            return cls.bind

        @staticmethod
        def alter_column(table_name, column_name, **kwargs) -> None:
            calls.append(("alter_column", table_name, column_name, kwargs))

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    update_call = next(call for call in calls if call[0] == "execute" and call[2])
    assert update_call[2]["embedding_sha256"] == revision._embedding_sha256_from_text("[1,0]")
    assert any(
        call[0] == "alter_column"
        and call[1] == "retrieval_evidence_span_multivectors"
        and call[2] == "embedding_sha256"
        and call[3]["nullable"] is False
        for call in calls
    )
