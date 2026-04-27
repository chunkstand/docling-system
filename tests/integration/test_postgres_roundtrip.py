from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.models import (
    DocumentFigure,
    DocumentTable,
    RetrievalEvidenceSpan,
    SearchRequestResultSpan,
    SemanticGraphSourceKind,
    SemanticOntologySourceKind,
)
from app.services.docling_parser import (
    ParsedChunk,
    ParsedDocument,
    ParsedFigure,
    ParsedTable,
    ParsedTableSegment,
)
from app.services.semantic_graph import persist_semantic_graph_snapshot
from app.services.semantic_registry import (
    clear_semantic_registry_cache,
    ensure_workspace_semantic_registry,
    get_active_semantic_ontology_snapshot,
    persist_semantic_ontology_snapshot,
)
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


class FailingParser:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def parse_pdf(self, source_path, *, source_filename=None) -> ParsedDocument:
        assert source_path.exists()
        assert source_filename
        raise self.error


def _build_parsed_document(
    *,
    title: str | None = "Integration Report",
    figure_caption: str = "Integration system diagram",
) -> ParsedDocument:
    chunk_text = "Integration threshold guidance keeps active retrieval grounded."
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
    figure = ParsedFigure(
        figure_index=0,
        source_figure_ref="figure-0",
        caption=figure_caption,
        heading="Section 1",
        page_from=1,
        page_to=1,
        confidence=0.99,
        metadata={
            "caption_resolution_source": "explicit_ref",
            "caption_candidates": [figure_caption],
            "caption_attachment_confidence": 1.0,
            "source_confidence": 0.99,
            "annotations": [],
            "provenance": [
                {
                    "page_no": 1,
                    "bbox": {"l": 0, "t": 0, "r": 1, "b": 1, "coord_origin": "TOPLEFT"},
                    "charspan": [0, 1],
                }
            ],
            "source_artifact_sha256": "figure-sha",
        },
    )
    exported_payload = {
        "name": title,
        "texts": [{"self_ref": "chunk-0", "text": chunk_text}],
        "tables": [{"self_ref": "table-0", "data": {"grid": []}}],
        "pictures": [{"self_ref": "figure-0", "captions": ["caption-0"], "prov": []}],
    }
    return ParsedDocument(
        title=title,
        page_count=1,
        yaml_text="document: integration-report\n",
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
        figures=[figure],
    )


