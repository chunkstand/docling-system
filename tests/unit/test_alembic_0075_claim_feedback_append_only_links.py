from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_revision_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0075_claim_feedback_append_only_links.py"
    )
    spec = importlib.util.spec_from_file_location(
        "revision_0075_claim_feedback_append_only_links",
        path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to load 0075 migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_0075_makes_claim_feedback_late_links_append_only(monkeypatch) -> None:
    revision = _load_revision_module()
    calls: list[str] = []

    class FakeOp:
        @staticmethod
        def execute(sql) -> None:
            calls.append(str(sql))

    monkeypatch.setattr(revision, "op", FakeOp)

    revision.upgrade()
    revision.downgrade()

    joined = "\n".join(calls)
    assert "prevent_tr_claim_feedback_core_mutation" in joined
    assert "evidence_manifest_id is append-only" in joined
    assert "prov_export_artifact_id is append-only" in joined
    assert "release_readiness_db_gate_id is append-only" in joined
    assert "semantic_governance_event_id is append-only" in joined
    assert "updated_at may only change with late links" in joined
    assert "updated_at cannot move backwards" in joined
