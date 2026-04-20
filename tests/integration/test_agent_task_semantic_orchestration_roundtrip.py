from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import AgentTask, AgentTaskStatus, Document
from app.schemas.agent_tasks import AgentTaskApprovalRequest, AgentTaskCreateRequest
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import approve_agent_task, create_agent_task
from app.services.docling_parser import (
    ParsedChunk,
    ParsedDocument,
    ParsedTable,
    ParsedTableSegment,
)
from app.services.semantic_registry import clear_semantic_registry_cache
from tests.integration.pdf_fixtures import valid_test_pdf_bytes

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


class StubParser:
    def __init__(self, parsed_document: ParsedDocument) -> None:
        self.parsed_document = parsed_document

    def parse_pdf(self, source_path, *, source_filename=None) -> ParsedDocument:
        assert source_path.exists()
        assert source_filename
        return self.parsed_document


def _write_registry(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """registry_name: semantics_layer_foundation
registry_version: semantics-layer-foundation-alpha.2
categories:
  - category_key: integration_governance
    preferred_label: Integration Governance
    scope_note: Controls, thresholds, and governance mechanisms for integration decisions.
concepts:
  - concept_key: integration_threshold
    preferred_label: Integration Threshold
    scope_note: Threshold guidance or threshold matrices used to govern integration decisions.
    category_keys:
      - integration_governance
    aliases:
      - integration threshold
      - threshold guidance
"""
    )


def _write_semantic_eval_corpus(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """corpus_name: semantic_guardrail
eval_version: 2
documents:
  - fixture_name: integration_guardrail_semantics
    source_filename: integration-guardrail-report.pdf
    expected_concepts:
      - concept_key: integration_threshold
        minimum_evidence_count: 2
        required_source_types:
          - chunk
          - table
        expected_category_keys:
          - integration_governance
        suggested_aliases:
          - integration guardrail
        expected_epistemic_status: observed
        expected_review_status: candidate
        expected_category_binding_review_status: candidate
"""
    )


def _build_parsed_document() -> ParsedDocument:
    chunk_text = "Integration guardrail keeps active retrieval grounded."
    table_rows = [
        ["Tier", "Guardrail"],
        ["alpha", "integration guardrail"],
    ]
    segment = ParsedTableSegment(
        segment_index=0,
        segment_order=0,
        source_table_ref="table-0",
        title="Integration Guardrail Matrix",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        metadata={
            "caption": "Integration Guardrail Matrix",
            "title_hint": None,
            "segment_label": "table",
            "title_source": "caption",
            "header_rows_retained": 1,
            "header_rows_removed": 0,
            "source_artifact_sha256": "segment-sha",
        },
    )
    table = ParsedTable(
        table_index=0,
        title="Integration Guardrail Matrix",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        search_text="Integration Guardrail Matrix integration guardrail alpha",
        preview_text="Tier | Guardrail\nalpha | integration guardrail",
        metadata={
            "is_merged": False,
            "source_segment_count": 1,
            "segment_count": 1,
            "merge_reason": "single_segment",
            "merge_confidence": 1.0,
            "continuation_candidate": False,
            "ambiguous_continuation_candidate": False,
            "repeated_header_rows_removed": False,
            "header_rows_removed_count": 0,
            "title_resolution_source": "caption",
            "merge_sanity_passed": True,
            "header_removal_passed": True,
            "source_segment_indices": [0],
            "source_titles": ["Integration Guardrail Matrix"],
        },
        segments=[segment],
    )
    exported_payload = {
        "name": "Guardrail Report",
        "texts": [{"self_ref": "chunk-0", "text": chunk_text}],
        "tables": [{"self_ref": "table-0", "data": {"grid": []}}],
        "pictures": [],
    }
    return ParsedDocument(
        title="Guardrail Report",
        page_count=1,
        yaml_text="document: guardrail-report\n",
        docling_json=json.dumps(exported_payload, indent=2),
        chunks=[
            ParsedChunk(
                chunk_index=0,
                text=chunk_text,
                heading="Section 1",
                page_from=1,
                page_to=1,
                metadata={"label": "text"},
            )
        ],
        tables=[table],
        raw_table_segments=[segment],
        figures=[],
    )


def _process_next_task(postgres_integration_harness) -> UUID:
    with postgres_integration_harness.session_factory() as session:
        task = claim_next_agent_task(session, "integration-agent-worker")
        assert task is not None
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)
        return task.id


