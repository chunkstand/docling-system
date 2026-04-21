from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

import pytest

from app.core.config import get_settings
from app.db.models import AgentTask, AgentTaskStatus, Document, SemanticOntologySnapshot
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
categories: []
concepts:
  - concept_key: integration_threshold
    preferred_label: Integration Threshold
    aliases:
      - integration threshold
"""
    )


def _write_empty_semantic_eval_corpus(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """corpus_name: semantic_bootstrap
eval_version: 2
documents: []
"""
    )


def _build_parsed_document() -> ParsedDocument:
    chunk_text = (
        "Incident response latency target remains under fifteen minutes. "
        "The incident response latency dashboard is reviewed every week."
    )
    table_rows = [
        ["Metric", "Target"],
        ["incident response latency", "15 minutes"],
    ]
    segment = ParsedTableSegment(
        segment_index=0,
        segment_order=0,
        source_table_ref="table-0",
        title="Incident Response Latency Targets",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        metadata={
            "caption": "Incident Response Latency Targets",
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
        title="Incident Response Latency Targets",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        search_text="incident response latency targets incident response latency 15 minutes",
        preview_text="Metric | Target\nincident response latency | 15 minutes",
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
            "source_titles": ["Incident Response Latency Targets"],
        },
        segments=[segment],
    )
    exported_payload = {
        "name": "Incident Review",
        "texts": [{"self_ref": "chunk-0", "text": chunk_text}],
        "tables": [{"self_ref": "table-0", "data": {"grid": []}}],
        "pictures": [],
    }
    return ParsedDocument(
        title="Incident Review",
        page_count=1,
        yaml_text="document: incident-review\n",
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


def test_semantic_bootstrap_roundtrip(postgres_integration_harness, monkeypatch, tmp_path) -> None:
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    eval_corpus_path = tmp_path / "docs" / "semantic_evaluation_corpus.yaml"
    _write_registry(registry_path)
    _write_empty_semantic_eval_corpus(eval_corpus_path)
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_EVALUATION_CORPUS_PATH", str(eval_corpus_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    client = postgres_integration_harness.client
    create_response = client.post(
        "/documents",
        files={
            "file": (
                "incident-review.pdf",
                valid_test_pdf_bytes(),
                "application/pdf",
            )
        },
    )
    assert create_response.status_code == 202
    document_id = UUID(create_response.json()["document_id"])
    original_run_id = UUID(create_response.json()["run_id"])

    processed_run_id = postgres_integration_harness.process_next_run(
        StubParser(_build_parsed_document())
    )
    assert processed_run_id == original_run_id

    semantics_response = client.get(f"/documents/{document_id}/semantics/latest")
    assert semantics_response.status_code == 200
    semantics = semantics_response.json()
    assert semantics["assertion_count"] == 0

    workflow_version = "semantic_bootstrap_integration"
    with postgres_integration_harness.session_factory() as session:
        discover_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="discover_semantic_bootstrap_candidates",
                input={
                    "document_ids": [str(document_id)],
                    "max_candidates": 6,
                    "min_document_count": 1,
                    "min_source_count": 2,
                    "min_phrase_tokens": 2,
                    "max_phrase_tokens": 4,
                    "exclude_existing_registry_terms": True,
                },
                workflow_version=workflow_version,
            ),
        )
        discover_task_id = discover_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        discover_task_row = session.get(AgentTask, discover_task_id)
        assert discover_task_row is not None
        report = discover_task_row.result_json["payload"]["report"]
        candidate = next(
            row for row in report["candidates"] if row["concept_key"] == "incident_response_latency"
        )
        candidate_id = candidate["candidate_id"]

        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_semantic_registry_update",
                input={
                    "source_task_id": str(discover_task_id),
                    "candidate_ids": [candidate_id],
                    "rationale": "bootstrap a registry concept from corpus evidence",
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
        verify_task_row = session.get(AgentTask, verify_task_id)
        assert verify_task_row is not None
        assert verify_task_row.result_json["payload"]["verification"]["outcome"] == "passed"

        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_semantic_registry_update",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "publish the verified bootstrap concept",
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
                approval_note="publish the bootstrap registry concept",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_task_row = session.get(AgentTask, apply_task_id)
        assert apply_task_row is not None
        apply_payload = apply_task_row.result_json["payload"]
        assert apply_payload["config_path"].startswith("db://semantic_ontology_snapshots/")
        snapshot_rows = (
            session.query(SemanticOntologySnapshot)
            .order_by(SemanticOntologySnapshot.created_at.desc())
            .all()
        )
        assert snapshot_rows
        assert snapshot_rows[0].ontology_version == "semantics-layer-foundation-alpha.3"
        assert "incident_response_latency" in json.dumps(snapshot_rows[0].payload_json)

    with postgres_integration_harness.session_factory() as session:
        reprocess_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="enqueue_document_reprocess",
                input={
                    "document_id": str(document_id),
                    "source_task_id": str(apply_task_id),
                    "reason": "refresh the document under the bootstrap registry",
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
                approval_note="refresh semantics under the bootstrap registry",
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
    assert final_semantics["assertion_count"] >= 1
    assert any(
        assertion["concept_key"] == "incident_response_latency"
        for assertion in final_semantics["assertions"]
    )
