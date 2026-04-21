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
registry_version: semantics-layer-foundation-alpha.4
categories:
  - category_key: integration_governance
    preferred_label: Integration Governance
    scope_note: Controls, thresholds, and ownership for integration decisions.
concepts:
  - concept_key: integration_threshold
    preferred_label: Integration Threshold
    scope_note: Threshold guidance or matrices used to govern integrations.
    category_keys:
      - integration_governance
    aliases:
      - integration threshold
  - concept_key: integration_owner
    preferred_label: Integration Owner
    scope_note: The owner who approves or governs integration changes.
    category_keys:
      - integration_governance
"""
    )


def _write_semantic_eval_corpus(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """corpus_name: semantic_shadow_guardrail
eval_version: 2
documents:
  - fixture_name: integration_shadow_semantics
    source_filename: integration-shadow-report.pdf
    expected_concepts:
      - concept_key: integration_threshold
        minimum_evidence_count: 2
        required_source_types:
          - chunk
          - table
        expected_category_keys:
          - integration_governance
        expected_epistemic_status: observed
      - concept_key: integration_owner
        minimum_evidence_count: 1
        required_source_types:
          - chunk
        expected_category_keys:
          - integration_governance
        expected_epistemic_status: observed
"""
    )


def _build_parsed_document() -> ParsedDocument:
    chunk_text = (
        "Integration threshold remains in force. "
        "Owners for integration approve changes before rollout."
    )
    table_rows = [
        ["Tier", "Threshold"],
        ["alpha", "integration threshold"],
    ]
    segment = ParsedTableSegment(
        segment_index=0,
        segment_order=0,
        source_table_ref="table-0",
        title="Integration Threshold Matrix",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        metadata={
            "caption": "Integration Threshold Matrix",
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
        title="Integration Threshold Matrix",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        search_text="Integration Threshold Matrix integration threshold alpha",
        preview_text="Tier | Threshold\nalpha | integration threshold",
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
            "source_titles": ["Integration Threshold Matrix"],
        },
        segments=[segment],
    )
    exported_payload = {
        "name": "Integration Shadow Report",
        "texts": [{"self_ref": "chunk-0", "text": chunk_text}],
        "tables": [{"self_ref": "table-0", "data": {"grid": []}}],
        "pictures": [],
    }
    return ParsedDocument(
        title="Integration Shadow Report",
        page_count=1,
        yaml_text="document: integration-shadow-report\n",
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


def test_semantic_candidate_roundtrip(
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
                "integration-shadow-report.pdf",
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
    assert semantics["evaluation_summary"]["all_expectations_passed"] is False

    threshold_assertion = semantics["assertions"][0]
    review_response = client.post(
        f"/documents/{document_id}/semantics/latest/assertions/{threshold_assertion['assertion_id']}/review",
        json={
            "review_status": "approved",
            "review_note": "Confirmed operator-approved threshold.",
            "reviewed_by": "operator@example.com",
        },
    )
    assert review_response.status_code == 200
    threshold_binding = threshold_assertion["category_bindings"][0]
    binding_review_response = client.post(
        f"/documents/{document_id}/semantics/latest/assertion-category-bindings/{threshold_binding['binding_id']}/review",
        json={
            "review_status": "approved",
            "review_note": "Confirmed threshold governance binding.",
            "reviewed_by": "operator@example.com",
        },
    )
    assert binding_review_response.status_code == 200

    workflow_version = "semantic_candidate_roundtrip"
    with postgres_integration_harness.session_factory() as session:
        brief_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="prepare_semantic_generation_brief",
                input={
                    "title": "Integration Shadow Brief",
                    "goal": "Summarize the live integration guidance and expose shadow candidates.",
                    "audience": "Operators",
                    "document_ids": [str(document_id)],
                    "target_length": "medium",
                    "review_policy": "allow_candidate_with_disclosure",
                    "include_shadow_candidates": True,
                    "candidate_extractor_name": "concept_ranker_v1",
                    "candidate_score_threshold": 0.34,
                    "max_shadow_candidates": 4,
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
        export_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="export_semantic_supervision_corpus",
                input={
                    "document_ids": [str(document_id)],
                    "reviewed_only": True,
                    "include_generation_verifications": True,
                },
                workflow_version=workflow_version,
            ),
        )
        export_task_id = export_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        evaluate_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_semantic_candidate_extractor",
                input={
                    "document_ids": [str(document_id)],
                    "candidate_extractor_name": "concept_ranker_v1",
                    "baseline_extractor_name": "registry_lexical_v1",
                    "max_candidates_per_source": 3,
                    "score_threshold": 0.34,
                },
                workflow_version=workflow_version,
            ),
        )
        evaluate_task_id = evaluate_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        triage_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="triage_semantic_candidate_disagreements",
                input={
                    "target_task_id": str(evaluate_task_id),
                    "min_score": 0.34,
                    "include_expected_only": False,
                },
                workflow_version=workflow_version,
            ),
        )
        triage_task_id = triage_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        brief_task_row = session.get(AgentTask, brief_task_id)
        assert brief_task_row is not None
        brief_payload = brief_task_row.result_json["payload"]["brief"]
        assert brief_payload["shadow_mode"] is True
        assert brief_payload["shadow_candidate_summary"]["candidate_count"] >= 1
        assert [row["concept_key"] for row in brief_payload["shadow_candidates"]] == [
            "integration_owner"
        ]
        assert [row["concept_key"] for row in brief_payload["semantic_dossier"]] == [
            "integration_threshold"
        ]

        verify_task_row = session.get(AgentTask, verify_task_id)
        assert verify_task_row is not None
        assert verify_task_row.result_json["payload"]["verification"]["outcome"] == "passed"

        export_task_row = session.get(AgentTask, export_task_id)
        assert export_task_row is not None
        corpus = export_task_row.result_json["payload"]["corpus"]
        assert corpus["row_type_counts"]["semantic_assertion_review"] == 1
        assert corpus["row_type_counts"]["semantic_category_review"] == 1
        assert corpus["row_type_counts"]["semantic_evaluation_expectation"] == 2
        assert corpus["row_type_counts"]["grounded_document_verification"] == 1
        assert Path(corpus["jsonl_path"]).exists()

        evaluate_task_row = session.get(AgentTask, evaluate_task_id)
        assert evaluate_task_row is not None
        evaluation = evaluate_task_row.result_json["payload"]
        assert (
            evaluation["summary"]["candidate_expected_recall"]
            > evaluation["summary"]["baseline_expected_recall"]
        )
        report = evaluation["document_reports"][0]
        assert report["improved_expected_concept_keys"] == ["integration_owner"]
        assert report["candidate_only_concept_keys"] == ["integration_owner"]

        triage_task_row = session.get(AgentTask, triage_task_id)
        assert triage_task_row is not None
        triage = triage_task_row.result_json["payload"]
        assert triage["disagreement_report"]["issue_count"] >= 1
        assert triage["recommendation"]["next_action"] == "review_shadow_candidates"
        assert triage["verification"]["outcome"] == "passed"

    export_context_response = client.get(f"/agent-tasks/{export_task_id}/context")
    assert export_context_response.status_code == 200
    assert export_context_response.json()["summary"]["next_action"] == (
        "Create evaluate_semantic_candidate_extractor to compare a "
        "shadow extractor against the baseline."
    )

    triage_context_response = client.get(f"/agent-tasks/{triage_task_id}/context")
    assert triage_context_response.status_code == 200
    assert triage_context_response.json()["summary"]["verification_state"] == "passed"