def test_semantic_orchestration_roundtrip(postgres_integration_harness, monkeypatch, tmp_path) -> None:
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    eval_corpus_path = tmp_path / "docs" / "semantic_evaluation_corpus.yaml"
    _write_registry(registry_path)
    _write_semantic_eval_corpus(eval_corpus_path)
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_EVALUATION_CORPUS_PATH", str(eval_corpus_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    client = postgres_integration_harness.client
    upload_files = {
        "file": (
            "integration-guardrail-report.pdf",
            valid_test_pdf_bytes(),
            "application/pdf",
        )
    }

    create_response = client.post("/documents", files=upload_files)
    assert create_response.status_code == 202
    document_id = UUID(create_response.json()["document_id"])
    original_run_id = UUID(create_response.json()["run_id"])

    processed_run_id = postgres_integration_harness.process_next_run(StubParser(_build_parsed_document()))
    assert processed_run_id == original_run_id

    semantics_response = client.get(f"/documents/{document_id}/semantics/latest")
    assert semantics_response.status_code == 200
    semantics = semantics_response.json()
    assert semantics["evaluation_summary"]["all_expectations_passed"] is False
    assert semantics["assertion_count"] == 0

    workflow_version = "semantic_milestone_integration"
    with postgres_integration_harness.session_factory() as session:
        latest_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="get_latest_semantic_pass",
                input={"document_id": str(document_id)},
                workflow_version=workflow_version,
            ),
        )
        latest_task_id = latest_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        triage_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="triage_semantic_pass",
                input={"target_task_id": str(latest_task_id), "low_evidence_threshold": 2},
                workflow_version=workflow_version,
            ),
        )
        triage_task_id = triage_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_semantic_registry_update",
                input={
                    "source_task_id": str(triage_task_id),
                    "rationale": "add the missing integration guardrail alias",
                },
                workflow_version=workflow_version,
            ),
        )
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_draft_semantic_registry_update",
                input={
                    "target_task_id": str(draft_task_id),
                    "max_regressed_document_count": 0,
                    "max_failed_expectation_increase": 0,
                    "min_improved_document_count": 1,
                },
                workflow_version=workflow_version,
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_semantic_registry_update",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "publish the verified semantic registry update",
                },
                workflow_version=workflow_version,
            ),
        )
        apply_task_id = apply_task.task_id

    with postgres_integration_harness.session_factory() as session:
        apply_task_row = session.get(AgentTask, apply_task_id)
        assert apply_task_row is not None
        assert apply_task_row.status == AgentTaskStatus.AWAITING_APPROVAL.value
        approve_agent_task(
            session,
            apply_task_id,
            AgentTaskApprovalRequest(
                approved_by="semantic-operator@example.com",
                approval_note="publish the verified registry update",
            ),
        )

    _process_next_task(postgres_integration_harness)

    applied_registry_payload = registry_path.read_text()
    assert "integration guardrail" in applied_registry_payload
    assert "semantics-layer-foundation-alpha.3" in applied_registry_payload

    with postgres_integration_harness.session_factory() as session:
        reprocess_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="enqueue_document_reprocess",
                input={
                    "document_id": str(document_id),
                    "source_task_id": str(apply_task_id),
                    "reason": "refresh the document under the new semantic registry",
                },
                workflow_version=workflow_version,
            ),
        )
        reprocess_task_id = reprocess_task.task_id
        approve_agent_task(
            session,
            reprocess_task_id,
            AgentTaskApprovalRequest(
                approved_by="semantic-operator@example.com",
                approval_note="refresh semantics under the new registry",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        reprocess_task_row = session.get(AgentTask, reprocess_task_id)
        assert reprocess_task_row is not None
        latest_run_id = UUID(reprocess_task_row.result_json["payload"]["reprocess"]["run_id"])
        document = session.get(Document, document_id)
        assert document is not None
        assert document.latest_run_id == latest_run_id

    rerun_id = postgres_integration_harness.process_next_run(StubParser(_build_parsed_document()))
    assert rerun_id == latest_run_id

    final_semantics_response = client.get(f"/documents/{document_id}/semantics/latest")
    assert final_semantics_response.status_code == 200
    final_semantics = final_semantics_response.json()
    assert final_semantics["run_id"] == str(latest_run_id)
    assert final_semantics["registry_version"] == "semantics-layer-foundation-alpha.3"
    assert final_semantics["evaluation_summary"]["all_expectations_passed"] is True
    assert final_semantics["assertion_count"] == 1
    assert final_semantics["assertions"][0]["concept_key"] == "integration_threshold"
    assert sorted(final_semantics["assertions"][0]["source_types"]) == ["chunk", "table"]

    triage_context_response = client.get(f"/agent-tasks/{triage_task_id}/context")
    assert triage_context_response.status_code == 200
    assert triage_context_response.json()["summary"]["next_action"] == "draft_registry_update"
    assert triage_context_response.json()["freshness_status"] == "fresh"

    verify_context_response = client.get(f"/agent-tasks/{verify_task_id}/context")
    assert verify_context_response.status_code == 200
    assert verify_context_response.json()["summary"]["verification_state"] == "passed"

    apply_context_response = client.get(f"/agent-tasks/{apply_task_id}/context")
    assert apply_context_response.status_code == 200
    assert apply_context_response.json()["summary"]["approval_state"] == "approved"
    assert apply_context_response.json()["summary"]["verification_state"] == "passed"

    recommendation_summary_response = client.get(
        "/agent-tasks/analytics/recommendations",
        params={"workflow_version": workflow_version},
    )
    assert recommendation_summary_response.status_code == 200
    recommendation_summary = recommendation_summary_response.json()
    assert recommendation_summary["recommendation_task_count"] >= 1
    assert recommendation_summary["draft_count"] >= 1
    assert recommendation_summary["passed_verification_count"] >= 1
    assert recommendation_summary["applied_count"] >= 1
