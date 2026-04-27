from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models import (
    RetrievalHardNegative,
    RetrievalJudgment,
    RetrievalJudgmentSet,
    RetrievalTrainingRun,
    SearchFeedback,
    SearchReplayQuery,
    SearchReplayRun,
    SearchRequestRecord,
    SearchRequestResult,
    SearchRequestResultSpan,
    SemanticGovernanceEvent,
)
from app.services.retrieval_learning import materialize_retrieval_learning_dataset

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def _make_search_request(*, now: datetime) -> SearchRequestRecord:
    return SearchRequestRecord(
        id=uuid4(),
        parent_request_id=None,
        evaluation_id=None,
        run_id=None,
        origin="api",
        query_text="vent stack sizing",
        mode="hybrid",
        filters_json={},
        details_json={},
        limit=5,
        tabular_query=False,
        harness_name="default_v1",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="default_v1",
        harness_config_json={"harness_name": "default_v1"},
        embedding_status="ready",
        embedding_error=None,
        candidate_count=2,
        result_count=2,
        table_hit_count=1,
        duration_ms=3.0,
        created_at=now,
    )


def _make_result(
    *,
    request_id,
    rank: int,
    result_type: str,
    now: datetime,
) -> SearchRequestResult:
    source_id = uuid4()
    return SearchRequestResult(
        id=uuid4(),
        search_request_id=request_id,
        rank=rank,
        base_rank=rank,
        result_type=result_type,
        document_id=uuid4(),
        run_id=uuid4(),
        chunk_id=source_id if result_type == "chunk" else None,
        table_id=source_id if result_type == "table" else None,
        score=1.0 / rank,
        keyword_score=0.4,
        semantic_score=0.6,
        hybrid_score=0.5,
        rerank_features_json={"rank_feature": rank},
        page_from=rank,
        page_to=rank,
        source_filename="fixture.pdf",
        label=f"{result_type}-{rank}",
        preview_text=f"{result_type} result {rank}",
        created_at=now,
    )


def test_materialize_retrieval_learning_dataset_roundtrip(
    postgres_integration_harness,
) -> None:
    now = datetime.now(UTC)

    with postgres_integration_harness.session_factory() as session:
        search_request = _make_search_request(now=now)
        session.add(search_request)
        session.flush()

        chunk_result = _make_result(
            request_id=search_request.id,
            rank=1,
            result_type="chunk",
            now=now,
        )
        table_result = _make_result(
            request_id=search_request.id,
            rank=2,
            result_type="table",
            now=now,
        )
        session.add_all([chunk_result, table_result])
        session.flush()

        session.add(
            SearchRequestResultSpan(
                id=uuid4(),
                search_request_id=search_request.id,
                search_request_result_id=chunk_result.id,
                retrieval_evidence_span_id=None,
                span_rank=1,
                score_kind="keyword",
                score=0.4,
                source_type="chunk",
                source_id=chunk_result.chunk_id,
                span_index=0,
                page_from=1,
                page_to=1,
                text_excerpt="vent stack sizing evidence",
                content_sha256="chunk-content-sha",
                source_snapshot_sha256="chunk-snapshot-sha",
                metadata_json={"fixture": "retrieval-learning"},
                created_at=now,
            )
        )

        relevant_feedback = SearchFeedback(
            id=uuid4(),
            search_request_id=search_request.id,
            search_request_result_id=table_result.id,
            result_rank=2,
            feedback_type="relevant",
            note="good table",
            created_at=now,
        )
        irrelevant_feedback = SearchFeedback(
            id=uuid4(),
            search_request_id=search_request.id,
            search_request_result_id=chunk_result.id,
            result_rank=1,
            feedback_type="irrelevant",
            note="wrong section",
            created_at=now,
        )
        missing_table_feedback = SearchFeedback(
            id=uuid4(),
            search_request_id=search_request.id,
            search_request_result_id=None,
            result_rank=None,
            feedback_type="missing_table",
            note="need the sizing table",
            created_at=now,
        )
        session.add_all([relevant_feedback, irrelevant_feedback, missing_table_feedback])

        replay_run = SearchReplayRun(
            id=uuid4(),
            source_type="feedback",
            status="completed",
            harness_name="candidate_v2",
            reranker_name="linear_feature_reranker",
            reranker_version="v2",
            retrieval_profile_name="wide_v2",
            harness_config_json={"harness_name": "candidate_v2"},
            query_count=1,
            passed_count=0,
            failed_count=1,
            zero_result_count=0,
            table_hit_count=1,
            top_result_changes=1,
            max_rank_shift=1,
            summary_json={"source_type": "feedback"},
            error_message=None,
            created_at=now,
            completed_at=now,
        )
        session.add(replay_run)
        session.flush()
        replay_query = SearchReplayQuery(
            id=uuid4(),
            replay_run_id=replay_run.id,
            source_search_request_id=search_request.id,
            replay_search_request_id=search_request.id,
            feedback_id=missing_table_feedback.id,
            evaluation_query_id=None,
            query_text=search_request.query_text,
            mode=search_request.mode,
            filters_json={},
            expected_result_type="table",
            expected_top_n=1,
            passed=False,
            result_count=2,
            table_hit_count=1,
            overlap_count=1,
            added_count=1,
            removed_count=0,
            top_result_changed=True,
            max_rank_shift=1,
            details_json={"feedback_type": "missing_table", "source_reason": "feedback_label"},
            created_at=now,
        )
        session.add(replay_query)
        session.flush()

        response = materialize_retrieval_learning_dataset(
            session,
            limit=10,
            source_types=["feedback", "replay"],
            set_name="integration-retrieval-learning",
            created_by="integration",
        )
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        judgment_sets = session.execute(select(RetrievalJudgmentSet)).scalars().all()
        judgments = session.execute(select(RetrievalJudgment)).scalars().all()
        hard_negatives = session.execute(select(RetrievalHardNegative)).scalars().all()
        training_runs = session.execute(select(RetrievalTrainingRun)).scalars().all()
        governance_events = session.execute(select(SemanticGovernanceEvent)).scalars().all()

    assert len(judgment_sets) == 1
    assert len(training_runs) == 1
    assert response["summary"]["judgment_count"] == 4
    assert response["summary"]["positive_count"] == 1
    assert response["summary"]["negative_count"] == 2
    assert response["summary"]["missing_count"] == 1
    assert response["summary"]["hard_negative_count"] == 3
    assert {row.judgment_kind for row in judgments} == {"positive", "negative", "missing"}
    assert {row.hard_negative_kind for row in hard_negatives} >= {
        "explicit_irrelevant",
        "wrong_result_type",
    }
    assert any(row.evidence_refs_json for row in judgments if row.result_type == "chunk")
    assert training_runs[0].training_dataset_sha256 == response["training_dataset_sha256"]
    assert training_runs[0].semantic_governance_event_id == governance_events[0].id
    assert governance_events[0].event_kind == "retrieval_training_run_materialized"
    assert (
        governance_events[0].event_payload_json["retrieval_training_run"][
            "training_dataset_sha256"
        ]
        == response["training_dataset_sha256"]
    )
