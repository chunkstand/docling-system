from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0072_harden_readiness_db_gates.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0072_tr_gate_harden", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0072 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0072_hardens_readiness_db_gate_core_fields(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def create_check_constraint(*args, **kwargs) -> None:
            calls.append(f"CREATE_CHECK:{args[0]}:{args[1]}:{args[2]}")

        @staticmethod
        def drop_constraint(*args, **kwargs) -> None:
            calls.append(f"DROP_CHECK:{args[0]}:{args[1]}:{kwargs.get('type_')}")

        @staticmethod
        def execute(sql) -> None:
            calls.append(str(sql))

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "ck_tr_readiness_db_gates_payload_sha_length" in joined
    assert "char_length(gate_payload_sha256) = 64" in joined
    assert "ck_tr_readiness_db_gates_request_count_consistency" in joined
    assert "jsonb_array_length(source_search_request_ids)" in joined
    assert "ck_tr_readiness_db_gates_complete_consistency" in joined
    assert "missing_expected_request_ids = '[]'::jsonb" in joined
    assert "prevent_tr_readiness_db_gate_core_mutation" in joined
    assert "BEFORE UPDATE OR DELETE ON technical_report_release_readiness_db_gates" in joined
    assert "core evidence fields are immutable" in joined
    assert "DROP TRIGGER IF EXISTS trg_tr_readiness_db_gates_prevent_core_mutation" in joined
