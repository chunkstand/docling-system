from __future__ import annotations

import os
from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.db.models import AgentTask, AgentTaskArtifact, EvidenceTraceNode
from tests.integration.technical_report_harness_support import (
    create_task_and_process,
    run_verified_report_roundtrip,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def _latest_draft_context_artifact(session, draft_task_id):
    return session.scalar(
        select(AgentTaskArtifact)
        .where(
            AgentTaskArtifact.task_id == draft_task_id,
            AgentTaskArtifact.artifact_kind == "context",
        )
        .order_by(AgentTaskArtifact.created_at.desc())
        .limit(1)
    )


def test_verification_flags_source_evidence_closure_regressions(
    postgres_integration_harness,
    monkeypatch,
    tmp_path,
) -> None:
    scenario = run_verified_report_roundtrip(
        postgres_integration_harness,
        monkeypatch,
        tmp_path,
    )
    audit_bundle = (
        scenario["client"].get(f"/agent-tasks/{scenario['verify_task_id']}/audit-bundle").json()
    )
    search_export_id = UUID(
        next(
            row["evidence_package_export_id"]
            for row in audit_bundle["evidence_package_exports"]
            if row["package_kind"] == "search_request"
        )
    )

    with postgres_integration_harness.session_factory() as session:
        draft_task_row = session.get(AgentTask, scenario["draft_task_id"])
        assert draft_task_row is not None
        original_draft_result = deepcopy(draft_task_row.result_json)
        draft_context_row = _latest_draft_context_artifact(session, scenario["draft_task_id"])
        assert draft_context_row is not None
        original_draft_context = deepcopy(draft_context_row.payload_json)
        uncovered_context = deepcopy(original_draft_context)
        uncovered_draft = uncovered_context["output"]["draft"]
        uncovered_card = next(
            card
            for card in uncovered_draft["evidence_cards"]
            if card["evidence_kind"] == "source_evidence"
            and card["source_evidence_match_status"] == "matched_source_record"
        )
        bogus_source_id = str(uuid4())
        uncovered_card["source_locator"] = bogus_source_id
        if uncovered_card["source_type"] == "chunk":
            uncovered_card["chunk_id"] = bogus_source_id
        elif uncovered_card["source_type"] == "table":
            uncovered_card["table_id"] = bogus_source_id
        uncovered_card["metadata"]["source_locator"] = bogus_source_id
        uncovered_card["metadata"]["source_record_keys"] = [
            f"source:{uncovered_card['source_type']}:{bogus_source_id}"
        ]
        uncovered_result = deepcopy(original_draft_result)
        uncovered_result["payload"]["draft"] = deepcopy(uncovered_draft)
        draft_task_row.result_json = uncovered_result
        draft_context_row.payload_json = uncovered_context
        session.commit()

    uncovered_verify_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=scenario["workflow_version"],
        task_type="verify_technical_report",
        task_input={"target_task_id": str(scenario["draft_task_id"])},
    )
    with postgres_integration_harness.session_factory() as session:
        uncovered_verify_task_row = session.get(AgentTask, uncovered_verify_task_id)
        assert uncovered_verify_task_row is not None
        uncovered_verification = uncovered_verify_task_row.result_json["payload"]["verification"]
        assert uncovered_verification["outcome"] == "failed"
        assert uncovered_verification["metrics"]["source_evidence_closure_complete"] is False
        assert (
            uncovered_verification["metrics"][
                "cited_cards_with_expected_record_without_recomputed_record_match_count"
            ]
            == 1
        )
        assert uncovered_verification["metrics"]["reported_recomputed_match_mismatch_count"] == 1
        assert uncovered_verification["metrics"]["source_record_recall"] < 1.0

        draft_task_row = session.get(AgentTask, scenario["draft_task_id"])
        assert draft_task_row is not None
        draft_task_row.result_json = original_draft_result
        draft_context_row = _latest_draft_context_artifact(session, scenario["draft_task_id"])
        assert draft_context_row is not None
        draft_context_row.payload_json = original_draft_context
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        draft_task_row = session.get(AgentTask, scenario["draft_task_id"])
        assert draft_task_row is not None
        original_draft_result = deepcopy(draft_task_row.result_json)
        draft_context_row = _latest_draft_context_artifact(session, scenario["draft_task_id"])
        assert draft_context_row is not None
        original_draft_context = deepcopy(draft_context_row.payload_json)
        weak_match_context = deepcopy(original_draft_context)
        weak_draft = weak_match_context["output"]["draft"]
        weak_card = next(
            card
            for card in weak_draft["evidence_cards"]
            if card["evidence_kind"] == "source_evidence"
            and card["source_evidence_match_status"]
            in {"matched_source_record", "matched_page_span"}
        )
        weak_card["source_evidence_match_status"] = "matched_document_run_fallback"
        weak_card["source_evidence_match_keys"] = [
            f"document-run-fallback:{weak_card['document_id']}:{weak_card['run_id']}"
        ]
        for claim in weak_draft["claims"]:
            if weak_card["evidence_card_id"] in claim["evidence_card_ids"]:
                claim["source_evidence_match_status"] = "matched_document_run_fallback"
                claim["source_evidence_match_keys"] = list(weak_card["source_evidence_match_keys"])
        weak_match_result = deepcopy(original_draft_result)
        weak_match_result["payload"]["draft"] = deepcopy(weak_draft)
        draft_task_row.result_json = weak_match_result
        draft_context_row.payload_json = weak_match_context
        session.commit()

    weak_match_verify_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=scenario["workflow_version"],
        task_type="verify_technical_report",
        task_input={"target_task_id": str(scenario["draft_task_id"])},
    )
    with postgres_integration_harness.session_factory() as session:
        weak_match_verify_task_row = session.get(AgentTask, weak_match_verify_task_id)
        assert weak_match_verify_task_row is not None
        weak_match_verification = weak_match_verify_task_row.result_json["payload"]["verification"]
        assert weak_match_verification["outcome"] == "failed"
        assert weak_match_verification["metrics"]["source_evidence_closure_complete"] is False
        assert (
            weak_match_verification["metrics"][
                "cited_cards_without_acceptable_source_evidence_match_count"
            ]
            == 1
        )
        assert any(
            "source-record or page-span coverage" in reason
            for reason in weak_match_verification["reasons"]
        )

        draft_task_row = session.get(AgentTask, scenario["draft_task_id"])
        assert draft_task_row is not None
        draft_task_row.result_json = original_draft_result
        draft_context_row = _latest_draft_context_artifact(session, scenario["draft_task_id"])
        assert draft_context_row is not None
        draft_context_row.payload_json = original_draft_context
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        source_trace_node = session.scalar(
            select(EvidenceTraceNode)
            .where(EvidenceTraceNode.evidence_package_export_id == search_export_id)
            .limit(1)
        )
        assert source_trace_node is not None
        tampered_source_payload = deepcopy(source_trace_node.payload_json)
        tampered_source_payload["tampered_for_verification_gate"] = True
        source_trace_node.payload_json = tampered_source_payload
        session.commit()

    tampered_verify_task_id = create_task_and_process(
        postgres_integration_harness,
        workflow_version=scenario["workflow_version"],
        task_type="verify_technical_report",
        task_input={"target_task_id": str(scenario["draft_task_id"])},
    )
    with postgres_integration_harness.session_factory() as session:
        tampered_verify_task_row = session.get(AgentTask, tampered_verify_task_id)
        assert tampered_verify_task_row is not None
        tampered_verification = tampered_verify_task_row.result_json["payload"]["verification"]
        assert tampered_verification["outcome"] == "failed"
        assert tampered_verification["metrics"]["source_evidence_closure_complete"] is False
        assert (
            tampered_verification["metrics"]["source_evidence_package_trace_incomplete_count"] == 1
        )
        assert any(
            "frozen search evidence packages" in reason
            for reason in tampered_verification["reasons"]
        )
