from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0073_claim_retrieval_feedback_ledger.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0073_claim_feedback_ledger", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0073 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0073_adds_claim_retrieval_feedback_ledger(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def create_table(*args, **kwargs) -> None:
            calls.append(f"CREATE_TABLE:{args[0]}:{args!r}")
            calls.extend(str(getattr(arg, "sqltext", "")) for arg in args)

        @staticmethod
        def create_index(*args, **kwargs) -> None:
            calls.append(f"CREATE_INDEX:{args[0]}:{args[1]}:{args[2]}")

        @staticmethod
        def create_check_constraint(*args, **kwargs) -> None:
            calls.append(f"CREATE_CHECK:{args[0]}:{args[1]}:{args[2]}")

        @staticmethod
        def drop_constraint(*args, **kwargs) -> None:
            calls.append(f"DROP_CONSTRAINT:{args[0]}:{args[1]}")

        @staticmethod
        def execute(sql) -> None:
            calls.append(str(sql))

        @staticmethod
        def drop_index(*args, **kwargs) -> None:
            calls.append(f"DROP_INDEX:{args[0]}:{kwargs.get('table_name')}")

        @staticmethod
        def drop_table(*args, **kwargs) -> None:
            calls.append(f"DROP_TABLE:{args[0]}")

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "technical_report_claim_retrieval_feedback_recorded" in joined
    assert "technical_report_claim_feedback" in joined
    assert "CREATE_TABLE:technical_report_claim_retrieval_feedback" in joined
    assert "claim_evidence_derivation_id" in joined
    assert "feedback_payload_sha256" in joined
    assert "source_payload_sha256" in joined
    assert "CREATE_INDEX:ix_tr_claim_feedback_verification_task" in joined
    assert "CREATE_INDEX:ix_tr_claim_feedback_release_gate" in joined
    assert "CREATE_INDEX:ix_tr_claim_feedback_governance" in joined
    assert "prevent_tr_claim_feedback_core_mutation" in joined
    assert "DROP_TABLE:technical_report_claim_retrieval_feedback" in joined
    assert "DELETE FROM semantic_governance_events" in joined
