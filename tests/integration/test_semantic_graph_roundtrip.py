from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

import pytest

from app.core.config import get_settings
from app.db.models import AgentTask, AgentTaskStatus
from app.schemas.agent_tasks import AgentTaskApprovalRequest, AgentTaskCreateRequest
from app.services.agent_task_worker import claim_next_agent_task, process_agent_task
from app.services.agent_tasks import approve_agent_task, create_agent_task
from app.services.docling_parser import (
    ParsedChunk,
    ParsedDocument,
    ParsedTable,
    ParsedTableSegment,
)
from app.services.semantic_graph import get_active_semantic_graph_snapshot
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
registry_version: semantics-layer-foundation-alpha.5
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
    aliases:
      - integration owner
relations:
  - relation_key: document_mentions_concept
    preferred_label: Document Mentions Concept
    domain_entity_types:
      - document
    range_entity_types:
      - concept
    symmetric: false
    allow_literal_object: false
  - relation_key: concept_related_to_concept
    preferred_label: Concept Related To Concept
    domain_entity_types:
      - concept
    range_entity_types:
      - concept
    symmetric: true
    allow_literal_object: false
    inverse_relation_key: concept_related_to_concept
  - relation_key: concept_depends_on_concept
    preferred_label: Concept Depends On Concept
    domain_entity_types:
      - concept
    range_entity_types:
      - concept
    symmetric: false
    allow_literal_object: false
    inverse_relation_key: concept_enables_concept
  - relation_key: concept_enables_concept
    preferred_label: Concept Enables Concept
    domain_entity_types:
      - concept
    range_entity_types:
      - concept
    symmetric: false
    allow_literal_object: false
    inverse_relation_key: concept_depends_on_concept
"""
    )


def _write_semantic_eval_corpus(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """corpus_name: semantic_graph_memory
eval_version: 2
documents:
  - fixture_name: integration_graph_alpha
    source_filename: integration-alpha-report.pdf
    expected_concepts:
      - concept_key: integration_threshold
        minimum_evidence_count: 2
        required_source_types:
          - chunk
          - table
        expected_category_keys:
          - integration_governance
      - concept_key: integration_owner
        minimum_evidence_count: 1
        required_source_types:
          - chunk
        expected_category_keys:
          - integration_governance
  - fixture_name: integration_graph_beta
    source_filename: integration-beta-report.pdf
    expected_concepts:
      - concept_key: integration_threshold
        minimum_evidence_count: 2
        required_source_types:
          - chunk
          - table
        expected_category_keys:
          - integration_governance
      - concept_key: integration_owner
        minimum_evidence_count: 1
        required_source_types:
          - chunk
        expected_category_keys:
          - integration_governance