def _configure_sample_semantics(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv(
        "DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH",
        str(repo_root / "config" / "semantic_registry.yaml"),
    )
    monkeypatch.setenv(
        "DOCLING_SYSTEM_SEMANTIC_EVALUATION_CORPUS_PATH",
        str(repo_root / "docs" / "semantic_evaluation_corpus.yaml"),
    )
    get_settings.cache_clear()
    clear_semantic_registry_cache()


def test_upload_process_search_and_evaluate_document_roundtrip(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    _configure_sample_semantics(monkeypatch)
    client = postgres_integration_harness.client
    upload_files = {
        "file": (
            "integration-report.pdf",
            valid_test_pdf_bytes(),
            "application/pdf",
        )
    }

    create_response = client.post(
        "/documents",
        files=upload_files,
    )
    assert create_response.status_code == 202
    create_body = create_response.json()
    document_id = create_body["document_id"]
    run_id = UUID(create_body["run_id"])

    processed_run_id = postgres_integration_harness.process_next_run(
        StubParser(_build_parsed_document())
    )
    assert processed_run_id == run_id

    detail_response = client.get(f"/documents/{document_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["is_searchable"] is True
    assert detail["active_run_id"] == str(run_id)
    assert detail["latest_run_id"] == str(run_id)
    assert detail["latest_validation_status"] == "passed"
    assert detail["latest_run_promoted"] is True
    assert detail["table_count"] == 1
    assert detail["figure_count"] == 1
    assert detail["latest_evaluation"]["status"] == "completed"

    quality_response = client.get("/quality/summary")
    assert quality_response.status_code == 200
    quality = quality_response.json()
    assert quality["document_count"] == 1
    assert quality["completed_latest_evaluations"] == 1
    assert quality["total_failed_queries"] == 0

    with postgres_integration_harness.session_factory() as session:
        session.execute(delete(RetrievalEvidenceSpan).where(RetrievalEvidenceSpan.run_id == run_id))
        session.commit()

    search_response = client.post(
        "/search",
        json={"query": "integration threshold", "mode": "keyword", "limit": 5},
    )
    assert search_response.status_code == 200
    search_request_id = search_response.headers["X-Search-Request-Id"]
    assert search_request_id
    results = search_response.json()
    assert {"chunk", "table"}.issubset({result["result_type"] for result in results})
    assert all(result["run_id"] == str(run_id) for result in results)
    assert all(result["evidence_spans"] for result in results)
    assert all(
        span["content_sha256"] and span["source_snapshot_sha256"]
        for result in results
        for span in result["evidence_spans"]
    )

    search_detail_response = client.get(f"/search/requests/{search_request_id}")
    assert search_detail_response.status_code == 200
    search_detail = search_detail_response.json()
    assert search_detail["details"]["span_candidate_count"] >= 1
    assert search_detail["details"]["selected_result_span_count"] == len(results)
    assert search_detail["details"]["retrieval_span_backfill"]["rebuilt_run_count"] == 1
    assert all(result["evidence_spans"] for result in search_detail["results"])

    search_evidence_response = client.get(f"/search/requests/{search_request_id}/evidence-package")
    assert search_evidence_response.status_code == 200
    search_evidence = search_evidence_response.json()
    assert search_evidence["audit_checklist"]["has_retrieval_evidence_spans"] is True
    assert search_evidence["audit_checklist"]["all_results_have_retrieval_evidence_spans"] is True
    assert search_evidence["audit_checklist"]["all_span_citations_hashed"] is True
    assert all(item["retrieval_evidence_spans"] for item in search_evidence["source_evidence"])

    chunks_response = client.get(f"/documents/{document_id}/chunks")
    assert chunks_response.status_code == 200
    assert len(chunks_response.json()) == 1

    tables_response = client.get(f"/documents/{document_id}/tables")
    assert tables_response.status_code == 200
    tables = tables_response.json()
    assert len(tables) == 1
    table_id = tables[0]["table_id"]

    table_detail_response = client.get(f"/documents/{document_id}/tables/{table_id}")
    assert table_detail_response.status_code == 200
    assert table_detail_response.json()["metadata"]["source_segment_count"] == 1

    figures_response = client.get(f"/documents/{document_id}/figures")
    assert figures_response.status_code == 200
    figures = figures_response.json()
    assert len(figures) == 1
    figure_id = figures[0]["figure_id"]

    figure_detail_response = client.get(f"/documents/{document_id}/figures/{figure_id}")
    assert figure_detail_response.status_code == 200
    assert figure_detail_response.json()["caption"] == "Integration system diagram"

    semantics_response = client.get(f"/documents/{document_id}/semantics/latest")
    assert semantics_response.status_code == 200
    semantics = semantics_response.json()
    assert semantics["status"] == "completed"
    assert semantics["registry_version"] == "semantics-layer-foundation-alpha.2"
    assert semantics["artifact_schema_version"] == "2.1"
    assert semantics["evaluation_status"] == "completed"
    assert semantics["evaluation_version"] == 2
    assert semantics["evaluation_summary"]["all_expectations_passed"] is True
    assert semantics["assertion_count"] == 2
    assert {
        (binding["concept_key"], binding["category_key"], binding["review_status"])
        for binding in semantics["concept_category_bindings"]
    } == {
        ("integration_threshold", "integration_governance", "approved"),
        ("system_diagram", "system_representation", "approved"),
    }
    assertions_by_concept = {
        assertion["concept_key"]: assertion for assertion in semantics["assertions"]
    }
    assert sorted(assertions_by_concept["integration_threshold"]["source_types"]) == [
        "chunk",
        "table",
    ]
    assert assertions_by_concept["system_diagram"]["source_types"] == ["figure"]
    assert assertions_by_concept["integration_threshold"]["epistemic_status"] == "observed"
    assert assertions_by_concept["integration_threshold"]["context_scope"] == "document_run"
    assert assertions_by_concept["integration_threshold"]["review_status"] == "candidate"
    assert assertions_by_concept["integration_threshold"]["category_bindings"] == [
        {
            "binding_id": assertions_by_concept["integration_threshold"]["category_bindings"][0][
                "binding_id"
            ],
            "category_key": "integration_governance",
            "category_label": "Integration Governance",
            "binding_type": "assertion_category",
            "created_from": "derived",
            "review_status": "candidate",
            "details": assertions_by_concept["integration_threshold"]["category_bindings"][0][
                "details"
            ],
        }
    ]
    assert assertions_by_concept["system_diagram"]["category_bindings"] == [
        {
            "binding_id": assertions_by_concept["system_diagram"]["category_bindings"][0][
                "binding_id"
            ],
            "category_key": "system_representation",
            "category_label": "System Representation",
            "binding_type": "assertion_category",
            "created_from": "derived",
            "review_status": "candidate",
            "details": assertions_by_concept["system_diagram"]["category_bindings"][0]["details"],
        }
    ]
    threshold_table_evidence = next(
        evidence
        for evidence in assertions_by_concept["integration_threshold"]["evidence"]
        if evidence["source_type"] == "table"
    )
    system_diagram_evidence = assertions_by_concept["system_diagram"]["evidence"][0]
    assert (
        threshold_table_evidence["source_artifact_api_path"]
        == f"/documents/{document_id}/tables/{table_id}/artifacts/json"
    )
    assert (
        system_diagram_evidence["source_artifact_api_path"]
        == f"/documents/{document_id}/figures/{figure_id}/artifacts/json"
    )
    assert "source_artifact_path" not in threshold_table_evidence
    assert "yaml_artifact_path" not in threshold_table_evidence["details"]

    assert client.get(f"/documents/{document_id}/artifacts/json").status_code == 200
    assert client.get(f"/documents/{document_id}/artifacts/yaml").status_code == 200
    table_json_response = client.get(f"/documents/{document_id}/tables/{table_id}/artifacts/json")
    assert table_json_response.status_code == 200
    table_yaml_response = client.get(f"/documents/{document_id}/tables/{table_id}/artifacts/yaml")
    assert table_yaml_response.status_code == 200
    figure_json_response = client.get(
        f"/documents/{document_id}/figures/{figure_id}/artifacts/json"
    )
    assert figure_json_response.status_code == 200
    figure_yaml_response = client.get(
        f"/documents/{document_id}/figures/{figure_id}/artifacts/yaml"
    )
    assert figure_yaml_response.status_code == 200

    table_artifact = table_json_response.json()
    figure_artifact = figure_json_response.json()
    assert "artifact_sha256" not in table_artifact
    assert "artifact_sha256" not in figure_artifact

    with postgres_integration_harness.session_factory() as session:
        table_row = session.execute(
            select(DocumentTable).where(DocumentTable.id == UUID(table_id))
        ).scalar_one()
        figure_row = session.execute(
            select(DocumentFigure).where(DocumentFigure.id == UUID(figure_id))
        ).scalar_one()
        retrieval_span_count = len(
            session.execute(
                select(RetrievalEvidenceSpan).where(RetrievalEvidenceSpan.run_id == run_id)
            )
            .scalars()
            .all()
        )
        result_span_count = len(
            session.execute(
                select(SearchRequestResultSpan).where(
                    SearchRequestResultSpan.search_request_id == UUID(search_request_id)
                )
            )
            .scalars()
            .all()
        )

    assert retrieval_span_count >= 2
    assert result_span_count >= len(results)

    assert (
        hashlib.sha256(Path(table_row.json_path).read_bytes()).hexdigest()
        == (table_row.metadata_json["audit"]["json_artifact_sha256"])
    )
    assert (
        hashlib.sha256(Path(table_row.yaml_path).read_bytes()).hexdigest()
        == (table_row.metadata_json["audit"]["yaml_artifact_sha256"])
    )
    assert (
        hashlib.sha256(Path(figure_row.json_path).read_bytes()).hexdigest()
        == (figure_row.metadata_json["audit"]["json_artifact_sha256"])
    )
    assert (
        hashlib.sha256(Path(figure_row.yaml_path).read_bytes()).hexdigest()
        == (figure_row.metadata_json["audit"]["yaml_artifact_sha256"])
    )
    semantic_artifact_response = client.get(
        f"/documents/{document_id}/semantics/latest/artifacts/json"
    )
    assert semantic_artifact_response.status_code == 200
    semantic_artifact = semantic_artifact_response.json()
    assert semantic_artifact["schema_name"] == "docling.semantic_pass"
    assert semantic_artifact["schema_version"] == "2.1"
    assert semantic_artifact["registry"]["version"] == "semantics-layer-foundation-alpha.2"
    assert semantic_artifact["evaluation"]["version"] == 2
    assert semantic_artifact["evaluation"]["summary"]["all_expectations_passed"] is True
    assert {
        (binding["concept_key"], binding["category_key"], binding["review_status"])
        for binding in semantic_artifact["concept_category_bindings"]
    } == {
        ("integration_threshold", "integration_governance", "approved"),
        ("system_diagram", "system_representation", "approved"),
    }
    artifact_threshold_table_evidence = next(
        evidence
        for assertion in semantic_artifact["assertions"]
        if assertion["concept_key"] == "integration_threshold"
        for evidence in assertion["evidence"]
        if evidence["source_type"] == "table"
    )
    artifact_threshold_assertion = next(
        assertion
        for assertion in semantic_artifact["assertions"]
        if assertion["concept_key"] == "integration_threshold"
    )
    assert artifact_threshold_assertion["epistemic_status"] == "observed"
    assert artifact_threshold_assertion["context_scope"] == "document_run"
    assert artifact_threshold_assertion["review_status"] == "candidate"
    assert (
        artifact_threshold_assertion["category_bindings"][0]["category_key"]
        == "integration_governance"
    )
    assert artifact_threshold_assertion["category_bindings"][0]["review_status"] == "candidate"
    assert "source_artifact_path" not in artifact_threshold_table_evidence
    assert "yaml_artifact_path" not in artifact_threshold_table_evidence["details"]
    assert (
        client.get(f"/documents/{document_id}/semantics/latest/artifacts/yaml").status_code == 200
    )

    evaluation_response = client.get(f"/documents/{document_id}/evaluations/latest")
    assert evaluation_response.status_code == 200
    evaluation = evaluation_response.json()
    assert evaluation["status"] == "completed"
    assert evaluation["summary"]["structural_passed"] is True
    assert "retrieval_rank_metrics" in evaluation["summary"]
    assert evaluation["passed_queries"] == evaluation["query_count"]
    assert evaluation["query_results"]
    assert "candidate_reciprocal_rank" in evaluation["query_results"][0]["details"]

    duplicate_response = client.post(
        "/documents",
        files=upload_files,
    )
    assert duplicate_response.status_code == 200
    duplicate_body = duplicate_response.json()
    assert duplicate_body["duplicate"] is True
    assert duplicate_body["active_run_id"] == str(run_id)


def test_semantic_reviews_persist_across_reruns_and_emit_continuity(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    _configure_sample_semantics(monkeypatch)
    client = postgres_integration_harness.client
    upload_files = {
        "file": (
            "integration-report.pdf",
            valid_test_pdf_bytes(),
            "application/pdf",
        )
    }

    create_response = client.post("/documents", files=upload_files)
    assert create_response.status_code == 202
    document_id = create_response.json()["document_id"]
    original_run_id = UUID(create_response.json()["run_id"])

    postgres_integration_harness.process_next_run(StubParser(_build_parsed_document()))

    first_semantics = client.get(f"/documents/{document_id}/semantics/latest")
    assert first_semantics.status_code == 200
    first_payload = first_semantics.json()
    threshold_assertion = next(
        assertion
        for assertion in first_payload["assertions"]
        if assertion["concept_key"] == "integration_threshold"
    )
    threshold_binding = threshold_assertion["category_bindings"][0]

    assertion_review_response = client.post(
        f"/documents/{document_id}/semantics/latest/assertions/{threshold_assertion['assertion_id']}/review",
        json={
            "review_status": "approved",
            "review_note": "Confirmed governance concept for this document.",
            "reviewed_by": "semantic-operator",
        },
    )
    assert assertion_review_response.status_code == 200
    assert assertion_review_response.json()["scope"] == "assertion"
    assert assertion_review_response.json()["review_status"] == "approved"

    binding_review_response = client.post(
        f"/documents/{document_id}/semantics/latest/assertion-category-bindings/{threshold_binding['binding_id']}/review",
        json={
            "review_status": "approved",
            "review_note": "Confirmed category binding for governance.",
            "reviewed_by": "semantic-operator",
        },
    )
    assert binding_review_response.status_code == 200
    assert binding_review_response.json()["scope"] == "assertion_category_binding"
    assert binding_review_response.json()["review_status"] == "approved"

    reviewed_semantics = client.get(f"/documents/{document_id}/semantics/latest")
    assert reviewed_semantics.status_code == 200
    reviewed_payload = reviewed_semantics.json()
    reviewed_threshold_assertion = next(
        assertion
        for assertion in reviewed_payload["assertions"]
        if assertion["concept_key"] == "integration_threshold"
    )
    assert reviewed_threshold_assertion["review_status"] == "approved"
    assert reviewed_threshold_assertion["details"]["review_overlay"]["review_note"] == (
        "Confirmed governance concept for this document."
    )
    assert reviewed_threshold_assertion["category_bindings"][0]["review_status"] == "approved"
    assert (
        reviewed_threshold_assertion["category_bindings"][0]["details"]["review_overlay"][
            "review_note"
        ]
        == "Confirmed category binding for governance."
    )

    reviewed_artifact = client.get(f"/documents/{document_id}/semantics/latest/artifacts/json")
    assert reviewed_artifact.status_code == 200
    reviewed_artifact_payload = reviewed_artifact.json()
    reviewed_artifact_threshold_assertion = next(
        assertion
        for assertion in reviewed_artifact_payload["assertions"]
        if assertion["concept_key"] == "integration_threshold"
    )
    assert reviewed_artifact_threshold_assertion["review_status"] == "approved"
    assert reviewed_artifact_threshold_assertion["category_bindings"][0]["review_status"] == (
        "approved"
    )

    reprocess_response = client.post(f"/documents/{document_id}/reprocess")
    assert reprocess_response.status_code == 202
    rerun_id = UUID(reprocess_response.json()["run_id"])
    assert rerun_id != original_run_id

    postgres_integration_harness.process_next_run(
        StubParser(_build_parsed_document(figure_caption="Overview illustration"))
    )

    latest_semantics = client.get(f"/documents/{document_id}/semantics/latest")
    assert latest_semantics.status_code == 200
    latest_payload = latest_semantics.json()
    assert latest_payload["run_id"] == str(rerun_id)
    assert latest_payload["baseline_run_id"] == str(original_run_id)
    assert latest_payload["baseline_semantic_pass_id"] is not None
    assert latest_payload["continuity_summary"]["has_baseline"] is True
    assert latest_payload["continuity_summary"]["removed_concept_keys"] == ["system_diagram"]
    assert latest_payload["continuity_summary"]["added_concept_keys"] == []
    assert latest_payload["continuity_summary"]["changed_assertion_review_statuses"] == []
    latest_threshold_assertion = next(
        assertion
        for assertion in latest_payload["assertions"]
        if assertion["concept_key"] == "integration_threshold"
    )
    assert latest_threshold_assertion["review_status"] == "approved"
    assert latest_threshold_assertion["category_bindings"][0]["review_status"] == "approved"
    assert latest_payload["evaluation_summary"]["all_expectations_passed"] is False

    continuity_response = client.get(f"/documents/{document_id}/semantics/latest/continuity")
    assert continuity_response.status_code == 200
    continuity = continuity_response.json()
    assert continuity["baseline_run_id"] == str(original_run_id)
    assert continuity["summary"]["removed_concept_keys"] == ["system_diagram"]
    assert continuity["summary"]["change_count"] == 1


def test_workspace_seed_snapshot_same_version_resync_does_not_self_parent(
    postgres_integration_harness,
    monkeypatch,
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        """registry_name: portable_upper_ontology
registry_version: portable-upper-ontology-v1
upper_ontology_version: portable-upper-ontology-v1
categories: []
concepts: []
relations:
  - relation_key: document_mentions_concept
    preferred_label: Document Mentions Concept
"""
    )
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    with postgres_integration_harness.session_factory() as session:
        ensure_workspace_semantic_registry(session)
        original_snapshot = get_active_semantic_ontology_snapshot(session)
        original_snapshot_id = original_snapshot.id
        assert original_snapshot.parent_snapshot_id is None
        original_sha256 = original_snapshot.sha256

    registry_path.write_text(
        """registry_name: portable_upper_ontology
registry_version: portable-upper-ontology-v1
upper_ontology_version: portable-upper-ontology-v1
categories: []
concepts:
  - concept_key: incident_response_latency
    preferred_label: Incident Response Latency
    scope_note: Time to respond to incidents.
    aliases:
      - response latency
relations:
  - relation_key: document_mentions_concept
    preferred_label: Document Mentions Concept
"""
    )
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    with postgres_integration_harness.session_factory() as session:
        ensure_workspace_semantic_registry(session)
        active_snapshot = get_active_semantic_ontology_snapshot(session)
        assert active_snapshot.id == original_snapshot_id
        assert active_snapshot.parent_snapshot_id is None
        assert active_snapshot.sha256 != original_sha256
        assert active_snapshot.payload_json["concepts"][0]["concept_key"] == (
            "incident_response_latency"
        )


def test_ontology_extension_snapshot_version_is_immutable(
    postgres_integration_harness,
    monkeypatch,
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        """registry_name: portable_upper_ontology
registry_version: portable-upper-ontology-v1
upper_ontology_version: portable-upper-ontology-v1
categories: []
concepts: []
relations:
  - relation_key: document_mentions_concept
    preferred_label: Document Mentions Concept
"""
    )
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    with postgres_integration_harness.session_factory() as session:
        ensure_workspace_semantic_registry(session)
        base_snapshot = get_active_semantic_ontology_snapshot(session)

        persist_semantic_ontology_snapshot(
            session,
            {
                "registry_name": "portable_upper_ontology",
                "registry_version": "portable-upper-ontology-v2",
                "upper_ontology_version": "portable-upper-ontology-v1",
                "categories": [],
                "concepts": [
                    {
                        "concept_key": "incident_response_latency",
                        "preferred_label": "Incident Response Latency",
                        "aliases": ["response latency"],
                    }
                ],
                "relations": [
                    {
                        "relation_key": "document_mentions_concept",
                        "preferred_label": "Document Mentions Concept",
                    }
                ],
            },
            source_kind=SemanticOntologySourceKind.ONTOLOGY_EXTENSION_APPLY.value,
            parent_snapshot_id=base_snapshot.id,
            activate=False,
        )

        with pytest.raises(ValueError, match="immutable"):
            persist_semantic_ontology_snapshot(
                session,
                {
                    "registry_name": "portable_upper_ontology",
                    "registry_version": "portable-upper-ontology-v2",
                    "upper_ontology_version": "portable-upper-ontology-v1",
                    "categories": [],
                    "concepts": [
                        {
                            "concept_key": "vendor_escalation_owner",
                            "preferred_label": "Vendor Escalation Owner",
                            "aliases": ["escalation owner"],
                        }
                    ],
                    "relations": [
                        {
                            "relation_key": "document_mentions_concept",
                            "preferred_label": "Document Mentions Concept",
                        }
                    ],
                },
                source_kind=SemanticOntologySourceKind.ONTOLOGY_EXTENSION_APPLY.value,
                parent_snapshot_id=base_snapshot.id,
                activate=False,
            )


def test_semantic_graph_snapshot_version_is_immutable(
    postgres_integration_harness,
    monkeypatch,
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
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
"""
    )
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    with postgres_integration_harness.session_factory() as session:
        ensure_workspace_semantic_registry(session)
        ontology_snapshot = get_active_semantic_ontology_snapshot(session)
        persist_semantic_graph_snapshot(
            session,
            {
                "graph_name": "workspace_semantic_graph",
                "graph_version": "portable-upper-ontology-v1.graph.1",
                "ontology_snapshot_id": str(ontology_snapshot.id),
                "nodes": [],
                "edges": [],
            },
            source_kind=SemanticGraphSourceKind.GRAPH_PROMOTION_APPLY.value,
            activate=False,
        )

        with pytest.raises(ValueError, match="immutable"):
            persist_semantic_graph_snapshot(
                session,
                {
                    "graph_name": "workspace_semantic_graph",
                    "graph_version": "portable-upper-ontology-v1.graph.1",
                    "ontology_snapshot_id": str(ontology_snapshot.id),
                    "nodes": [],
                    "edges": [
                        {
                            "edge_id": (
                                "graph_edge:concept_related_to_concept:"
                                "concept:incident_response_latency:"
                                "concept:vendor_escalation_owner"
                            ),
                            "relation_key": "concept_related_to_concept",
                        }
                    ],
                },
                source_kind=SemanticGraphSourceKind.GRAPH_PROMOTION_APPLY.value,
                activate=False,
            )


def test_semantic_reviews_survive_additive_registry_version_bump(
    postgres_integration_harness,
    monkeypatch,
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "config" / "semantic_registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        """registry_name: semantics_layer_foundation
registry_version: semantics-layer-foundation-alpha.2
categories:
  - category_key: integration_governance
    preferred_label: Integration Governance
    scope_note: Controls, thresholds, and governance mechanisms for integration decisions.
  - category_key: system_representation
    preferred_label: System Representation
    scope_note: Representations that communicate system structure, flow, or architecture.
concepts:
  - concept_key: integration_threshold
    preferred_label: Integration Threshold
    scope_note: Threshold guidance or threshold matrices used to govern integration decisions.
    category_keys:
      - integration_governance
    aliases:
      - integration threshold
      - threshold guidance
  - concept_key: system_diagram
    preferred_label: System Diagram
    scope_note: Figures or diagrams that communicate a system structure, flow, or arrangement.
    category_keys:
      - system_representation
    aliases:
      - system diagram
      - architecture diagram
"""
    )
    monkeypatch.setenv("DOCLING_SYSTEM_SEMANTIC_REGISTRY_PATH", str(registry_path))
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    client = postgres_integration_harness.client
    upload_files = {
        "file": (
            "integration-report.pdf",
            valid_test_pdf_bytes(),
            "application/pdf",
        )
    }

    create_response = client.post("/documents", files=upload_files)
    assert create_response.status_code == 202
    document_id = create_response.json()["document_id"]
    original_run_id = UUID(create_response.json()["run_id"])

    postgres_integration_harness.process_next_run(StubParser(_build_parsed_document()))

    first_semantics = client.get(f"/documents/{document_id}/semantics/latest")
    assert first_semantics.status_code == 200
    first_payload = first_semantics.json()
    threshold_assertion = next(
        assertion
        for assertion in first_payload["assertions"]
        if assertion["concept_key"] == "integration_threshold"
    )
    threshold_binding = threshold_assertion["category_bindings"][0]

    assertion_review_response = client.post(
        f"/documents/{document_id}/semantics/latest/assertions/{threshold_assertion['assertion_id']}/review",
        json={
            "review_status": "approved",
            "review_note": "Carry this approval across additive registry versions.",
            "reviewed_by": "semantic-operator",
        },
    )
    assert assertion_review_response.status_code == 200

    binding_review_response = client.post(
        f"/documents/{document_id}/semantics/latest/assertion-category-bindings/{threshold_binding['binding_id']}/review",
        json={
            "review_status": "approved",
            "review_note": "Carry this binding approval across additive registry versions.",
            "reviewed_by": "semantic-operator",
        },
    )
    assert binding_review_response.status_code == 200

    registry_path.write_text(
        """registry_name: semantics_layer_foundation
registry_version: semantics-layer-foundation-alpha.3
categories:
  - category_key: integration_governance
    preferred_label: Integration Governance
    scope_note: Controls, thresholds, and governance mechanisms for integration decisions.
  - category_key: system_representation
    preferred_label: System Representation
    scope_note: Representations that communicate system structure, flow, or architecture.
concepts:
  - concept_key: integration_threshold
    preferred_label: Integration Threshold
    scope_note: Threshold guidance or threshold matrices used to govern integration decisions.
    category_keys:
      - integration_governance
    aliases:
      - integration threshold
      - threshold guidance
      - integration control threshold
  - concept_key: system_diagram
    preferred_label: System Diagram
    scope_note: Figures or diagrams that communicate a system structure, flow, or arrangement.
    category_keys:
      - system_representation
    aliases:
      - system diagram
      - architecture diagram
"""
    )
    get_settings.cache_clear()
    clear_semantic_registry_cache()

    reprocess_response = client.post(f"/documents/{document_id}/reprocess")
    assert reprocess_response.status_code == 202
    rerun_id = UUID(reprocess_response.json()["run_id"])
    assert rerun_id != original_run_id

    postgres_integration_harness.process_next_run(StubParser(_build_parsed_document()))

    latest_semantics = client.get(f"/documents/{document_id}/semantics/latest")
    assert latest_semantics.status_code == 200
    latest_payload = latest_semantics.json()
    assert latest_payload["registry_version"] == "semantics-layer-foundation-alpha.3"
    latest_threshold_assertion = next(
        assertion
        for assertion in latest_payload["assertions"]
        if assertion["concept_key"] == "integration_threshold"
    )
    assert latest_threshold_assertion["review_status"] == "approved"
    assert latest_threshold_assertion["details"]["review_overlay"]["review_note"] == (
        "Carry this approval across additive registry versions."
    )
    assert latest_threshold_assertion["category_bindings"][0]["review_status"] == "approved"
    assert (
        latest_threshold_assertion["category_bindings"][0]["details"]["review_overlay"][
            "review_note"
        ]
        == "Carry this binding approval across additive registry versions."
    )


def test_failed_reprocess_does_not_replace_active_run(postgres_integration_harness) -> None:
    client = postgres_integration_harness.client
    upload_files = {
        "file": (
            "integration-report.pdf",
            valid_test_pdf_bytes(),
            "application/pdf",
        )
    }

    create_response = client.post(
        "/documents",
        files=upload_files,
    )
    assert create_response.status_code == 202
    document_id = create_response.json()["document_id"]
    original_run_id = UUID(create_response.json()["run_id"])

    postgres_integration_harness.process_next_run(StubParser(_build_parsed_document()))

    reprocess_response = client.post(f"/documents/{document_id}/reprocess")
    assert reprocess_response.status_code == 202
    failed_run_id = UUID(reprocess_response.json()["run_id"])
    assert failed_run_id != original_run_id

    postgres_integration_harness.process_next_run(StubParser(_build_parsed_document(title=None)))

    detail_response = client.get(f"/documents/{document_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["active_run_id"] == str(original_run_id)
    assert detail["latest_run_id"] == str(failed_run_id)
    assert detail["latest_validation_status"] == "failed"
    assert detail["latest_run_promoted"] is False
    assert detail["latest_error_message"] == "Validation failed."

    runs_response = client.get(f"/documents/{document_id}/runs")
    assert runs_response.status_code == 200
    runs = runs_response.json()
    failed_run = next(run for run in runs if run["run_id"] == str(failed_run_id))
    assert failed_run["status"] == "failed"
    assert failed_run["failure_stage"] == "validation"
    assert failed_run["has_failure_artifact"] is True
    assert failed_run["is_active_run"] is False

    failure_artifact_response = client.get(f"/runs/{failed_run_id}/failure-artifact")
    assert failure_artifact_response.status_code == 200
    failure_artifact = failure_artifact_response.json()
    assert failure_artifact["failure_stage"] == "validation"
    assert failure_artifact["error_message"] == "Validation failed."

    search_response = client.post(
        "/search",
        json={"query": "integration threshold", "mode": "keyword", "limit": 5},
    )
    assert search_response.status_code == 200
    assert search_response.json()
    assert all(result["run_id"] == str(original_run_id) for result in search_response.json())


def test_corrupted_artifact_during_validation_does_not_promote_run(
    monkeypatch,
    postgres_integration_harness,
) -> None:
    client = postgres_integration_harness.client
    upload_files = {
        "file": (
            "integration-report.pdf",
            valid_test_pdf_bytes(),
            "application/pdf",
        )
    }

    runs_module = __import__("app.services.runs", fromlist=["_mark_run_validating"])
    original_mark_run_validating = runs_module._mark_run_validating

    def corrupting_mark_run_validating(session, run) -> None:
        original_mark_run_validating(session, run)
        assert run.docling_json_path is not None
        Path(run.docling_json_path).write_text('{"corrupted": true}')

    monkeypatch.setattr("app.services.runs._mark_run_validating", corrupting_mark_run_validating)

    create_response = client.post("/documents", files=upload_files)
    assert create_response.status_code == 202
    document_id = create_response.json()["document_id"]
    run_id = UUID(create_response.json()["run_id"])

    processed_run_id = postgres_integration_harness.process_next_run(
        StubParser(_build_parsed_document())
    )
    assert processed_run_id == run_id

    detail_response = client.get(f"/documents/{document_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["active_run_id"] is None
    assert detail["latest_run_id"] == str(run_id)
    assert detail["latest_validation_status"] == "failed"
    assert detail["latest_run_promoted"] is False
    assert detail["latest_error_message"] == "Validation failed."

    runs_response = client.get(f"/documents/{document_id}/runs")
    assert runs_response.status_code == 200
    failed_run = next(run for run in runs_response.json() if run["run_id"] == str(run_id))
    assert failed_run["status"] == "failed"
    assert failed_run["failure_stage"] == "validation"

    failure_artifact_response = client.get(f"/runs/{run_id}/failure-artifact")
    assert failure_artifact_response.status_code == 200
    failure_artifact = failure_artifact_response.json()
    assert failure_artifact["failure_stage"] == "validation"
    assert failure_artifact["error_message"] == "Validation failed."


def test_terminal_parse_failure_reports_failed_validation_status(
    postgres_integration_harness,
) -> None:
    client = postgres_integration_harness.client
    upload_files = {
        "file": (
            "integration-report.pdf",
            valid_test_pdf_bytes(),
            "application/pdf",
        )
    }

    create_response = client.post("/documents", files=upload_files)
    assert create_response.status_code == 202
    document_id = create_response.json()["document_id"]
    run_id = UUID(create_response.json()["run_id"])

    processed_run_id = postgres_integration_harness.process_next_run(
        FailingParser(ValueError("parse exploded"))
    )
    assert processed_run_id == run_id

    detail_response = client.get(f"/documents/{document_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["active_run_id"] is None
    assert detail["latest_run_id"] == str(run_id)
    assert detail["latest_validation_status"] == "failed"
    assert detail["latest_run_promoted"] is False
    assert detail["latest_error_message"] == "parse exploded"

    runs_response = client.get(f"/documents/{document_id}/runs")
    assert runs_response.status_code == 200
    failed_run = next(run for run in runs_response.json() if run["run_id"] == str(run_id))
    assert failed_run["status"] == "failed"
    assert failed_run["failure_stage"] == "parse"
    assert failed_run["validation_status"] == "failed"

    failure_artifact_response = client.get(f"/runs/{run_id}/failure-artifact")
    assert failure_artifact_response.status_code == 200
    failure_artifact = failure_artifact_response.json()
    assert failure_artifact["failure_stage"] == "parse"
    assert failure_artifact["error_message"] == "parse exploded"
    assert failure_artifact["validation_status"] == "failed"

    quality_response = client.get("/quality/summary")
    assert quality_response.status_code == 200
    assert quality_response.json()["failed_run_count"] == 1
