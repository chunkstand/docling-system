from __future__ import annotations

import os
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.db.models import (
    DocumentRun,
    RetrievalEvidenceSpanMultiVector,
    SearchRequestResultSpan,
)
from app.services.retrieval_spans import rebuild_retrieval_evidence_spans
from tests.integration.pdf_fixtures import valid_test_pdf_bytes
from tests.integration.test_postgres_roundtrip import StubParser, _build_parsed_document

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


class DeterministicMultiVectorProvider:
    model = "deterministic-multivector-test"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    @staticmethod
    def _embed(text: str) -> list[float]:
        normalized = text.lower()
        vector = [0.0] * 1536
        if "integration" in normalized:
            vector[0] = 1.0
        if "threshold" in normalized:
            vector[1] = 1.0
        if len(normalized.split()) > 16:
            vector[2] = 1.0
        if not any(vector):
            vector[3] = 1.0
        return vector


def test_multivector_harness_persists_late_interaction_trace(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    provider = DeterministicMultiVectorProvider()
    parsed = _build_parsed_document()
    parsed.chunks[0].text = (
        "integration threshold "
        + " ".join(f"supporting context {index}" for index in range(20))
    )

    create_response = postgres_integration_harness.client.post(
        "/documents",
        files={
            "file": (
                "multivector-report.pdf",
                valid_test_pdf_bytes(),
                "application/pdf",
            )
        },
    )
    assert create_response.status_code == 202
    run_id = UUID(create_response.json()["run_id"])
    processed_run_id = postgres_integration_harness.process_next_run(StubParser(parsed))
    assert processed_run_id == run_id

    with postgres_integration_harness.session_factory() as session:
        run = session.get(DocumentRun, run_id)
        assert run is not None
        summary = rebuild_retrieval_evidence_spans(
            session,
            run,
            embedding_provider=provider,
        )
        session.commit()

    multivector_summary = summary["multivector_summary"]
    assert multivector_summary["embedding_status"] == "completed"
    assert multivector_summary["multivector_count"] >= 1

    monkeypatch.setattr("app.services.search.get_embedding_provider", lambda: provider)
    response = postgres_integration_harness.client.post(
        "/search",
        json={
            "query": "integration threshold",
            "mode": "hybrid",
            "limit": 5,
            "harness_name": "multivector_v1",
        },
    )
    assert response.status_code == 200
    search_request_id = UUID(response.headers["X-Search-Request-Id"])
    results = response.json()
    late_spans = [
        span
        for result in results
        for span in result["evidence_spans"]
        if span["score_kind"] == "late_interaction_maxsim"
    ]
    assert late_spans
    late_trace = late_spans[0]["metadata"]["late_interaction"]
    assert late_trace["score_policy"] == "average_query_window_max_similarity"
    assert late_trace["query_vector_count"] >= 1
    assert late_trace["maxsim_matches"][0]["span_vector_id"]

    detail_response = postgres_integration_harness.client.get(
        f"/search/requests/{search_request_id}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["harness_name"] == "multivector_v1"
    assert detail["details"]["late_interaction"]["status"] == "completed"
    assert detail["details"]["late_interaction_candidate_count"] >= 1

    with postgres_integration_harness.session_factory() as session:
        stored_vector_count = session.scalar(
            select(func.count())
            .select_from(RetrievalEvidenceSpanMultiVector)
            .where(RetrievalEvidenceSpanMultiVector.run_id == run_id)
        )
        stored_vector_hash = session.scalar(
            select(RetrievalEvidenceSpanMultiVector.embedding_sha256)
            .where(RetrievalEvidenceSpanMultiVector.run_id == run_id)
            .limit(1)
        )
        stored_trace_span = session.scalar(
            select(SearchRequestResultSpan)
            .where(SearchRequestResultSpan.search_request_id == search_request_id)
            .where(SearchRequestResultSpan.score_kind == "late_interaction_maxsim")
            .limit(1)
        )

    assert stored_vector_count and stored_vector_count >= 1
    assert stored_vector_hash
    assert stored_trace_span is not None
    assert stored_trace_span.metadata_json["late_interaction"]["maxsim_matches"]

    evidence_response = postgres_integration_harness.client.get(
        f"/search/requests/{search_request_id}/evidence-package"
    )
    assert evidence_response.status_code == 200
    evidence_package = evidence_response.json()
    assert evidence_package["audit_checklist"]["late_interaction_trace_count"] >= 1
    assert (
        evidence_package["audit_checklist"]["all_late_interaction_vectors_materialized"]
        is True
    )
    assert evidence_package["audit_checklist"]["all_late_interaction_vectors_hashed"] is True
    evidence_late_spans = [
        span
        for item in evidence_package["source_evidence"]
        for span in item["retrieval_evidence_spans"]
        if span["score_kind"] == "late_interaction_maxsim"
    ]
    assert evidence_late_spans
    evidence_vector = evidence_late_spans[0]["late_interaction_multivectors"][0]
    assert evidence_vector["embedding_sha256"] == stored_vector_hash
    assert evidence_vector["span_vector_snapshot_sha256"]