"""
    )


def _build_parsed_document(
    *, title: str, threshold_phrase: str, owner_phrase: str
) -> ParsedDocument:
    chunk_text = (
        f"{title} keeps the {threshold_phrase} in force and assigns an {owner_phrase} "
        f"that depends on the {threshold_phrase} for every rollout."
    )
    table_rows = [
        ["Tier", "Threshold"],
        ["alpha", threshold_phrase],
    ]
    segment = ParsedTableSegment(
        segment_index=0,
        segment_order=0,
        source_table_ref="table-0",
        title=f"{title} Threshold Matrix",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        metadata={
            "caption": f"{title} Threshold Matrix",
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
        title=f"{title} Threshold Matrix",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        search_text=f"{title} {threshold_phrase} {owner_phrase}",
        preview_text=f"Tier | Threshold\nalpha | {threshold_phrase}",
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
            "source_titles": [f"{title} Threshold Matrix"],
        },
        segments=[segment],
    )
    exported_payload = {
        "name": title,
        "texts": [{"self_ref": "chunk-0", "text": chunk_text}],
        "tables": [{"self_ref": "table-0", "data": {"grid": []}}],
        "pictures": [],
    }
    return ParsedDocument(
        title=title,
        page_count=1,
        yaml_text=f"document: {title.lower().replace(' ', '-')}\n",
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
        task = claim_next_agent_task(session, "semantic-graph-worker")
        assert task is not None
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)
        return task.id


def _approve_all_semantic_reviews(client, document_id: UUID) -> None:
    semantics_response = client.get(f"/documents/{document_id}/semantics/latest")
    assert semantics_response.status_code == 200
    semantics = semantics_response.json()
    assert semantics["assertion_count"] == 2
    for assertion in semantics["assertions"]:
        review_response = client.post(
            f"/documents/{document_id}/semantics/latest/assertions/{assertion['assertion_id']}/review",
            json={
                "review_status": "approved",
                "review_note": "Approved for graph-memory rollout.",
                "reviewed_by": "operator@example.com",
            },
        )
        assert review_response.status_code == 200
        for binding in assertion["category_bindings"]:
            binding_response = client.post(
                (
                    "/documents/"
                    f"{document_id}/semantics/latest/assertion-category-bindings/{binding['binding_id']}/review"
                ),
                json={
                    "review_status": "approved",
                    "review_note": "Approved for graph-memory rollout.",
                    "reviewed_by": "operator@example.com",
                },
            )
            assert binding_response.status_code == 200


def test_semantic_graph_roundtrip(
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
    workflow_version = "semantic_graph_roundtrip"

    uploads = [
        (
            "integration-alpha-report.pdf",
            _build_parsed_document(
                title="Integration Alpha Report",
                threshold_phrase="integration threshold",
                owner_phrase="integration owner",
            ),
        ),
        (
            "integration-beta-report.pdf",
            _build_parsed_document(
                title="Integration Beta Report",
                threshold_phrase="integration threshold",
                owner_phrase="integration owner",
            ),
        ),
    ]

    document_ids: list[UUID] = []
    run_ids: list[UUID] = []
    for source_filename, parsed_document in uploads:
        create_response = client.post(
            "/documents",
            files={
                "file": (
                    source_filename,
                    valid_test_pdf_bytes() + f"\n% {source_filename}\n".encode(),
                    "application/pdf",
                )
            },
        )
        assert create_response.status_code == 202
        document_ids.append(UUID(create_response.json()["document_id"]))
        run_ids.append(UUID(create_response.json()["run_id"]))
        processed_run_id = postgres_integration_harness.process_next_run(
            StubParser(parsed_document)
        )
        assert processed_run_id == run_ids[-1]

    for document_id in document_ids:
        semantics_response = client.get(f"/documents/{document_id}/semantics/latest")
        assert semantics_response.status_code == 200
        semantics = semantics_response.json()
        assert semantics["evaluation_summary"]["all_expectations_passed"] is True
        assert semantics["assertion_count"] == 2
        _approve_all_semantic_reviews(client, document_id)

    with postgres_integration_harness.session_factory() as session:
        build_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="build_shadow_semantic_graph",
                input={
                    "document_ids": [str(document_id) for document_id in document_ids],
                    "minimum_review_status": "approved",
                    "min_shared_documents": 2,
                    "score_threshold": 0.45,
                },
                workflow_version=workflow_version,
            ),
        )
        build_task_id = build_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        build_task_row = session.get(AgentTask, build_task_id)
        assert build_task_row is not None
        build_payload = build_task_row.result_json["payload"]
        assert build_payload["shadow_graph"]["edge_count"] == 2
        assert build_payload["shadow_graph"]["summary"]["relation_key_counts"] == {
            "concept_depends_on_concept": 1,
            "concept_related_to_concept": 1,
        }
        assert any(
            metric["metric_key"] == "memory_compaction" and metric["passed"]
            for metric in build_payload["shadow_graph"]["success_metrics"]
        )

        evaluate_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="evaluate_semantic_relation_extractor",
                input={
                    "document_ids": [str(document_id) for document_id in document_ids],
                    "minimum_review_status": "approved",
                    "baseline_min_shared_documents": 3,
                    "candidate_score_threshold": 0.45,
                    "expected_min_shared_documents": 1,
                },
                workflow_version=workflow_version,
            ),
        )
        evaluate_task_id = evaluate_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        evaluate_task_row = session.get(AgentTask, evaluate_task_id)
        assert evaluate_task_row is not None
        evaluation_payload = evaluate_task_row.result_json["payload"]
        assert evaluation_payload["summary"]["candidate_expected_recall"] == 1.0
        assert evaluation_payload["summary"]["baseline_expected_recall"] == 0.0
        assert any(
            metric["metric_key"] == "bitter_lesson_alignment" and metric["passed"]
            for metric in evaluation_payload["success_metrics"]
        )

        triage_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="triage_semantic_graph_disagreements",
                input={
                    "target_task_id": str(evaluate_task_id),
                    "min_score": 0.45,
                    "expected_only": True,
                },
                workflow_version=workflow_version,
            ),
        )
        triage_task_id = triage_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        triage_task_row = session.get(AgentTask, triage_task_id)
        assert triage_task_row is not None
        triage_payload = triage_task_row.result_json["payload"]
        assert triage_payload["disagreement_report"]["issue_count"] == 2
        assert triage_payload["recommendation"]["next_action"] == "draft_graph_promotions"

        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_graph_promotions",
                input={
                    "source_task_id": str(triage_task_id),
                    "rationale": "Promote approved cross-document graph memory.",
                    "min_score": 0.45,
                },
                workflow_version=workflow_version,
            ),
        )
        draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        draft_task_row = session.get(AgentTask, draft_task_id)
        assert draft_task_row is not None
        draft_payload = draft_task_row.result_json["payload"]["draft"]
        assert len(draft_payload["promoted_edges"]) == 2
        assert {edge["relation_key"] for edge in draft_payload["promoted_edges"]} == {
            "concept_related_to_concept",
            "concept_depends_on_concept",
        }
        assert any(
            metric["metric_key"] == "semantic_integrity" and metric["passed"]
            for metric in draft_payload["success_metrics"]
        )

        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_draft_graph_promotions",
                input={
                    "target_task_id": str(draft_task_id),
                    "min_supporting_document_count": 2,
                    "max_conflict_count": 0,
                    "require_current_ontology_snapshot": True,
                },
                workflow_version=workflow_version,
            ),
        )
        verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        verify_task_row = session.get(AgentTask, verify_task_id)
        assert verify_task_row is not None
        verify_payload = verify_task_row.result_json["payload"]
        assert verify_payload["verification"]["outcome"] == "passed"
        assert verify_payload["summary"]["supported_edge_count"] == 2
        assert any(
            metric["metric_key"] == "semantic_integrity" and metric["passed"]
            for metric in verify_payload["success_metrics"]
        )

        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_graph_promotions",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "Publish the verified semantic graph memory snapshot.",
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
                approval_note="publish the verified semantic graph memory snapshot",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_task_row = session.get(AgentTask, apply_task_id)
        assert apply_task_row is not None
        apply_payload = apply_task_row.result_json["payload"]
        assert apply_payload["applied_edge_count"] == 2
        active_graph = get_active_semantic_graph_snapshot(session)
        assert active_graph is not None
        assert active_graph.graph_version == apply_payload["applied_graph_version"]
        assert len((active_graph.payload_json or {}).get("edges") or []) == 2

        brief_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="prepare_semantic_generation_brief",
                input={
                    "title": "Integration Graph Memory Brief",
                    "goal": "Summarize grounded integration governance memory across documents.",
                    "audience": "Operators",
                    "document_ids": [str(document_id) for document_id in document_ids],
                    "concept_keys": ["integration_threshold"],
                    "target_length": "medium",
                    "review_policy": "approved_only",
                },
                workflow_version=workflow_version,
            ),
        )
        brief_task_id = brief_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        brief_task_row = session.get(AgentTask, brief_task_id)
        assert brief_task_row is not None
        brief_payload = brief_task_row.result_json["payload"]["brief"]
        assert brief_payload["graph_summary"]["edge_count"] == 2
        assert set(brief_payload["selected_concept_keys"]) == {
            "integration_owner",
            "integration_threshold",
        }
        assert any(
            section["title"] == "Cross-Document Relationships"
            for section in brief_payload["sections"]
        )
        assert any(claim["graph_edge_ids"] for claim in brief_payload["claim_candidates"])
        assert any(
            "depends on concept" in claim["summary"].lower()
            for claim in brief_payload["claim_candidates"]
            if claim["graph_edge_ids"]
        )
        assert any(
            metric["metric_key"] == "semantic_integrity" and metric["passed"]
            for metric in brief_payload["success_metrics"]
        )

    build_context = client.get(f"/agent-tasks/{build_task_id}/context")
    assert build_context.status_code == 200
    assert build_context.json()["summary"]["metrics"]["edge_count"] == 2

    apply_context = client.get(f"/agent-tasks/{apply_task_id}/context")
    assert apply_context.status_code == 200
    assert apply_context.json()["summary"]["approval_state"] == "approved"

    brief_context = client.get(f"/agent-tasks/{brief_task_id}/context")
    assert brief_context.status_code == 200
    assert brief_context.json()["summary"]["next_action"] == (
        "Create draft_semantic_grounded_document to render a grounded knowledge brief."
    )
