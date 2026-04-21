from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.search import (
    SearchLoggedResultResponse,
    SearchRequestDetailResponse,
    SearchScores,
)
from app.services.search_legibility import (
    get_search_harness_descriptor,
    get_search_request_explanation,
)


def _detail_payload(**overrides) -> SearchRequestDetailResponse:
    document_id = uuid4()
    run_id = uuid4()
    payload = {
        "search_request_id": uuid4(),
        "parent_search_request_id": None,
        "evaluation_id": None,
        "run_id": run_id,
        "origin": "api",
        "query": "integration table",
        "mode": "hybrid",
        "filters": {},
        "details": {
            "requested_mode": "hybrid",
            "served_mode": "hybrid",
            "query_intent": "tabular",
            "keyword_candidate_count": 4,
            "keyword_strict_candidate_count": 2,
            "semantic_candidate_count": 3,
            "metadata_candidate_count": 0,
            "context_expansion_count": 0,
            "candidate_source_breakdown": {"keyword": 4, "semantic": 3},
        },
        "limit": 8,
        "tabular_query": True,
        "harness_name": "default_v1",
        "reranker_name": "linear_feature_reranker",
        "reranker_version": "v1",
        "retrieval_profile_name": "default_v1",
        "harness_config": {"harness_name": "default_v1"},
        "embedding_status": "completed",
        "embedding_error": None,
        "candidate_count": 7,
        "result_count": 1,
        "table_hit_count": 1,
        "duration_ms": 12.5,
        "created_at": datetime.now(UTC),
        "feedback": [],
        "results": [
            SearchLoggedResultResponse(
                rank=1,
                base_rank=2,
                rerank_features={"tabular_table_bonus": 0.05},
                result_type="table",
                document_id=document_id,
                run_id=run_id,
                score=0.91,
                table_id=uuid4(),
                table_title="Integration Table",
                page_from=1,
                page_to=1,
                source_filename="report.pdf",
                scores=SearchScores(keyword_score=0.5, semantic_score=0.7, hybrid_score=0.9),
            )
        ],
    }
    payload.update(overrides)
    return SearchRequestDetailResponse.model_validate(payload)


def test_search_request_explanation_classifies_fallback(monkeypatch) -> None:
    detail = _detail_payload(
        details={
            "requested_mode": "hybrid",
            "served_mode": "keyword",
            "fallback_reason": "embedding_provider_unavailable",
            "keyword_candidate_count": 4,
            "semantic_candidate_count": 0,
        },
        embedding_status="unavailable",
    )
    monkeypatch.setattr(
        "app.services.search_legibility.get_search_request_detail",
        lambda session, search_request_id: detail,
    )

    explanation = get_search_request_explanation(object(), detail.search_request_id)

    assert explanation.schema_name == "search_request_explanation"
    assert explanation.diagnosis.category == "fallback_only"
    assert explanation.fallback_reason == "embedding_provider_unavailable"
    assert explanation.recommended_next_action.startswith("Inspect embedding availability")


def test_search_request_explanation_classifies_table_recall_gap(monkeypatch) -> None:
    detail = _detail_payload(table_hit_count=0, result_count=1, candidate_count=4, results=[])
    monkeypatch.setattr(
        "app.services.search_legibility.get_search_request_detail",
        lambda session, search_request_id: detail,
    )

    explanation = get_search_request_explanation(object(), detail.search_request_id)

    assert explanation.diagnosis.category == "table_recall_gap"
    assert explanation.query_understanding["query_intent"] == "tabular"
    assert explanation.top_result_snapshot == []


def test_search_request_explanation_classifies_healthy(monkeypatch) -> None:
    detail = _detail_payload()
    monkeypatch.setattr(
        "app.services.search_legibility.get_search_request_detail",
        lambda session, search_request_id: detail,
    )

    explanation = get_search_request_explanation(object(), detail.search_request_id)

    assert explanation.diagnosis.category == "healthy"
    assert explanation.top_result_snapshot[0].result_type == "table"
    assert explanation.evidence_refs[0]["ref_kind"] == "search_request"


def test_search_harness_descriptor_is_self_describing() -> None:
    descriptor = get_search_harness_descriptor("default_v1")

    assert descriptor.schema_name == "search_harness_descriptor"
    assert descriptor.harness_name == "default_v1"
    assert descriptor.is_default is True
    assert "keyword_candidate_multiplier" in descriptor.tunable_knobs["retrieval_profile_overrides"]
    assert descriptor.config_fingerprint
