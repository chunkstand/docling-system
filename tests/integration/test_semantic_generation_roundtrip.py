from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

import pytest

from app.core.config import get_settings
from app.db.models import AgentTask
from app.schemas.agent_tasks import AgentTaskCreateRequest
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import create_agent_task
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
registry_version: semantics-layer-foundation-alpha.3
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
      - integration guardrail
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


def test_semantic_generation_roundtrip(
    postgres_integration_harness,
    monkeypatch,
    tmp_path,
) -> None:
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    eval_corpus_path = tmp_path / "docs" / "semantic_evaluation_corpus.yaml"
    _write_registry(registry_path)
    _write_semantic_eval_corpus(eval_corpus_path)
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_EVALUATION_CORPUS_PATH", str(eval_corpus_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    client = postgres_integration_harness.client
    create_response = client.post(
        "/documents",
        files={
            "file": (
                "integration-guardrail-report.pdf",
                valid_test_pdf_bytes(),
                "application/pdf",
            )
        },
    )
    assert create_response.status_code == 202
    document_id = UUID(create_response.json()["document_id"])
    run_id = UUID(create_response.json()["run_id"])

    processed_run_id = postgres_integration_harness.process_next_run(
        StubParser(_build_parsed_document())
    )
    assert processed_run_id == run_id

    semantics_response = client.get(f"/documents/{document_id}/semantics/latest")
    assert semantics_response.status_code == 200
    semantics = semantics_response.json()
    assert semantics["assertion_count"] == 1
    assert semantics["evaluation_summary"]["all_expectations_passed"] is True

    workflow_version = "semantic_generation_integration"
    with postgres_integration_harness.session_factory() as session:
        brief_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="prepare_semantic_generation_brief",
                input={
                    "title": "Integration Governance Brief",
                    "goal": "Summarize the knowledge base guidance on integration governance.",
                    "audience": "Operators",
                    "document_ids": [str(document_id)],
                    "target_length": "medium",
                    "review_policy": "allow_candidate_with_disclosure",
                },
                workflow_version=workflow_version,
            ),
        )
        brief_task_id = brief_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_semantic_grounded_document",
                input={"target_task_id": str(brief_task_id)},
                workflow_version=workflow_version,
            ),
        )
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_semantic_grounded_document",
                input={"target_task_id": str(draft_task_id)},
                workflow_version=workflow_version,
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_task_row = session.get(AgentTask, draft_task_id)
        assert draft_task_row is not None
        markdown_path = Path(draft_task_row.result_json["payload"]["draft"]["markdown_path"])
        assert markdown_path.exists()
        assert "Evidence Appendix" in markdown_path.read_text()

        verify_task_row = session.get(AgentTask, verify_task_id)
        assert verify_task_row is not None
        assert verify_task_row.result_json["payload"]["verification"]["outcome"] == "passed"

    brief_context_response = client.get(f"/agent-tasks/{brief_task_id}/context")
    assert brief_context_response.status_code == 200
    assert brief_context_response.json()["summary"]["next_action"] == (
        "Create draft_semantic_grounded_document to render a grounded knowledge brief."
    )

    draft_context_response = client.get(f"/agent-tasks/{draft_task_id}/context")
    assert draft_context_response.status_code == 200
    assert draft_context_response.json()["summary"]["verification_state"] == "pending"

    verify_context_response = client.get(f"/agent-tasks/{verify_task_id}/context")
    assert verify_context_response.status_code == 200
    assert verify_context_response.json()["summary"]["verification_state"] == "passed"

    recommendation_summary_response = client.get(
        "/agent-tasks/analytics/costs",
        params={
            "workflow_version": workflow_version,
            "task_type": "verify_semantic_grounded_document",
        },
    )
    assert recommendation_summary_response.status_code == 200
    assert recommendation_summary_response.json()["attempt_count"] >= 1
