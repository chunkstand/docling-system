from __future__ import annotations

import os
from uuid import UUID

import pytest
from sqlalchemy import select

from app.db.models import KnowledgeOperatorRun
from tests.integration.pdf_fixtures import valid_test_pdf_bytes
from tests.integration.test_postgres_roundtrip import StubParser, _build_parsed_document

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_search_evidence_operator_runs_roundtrip(postgres_integration_harness):
    client = postgres_integration_harness.client
    create_response = client.post(
        "/documents",
        files={
            "file": (
                "evidence-ledger.pdf",
                valid_test_pdf_bytes(),
                "application/pdf",
            )
        },
    )
    assert create_response.status_code == 202
    run_id = UUID(create_response.json()["run_id"])
    processed_run_id = postgres_integration_harness.process_next_run(
        StubParser(_build_parsed_document())
    )
    assert processed_run_id == run_id

    search_response = client.post(
        "/search",
        json={"query": "integration threshold", "mode": "keyword", "limit": 5},
    )
    assert search_response.status_code == 200
    search_request_id = UUID(search_response.headers["X-Search-Request-Id"])

    package_response = client.get(f"/search/requests/{search_request_id}/evidence-package")
    assert package_response.status_code == 200
    package = package_response.json()

    assert package["schema_name"] == "search_evidence_package"
    assert package["audit_checklist"]["has_retrieve_run"] is True
    assert package["audit_checklist"]["has_rerank_run"] is True
    assert package["audit_checklist"]["has_judge_run"] is True
    assert package["audit_checklist"]["result_count_matches"] is True
    assert package["audit_checklist"]["has_source_snapshots"] is True
    assert package["audit_checklist"]["all_results_have_source_snapshot"] is True
    assert package["audit_checklist"]["all_results_have_source_record"] is True
    assert package["audit_checklist"]["all_results_reference_active_run"] is True
    assert package["audit_checklist"]["all_result_runs_validation_passed"] is True
    assert package["audit_checklist"]["all_source_snapshots_hashed"] is True
    assert package["package_sha256"]
    assert [row["operator_kind"] for row in package["operator_runs"]] == [
        "retrieve",
        "rerank",
        "judge",
    ]
    assert package["operator_runs"][0]["outputs"][0]["output_kind"] == "candidate_set"
    assert package["operator_runs"][1]["config_sha256"]
    assert package["operator_runs"][2]["outputs"][0]["output_kind"] == "selected_evidence"
    assert package["operator_runs"][2]["outputs"][0]["payload"]["preview_text"]
    assert package["results"][0]["search_request_result_id"]
    assert package["results"][0]["source_snapshot_sha256"]
    assert package["results"][0]["preview_text"]
    assert len(package["source_evidence"]) == package["search_request"]["result_count"]

    table_snapshot = next(
        row for row in package["source_evidence"] if row["result_type"] == "table"
    )
    assert table_snapshot["document"]["sha256"]
    assert table_snapshot["run"]["validation_status"] == "passed"
    segment_metadata = table_snapshot["table"]["segments"][0]["metadata"]
    assert segment_metadata["source_artifact_sha256"] == "segment-sha"

    chunk_snapshot = next(
        row for row in package["source_evidence"] if row["result_type"] == "chunk"
    )
    assert chunk_snapshot["chunk"]["text_sha256"]

    with postgres_integration_harness.session_factory() as session:
        rows = list(
            session.scalars(
                select(KnowledgeOperatorRun)
                .where(KnowledgeOperatorRun.search_request_id == search_request_id)
                .order_by(KnowledgeOperatorRun.created_at.asc())
            )
        )
        assert [row.operator_kind for row in rows] == ["retrieve", "rerank", "judge"]
