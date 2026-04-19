from __future__ import annotations

import json
import os
from uuid import UUID

import pytest

from app.services.docling_parser import (
    ParsedChunk,
    ParsedDocument,
    ParsedFigure,
    ParsedTable,
    ParsedTableSegment,
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


def _build_parsed_document(*, title: str | None = "Integration Report") -> ParsedDocument:
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
        caption="Integration system diagram",
        heading="Section 1",
        page_from=1,
        page_to=1,
        confidence=0.99,
        metadata={
            "caption_resolution_source": "explicit_ref",
            "caption_candidates": ["Integration system diagram"],
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


def test_upload_process_search_and_evaluate_document_roundtrip(
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

    search_response = client.post(
        "/search",
        json={"query": "integration threshold", "mode": "keyword", "limit": 5},
    )
    assert search_response.status_code == 200
    assert search_response.headers["X-Search-Request-Id"]
    results = search_response.json()
    assert {"chunk", "table"}.issubset({result["result_type"] for result in results})
    assert all(result["run_id"] == str(run_id) for result in results)

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
    assert semantics["registry_version"] == "semantics-layer-foundation-alpha.1"
    assert semantics["artifact_schema_version"] == "1.0"
    assert semantics["evaluation_status"] == "completed"
    assert semantics["evaluation_summary"]["all_expectations_passed"] is True
    assert semantics["assertion_count"] == 2
    assertions_by_concept = {
        assertion["concept_key"]: assertion for assertion in semantics["assertions"]
    }
    assert sorted(assertions_by_concept["integration_threshold"]["source_types"]) == [
        "chunk",
        "table",
    ]
    assert assertions_by_concept["system_diagram"]["source_types"] == ["figure"]
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
    assert (
        client.get(f"/documents/{document_id}/tables/{table_id}/artifacts/json").status_code == 200
    )
    assert (
        client.get(f"/documents/{document_id}/tables/{table_id}/artifacts/yaml").status_code == 200
    )
    assert (
        client.get(f"/documents/{document_id}/figures/{figure_id}/artifacts/json").status_code
        == 200
    )
    assert (
        client.get(f"/documents/{document_id}/figures/{figure_id}/artifacts/yaml").status_code
        == 200
    )
    semantic_artifact_response = client.get(f"/documents/{document_id}/semantics/latest/artifacts/json")
    assert semantic_artifact_response.status_code == 200
    semantic_artifact = semantic_artifact_response.json()
    assert semantic_artifact["schema_name"] == "docling.semantic_pass"
    assert semantic_artifact["schema_version"] == "1.0"
    assert semantic_artifact["registry"]["version"] == "semantics-layer-foundation-alpha.1"
    assert semantic_artifact["evaluation"]["summary"]["all_expectations_passed"] is True
    artifact_threshold_table_evidence = next(
        evidence
        for assertion in semantic_artifact["assertions"]
        if assertion["concept_key"] == "integration_threshold"
        for evidence in assertion["evidence"]
        if evidence["source_type"] == "table"
    )
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
