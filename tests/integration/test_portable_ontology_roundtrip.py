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


def _write_upper_ontology(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """registry_name: portable_upper_ontology
registry_version: portable-upper-ontology-v1
upper_ontology_version: portable-upper-ontology-v1
categories: []
concepts: []
relations:
  - relation_key: document_mentions_concept
    preferred_label: Document Mentions Concept
  - relation_key: concept_related_to_concept
    preferred_label: Concept Related To Concept
entity_types:
  - entity_type: document
    preferred_label: Document
  - entity_type: concept
    preferred_label: Concept
  - entity_type: literal
    preferred_label: Literal
"""
    )


def _write_empty_semantic_eval_corpus(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """corpus_name: portable_semantic_eval
eval_version: 2
documents: []
"""
    )


def _build_parsed_document(*, title: str, phrase: str) -> ParsedDocument:
    title_slug = phrase.title()
    chunk_text = (
        f"{title_slug} target remains under active review. "
        f"The {phrase} dashboard is reviewed weekly."
    )
    table_rows = [
        ["Metric", "Target"],
        [title_slug, phrase],
    ]
    segment = ParsedTableSegment(
        segment_index=0,
        segment_order=0,
        source_table_ref="table-0",
        title=f"{title_slug} Matrix",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        metadata={
            "caption": f"{title_slug} Matrix",
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
        title=f"{title_slug} Matrix",
        heading="Section 1",
        page_from=1,
        page_to=1,
        row_count=len(table_rows),
        col_count=2,
        rows=table_rows,
        search_text=f"{title_slug} Matrix {phrase}",
        preview_text=f"Metric | Target\n{title_slug} | {phrase}",
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
            "source_titles": [f"{title_slug} Matrix"],
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
        task = claim_next_agent_task(session, "portable-ontology-worker")
        assert task is not None
        process_agent_task(session, task.id, postgres_integration_harness.storage_service)
        return task.id


@pytest.mark.parametrize(
    ("title", "source_filename", "phrase", "expected_concept_key"),
    [
        (
            "Incident Review",
            "incident-review.pdf",
            "incident response latency",
            "incident_response_latency",
        ),
        (
            "Vendor Escalation Memo",
            "vendor-escalation.pdf",
            "vendor escalation owner",
            "vendor_escalation_owner",
        ),
    ],
)
def test_portable_ontology_roundtrip_is_domain_agnostic(
    postgres_integration_harness,
    monkeypatch,
    tmp_path: Path,
    title: str,
    source_filename: str,
    phrase: str,
    expected_concept_key: str,
) -> None:
    upper_ontology_path = tmp_path / "config" / "upper_ontology.yaml"
    eval_corpus_path = tmp_path / "docs" / "semantic_evaluation_corpus.yaml"
    _write_upper_ontology(upper_ontology_path)
    _write_empty_semantic_eval_corpus(eval_corpus_path)
    monkeypatch.delenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", raising=False)
    monkeypatch.setenv("DOCLING_SYSTEM_UPPER_ONTOLOGY_PATH", str(upper_ontology_path))
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_EVALUATION_CORPUS_PATH", str(eval_corpus_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    workflow_version = "portable_ontology_integration"
    client = postgres_integration_harness.client

    with postgres_integration_harness.session_factory() as session:
        initialize_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="initialize_workspace_ontology",
                input={},
                workflow_version=workflow_version,
            ),
        )
        initialize_task_id = initialize_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        initialize_task_row = session.get(AgentTask, initialize_task_id)
        assert initialize_task_row is not None
        initialize_payload = initialize_task_row.result_json["payload"]
        assert initialize_payload["snapshot"]["ontology_version"] == "portable-upper-ontology-v1"
        assert initialize_payload["snapshot"]["concept_count"] == 0
        assert any(
            metric["metric_key"] == "portable_bootstrap" and metric["passed"]
            for metric in initialize_payload["success_metrics"]
        )

        snapshot_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="get_active_ontology_snapshot",
                input={},
                workflow_version=workflow_version,
            ),
        )
        snapshot_task_id = snapshot_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        snapshot_task_row = session.get(AgentTask, snapshot_task_id)
        assert snapshot_task_row is not None
        snapshot_payload = snapshot_task_row.result_json["payload"]
        assert snapshot_payload["snapshot"]["relation_keys"] == [
            "concept_related_to_concept",
            "document_mentions_concept",
        ]

    create_response = client.post(
        "/documents",
        files={
            "file": (
                source_filename,
                valid_test_pdf_bytes(),
                "application/pdf",
            )
        },
    )
    assert create_response.status_code == 202
    document_id = UUID(create_response.json()["document_id"])
    run_id = UUID(create_response.json()["run_id"])

    processed_run_id = postgres_integration_harness.process_next_run(
        StubParser(_build_parsed_document(title=title, phrase=phrase))
    )
    assert processed_run_id == run_id

    initial_semantics_response = client.get(f"/documents/{document_id}/semantics/latest")
    assert initial_semantics_response.status_code == 200
    initial_semantics = initial_semantics_response.json()
    assert initial_semantics["assertion_count"] == 0
    assert initial_semantics["ontology_snapshot_id"] is not None
    assert initial_semantics["upper_ontology_version"] == "portable-upper-ontology-v1"

    with postgres_integration_harness.session_factory() as session:
        discover_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="discover_semantic_bootstrap_candidates",
                input={
                    "document_ids": [str(document_id)],
                    "max_candidates": 8,
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
        discover_payload = discover_task_row.result_json["payload"]
        report = discover_payload["report"]
        candidate = next(
            row for row in report["candidates"] if row["concept_key"] == expected_concept_key
        )
        candidate_id = candidate["candidate_id"]
        assert any(
            metric["metric_key"] == "bitter_lesson_alignment" and metric["passed"]
            for metric in report["success_metrics"]
        )

        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_ontology_extension",
                input={
                    "source_task_id": str(discover_task_id),
                    "candidate_ids": [candidate_id],
                    "rationale": "extend the workspace ontology from corpus evidence",
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
        assert draft_payload["proposed_ontology_version"] == "portable-upper-ontology-v1.1"
        assert draft_payload["operations"][0]["concept_key"] == expected_concept_key

        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_draft_ontology_extension",
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
        verify_payload = verify_task_row.result_json["payload"]
        assert verify_payload["verification"]["outcome"] == "passed"
        assert any(
            metric["metric_key"] == "semantic_value_gain" and metric["passed"]
            for metric in verify_payload["success_metrics"]
        )

        apply_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="apply_ontology_extension",
                input={
                    "draft_task_id": str(draft_task_id),
                    "verification_task_id": str(verify_task_id),
                    "reason": "publish the verified ontology extension",
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
                approved_by="ontology-operator@example.com",
                approval_note="publish the verified ontology extension",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        apply_task_row = session.get(AgentTask, apply_task_id)
        assert apply_task_row is not None
        apply_payload = apply_task_row.result_json["payload"]
        assert apply_payload["applied_ontology_version"] == "portable-upper-ontology-v1.1"
        assert any(
            metric["metric_key"] == "semantic_contract_published" and metric["passed"]
            for metric in apply_payload["success_metrics"]
        )

        reprocess_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="enqueue_document_reprocess",
                input={
                    "document_id": str(document_id),
                    "source_task_id": str(apply_task_id),
                    "reason": "refresh the document under the new ontology snapshot",
                },
                workflow_version=workflow_version,
            ),
        )
        reprocess_task_id = reprocess_task.task_id
        approve_agent_task(
            session,
            reprocess_task_id,
            AgentTaskApprovalRequest(
                approved_by="ontology-operator@example.com",
                approval_note="refresh semantics under the new ontology snapshot",
            ),
        )

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        reprocess_task_row = session.get(AgentTask, reprocess_task_id)
        assert reprocess_task_row is not None
        latest_run_id = UUID(reprocess_task_row.result_json["payload"]["reprocess"]["run_id"])

    rerun_id = postgres_integration_harness.process_next_run(
        StubParser(_build_parsed_document(title=title, phrase=phrase))
    )
    assert rerun_id == latest_run_id

    final_semantics_response = client.get(f"/documents/{document_id}/semantics/latest")
    assert final_semantics_response.status_code == 200
    final_semantics = final_semantics_response.json()
    assert final_semantics["run_id"] == str(latest_run_id)
    assert final_semantics["registry_version"] == "portable-upper-ontology-v1.1"
    assert final_semantics["assertion_count"] >= 1
    assertion = next(
        row for row in final_semantics["assertions"] if row["concept_key"] == expected_concept_key
    )

    assertion_review_response = client.post(
        f"/documents/{document_id}/semantics/latest/assertions/{assertion['assertion_id']}/review",
        json={
            "review_status": "approved",
            "review_note": "Approve the corpus-derived concept before fact generation.",
            "reviewed_by": "ontology-operator@example.com",
        },
    )
    assert assertion_review_response.status_code == 200

    with postgres_integration_harness.session_factory() as session:
        fact_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="build_document_fact_graph",
                input={
                    "document_id": str(document_id),
                    "minimum_review_status": "approved",
                },
                workflow_version=workflow_version,
            ),
        )
        fact_task_id = fact_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        fact_task_row = session.get(AgentTask, fact_task_id)
        assert fact_task_row is not None
        fact_payload = fact_task_row.result_json["payload"]
        assert fact_payload["fact_count"] >= 1
        assert any(
            metric["metric_key"] == "semantic_integrity" and metric["passed"]
            for metric in fact_payload["success_metrics"]
        )

        brief_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="prepare_semantic_generation_brief",
                input={
                    "title": f"{title} Brief",
                    "goal": f"Summarize the knowledge base guidance on {phrase}.",
                    "audience": "Operators",
                    "document_ids": [str(document_id)],
                    "concept_keys": [expected_concept_key],
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
        assert brief_payload["claim_candidates"][0]["fact_ids"]
        assert brief_payload["semantic_dossier"][0]["facts"]
        assert any(
            metric["metric_key"] == "approved_fact_support_ratio" and metric["passed"]
            for metric in brief_payload["success_metrics"]
        )

        draft_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="draft_semantic_grounded_document",
                input={"target_task_id": str(brief_task_id)},
                workflow_version=workflow_version,
            ),
        )
        grounded_draft_task_id = draft_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        grounded_draft_task_row = session.get(AgentTask, grounded_draft_task_id)
        assert grounded_draft_task_row is not None
        grounded_draft_payload = grounded_draft_task_row.result_json["payload"]["draft"]
        assert grounded_draft_payload["fact_index"]
        assert grounded_draft_payload["claims"][0]["fact_ids"]

        verify_task = create_agent_task(
            session,
            AgentTaskCreateRequest(
                task_type="verify_semantic_grounded_document",
                input={
                    "target_task_id": str(grounded_draft_task_id),
                    "max_unsupported_claim_count": 0,
                    "require_full_claim_traceability": True,
                    "require_full_concept_coverage": True,
                },
                workflow_version=workflow_version,
            ),
        )
        grounded_verify_task_id = verify_task.task_id

    _process_next_task(postgres_integration_harness)

    with postgres_integration_harness.session_factory() as session:
        grounded_verify_task_row = session.get(AgentTask, grounded_verify_task_id)
        assert grounded_verify_task_row is not None
        grounded_verify_payload = grounded_verify_task_row.result_json["payload"]
        assert grounded_verify_payload["verification"]["outcome"] == "passed"
        assert grounded_verify_payload["summary"]["fact_ref_coverage_ratio"] == 1.0
        assert grounded_verify_payload["summary"]["required_concept_coverage_ratio"] == 1.0
        assert any(
            metric["metric_key"] == "semantic_integrity" and metric["passed"]
            for metric in grounded_verify_payload["success_metrics"]
        )
