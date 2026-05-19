from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import delete, select

from app.db.models import (
    DocumentFigure,
    DocumentTable,
    RetrievalEvidenceSpan,
    SearchRequestResultSpan,
)
from tests.integration.pdf_fixtures import valid_test_pdf_bytes
from tests.integration.postgres_roundtrip_support import (
    StubParser,
    _build_parsed_document,
    _configure_sample_semantics,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


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

    duplicate_response = client.post("/documents", files=upload_files)
    assert duplicate_response.status_code == 200
    duplicate_body = duplicate_response.json()
    assert duplicate_body["duplicate"] is True
    assert duplicate_body["active_run_id"] == str(run_id)
