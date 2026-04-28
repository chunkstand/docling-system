from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0053_reranker_artifacts.py"
    )
    spec = importlib.util.spec_from_file_location("revision_0053_reranker_artifacts", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0053 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0053_adds_reranker_artifact_ledger(monkeypatch) -> None:
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
        def create_table(*args, **kwargs) -> None:
            calls.append(f"CREATE_TABLE:{args[0]}")
            calls.extend(str(arg) for arg in args[1:])

        @staticmethod
        def create_index(*args, **kwargs) -> None:
            calls.append(f"CREATE_INDEX:{args[0]}:{args[1]}:{args[2]}")

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
    revision_source = Path(revision.__file__).read_text()
    assert "retrieval_reranker_artifact_materialized" in joined
    assert "CREATE_TABLE:retrieval_reranker_artifacts" in joined
    assert "fk_retrieval_reranker_artifacts_training_run" in joined
    assert "fk_retrieval_reranker_artifacts_candidate_eval" in joined
    assert "uq_retrieval_reranker_artifacts_candidate_eval" in revision_source
    assert "CREATE_INDEX:ix_retrieval_reranker_artifacts_artifact_sha" in joined
    assert "CREATE_INDEX:ix_retrieval_reranker_artifacts_impact_sha" in joined
    assert "DROP_TABLE:retrieval_reranker_artifacts" in joined
