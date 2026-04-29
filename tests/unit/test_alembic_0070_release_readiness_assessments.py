from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0070_release_readiness_assessments.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0070_release_readiness", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0070 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0070_adds_append_only_release_readiness_assessments(
    monkeypatch,
) -> None:
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
    assert "CREATE_TABLE:search_harness_release_readiness_assessments" in joined
    assert "search_harness_release_readiness_assessed" in joined
    assert "readiness_status IN ('ready', 'blocked')" in joined
    assert "CREATE_INDEX:ix_shr_readiness_assessments_release_created" in joined
    assert "CREATE_INDEX:ix_shr_readiness_assessments_receipt_created" in joined
    assert "CREATE_INDEX:ix_shr_readiness_assessments_payload_sha" in joined
    assert (
        "CREATE OR REPLACE FUNCTION "
        "prevent_search_harness_release_readiness_assessment_mutation"
    ) in joined
    assert "trg_shr_readiness_assessments_prevent_update_delete" in joined
    assert (
        "BEFORE UPDATE OR DELETE ON search_harness_release_readiness_assessments"
    ) in joined
    assert "search_harness_release_readiness_assessments rows are immutable" in joined
    assert (
        "DROP FUNCTION IF EXISTS "
        "prevent_search_harness_release_readiness_assessment_mutation"
    ) in joined
    assert "DROP_TABLE:search_harness_release_readiness_assessments" in joined
