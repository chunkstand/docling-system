from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import app.services.evidence_claim_feedback as evidence_claim_feedback


def test_technical_report_claim_feedback_status_classifies_core_verdicts() -> None:
    assert evidence_claim_feedback._technical_report_claim_feedback_status(
        {"support_verdict": "supported", "support_score": 0.91}
    ) == ("supported", "positive", None)
    assert evidence_claim_feedback._technical_report_claim_feedback_status(
        {"support_verdict": "supported", "support_score": 0.2}
    ) == ("weak", "positive", None)
    assert evidence_claim_feedback._technical_report_claim_feedback_status(
        {"support_verdict": "insufficient_evidence"}
    ) == ("missing", "missing", "missing_expected")
    assert evidence_claim_feedback._technical_report_claim_feedback_status(
        {
            "support_verdict": "unsupported",
            "support_judgment": {
                "unsupported_reasons": ["evidence_contains_contradiction_cue"]
            },
        }
    ) == ("contradicted", "negative", "explicit_irrelevant")


def test_claim_feedback_retrieval_context_uses_primary_request_defaults() -> None:
    request_id = uuid4()
    table_id = uuid4()
    request_row = SimpleNamespace(
        id=request_id,
        origin="operator",
        query_text="forest plan standards",
        mode=None,
        filters_json=None,
        harness_name="table_harness",
        reranker_name="reranker-v1",
        reranker_version="1.0",
        retrieval_profile_name="default",
        harness_config_json=None,
        embedding_status="ready",
        candidate_count=3,
        result_count=1,
        table_hit_count=1,
        created_at=datetime(2026, 5, 15, 12, 0, tzinfo=UTC),
    )
    result_row = SimpleNamespace(
        id=uuid4(),
        search_request_id=request_id,
        rank=1,
        base_rank=1,
        result_type="table",
        document_id=uuid4(),
        run_id=uuid4(),
        chunk_id=None,
        table_id=table_id,
        score=0.92,
        keyword_score=0.17,
        semantic_score=0.88,
        hybrid_score=0.92,
        rerank_features_json=None,
        page_from=4,
        page_to=5,
        source_filename="forest-plan.pdf",
        label="Table 2",
        preview_text="Standard and guideline summary",
    )

    payload = evidence_claim_feedback._claim_feedback_retrieval_context(
        [request_row],
        [result_row],
    )

    assert payload["schema_name"] == "technical_report_claim_retrieval_context"
    assert payload["request_count"] == 1
    assert payload["result_count"] == 1
    assert payload["primary_mode"] == "hybrid"
    assert payload["primary_harness_name"] == "table_harness"
    assert payload["requests"][0]["filters"] == {}
    assert payload["results"][0]["table_id"] == str(table_id)
