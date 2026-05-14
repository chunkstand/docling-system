from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db.models import AgentTask, KnowledgeOperatorRun
from tests.integration.technical_report_harness_support import run_verified_report_roundtrip

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_technical_report_harness_roundtrip(postgres_integration_harness, monkeypatch, tmp_path) -> None:  # noqa: E501
    scenario = run_verified_report_roundtrip(
        postgres_integration_harness,
        monkeypatch,
        tmp_path,
    )
    client = scenario["client"]

    harness_context_response = client.get(f"/agent-tasks/{scenario['harness_task_id']}/context")
    assert harness_context_response.status_code == 200
    harness_context = harness_context_response.json()
    assert harness_context["summary"]["next_action"] == (
        "Create evaluate_document_generation_context_pack before rendering a report draft."
    )
    assert (
        harness_context["output"]["harness"]["workflow_state"]["next_task_type"]
        == "evaluate_document_generation_context_pack"
    )

    context_pack_eval_response = client.get(
        f"/agent-tasks/{scenario['context_pack_eval_task_id']}/context"
    )
    assert context_pack_eval_response.status_code == 200
    context_pack_eval_context = context_pack_eval_response.json()
    assert context_pack_eval_context["summary"]["verification_state"] == "passed"
    assert context_pack_eval_context["summary"]["metrics"]["traceable_claim_ratio"] == 1.0
    assert context_pack_eval_context["output"]["evaluation"]["gate_outcome"] == "passed"
    assert context_pack_eval_context["output"]["context_pack"]["context_pack_sha256"]

    verify_context_response = client.get(f"/agent-tasks/{scenario['verify_task_id']}/context")
    assert verify_context_response.status_code == 200
    assert verify_context_response.json()["summary"]["verification_state"] == "passed"

    audit_response = client.get(f"/agent-tasks/{scenario['verify_task_id']}/audit-bundle")
    assert audit_response.status_code == 200
    audit_bundle = audit_response.json()
    assert audit_bundle["schema_name"] == "technical_report_audit_bundle"
    assert audit_bundle["audit_checklist"]["complete"] is True
    assert audit_bundle["context_pack_audit"]["integrity"]["complete"] is True
    assert audit_bundle["source_evidence_closure"]["complete"] is True

    with postgres_integration_harness.session_factory() as session:
        draft_task_row = session.get(AgentTask, scenario["draft_task_id"])
        assert draft_task_row is not None
        draft_payload = draft_task_row.result_json["payload"]["draft"]
        markdown_path = Path(draft_payload["markdown_path"])
        assert markdown_path.exists()
        assert "Evidence Cards" in markdown_path.read_text()
        assert (
            draft_task_row.result_json["payload"]["context_pack_sha256"]
            == (context_pack_eval_context["output"]["context_pack"]["context_pack_sha256"])
        )

        verify_task_row = session.get(AgentTask, scenario["verify_task_id"])
        assert verify_task_row is not None
        verification = verify_task_row.result_json["payload"]["verification"]
        assert verification["outcome"] == "passed"
        assert verification["metrics"]["source_evidence_closure_complete"] is True
        assert verification["metrics"]["source_record_recall"] == 1.0

        draft_operator_rows = list(
            session.scalars(
                select(KnowledgeOperatorRun)
                .where(KnowledgeOperatorRun.agent_task_id == scenario["draft_task_id"])
                .order_by(KnowledgeOperatorRun.created_at.asc())
            )
        )
        verify_operator_rows = list(
            session.scalars(
                select(KnowledgeOperatorRun).where(
                    KnowledgeOperatorRun.agent_task_id == scenario["verify_task_id"]
                )
            )
        )
        assert [row.operator_kind for row in draft_operator_rows] == ["judge", "generate"]
        assert [row.operator_kind for row in verify_operator_rows] == ["verify"]
