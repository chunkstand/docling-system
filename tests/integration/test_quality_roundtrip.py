from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.db.models import (
    ChatAnswerFeedback,
    ChatAnswerRecord,
    Document,
    DocumentRun,
    DocumentRunEvaluation,
    DocumentRunEvaluationQuery,
    SearchFeedback,
    SearchReplayRun,
    SearchRequestRecord,
)


def _make_search_request(
    *,
    query_text: str,
    created_at: datetime,
    result_count: int,
    table_hit_count: int,
    filters_json: dict | None = None,
    origin: str = "api",
    mode: str = "keyword",
    tabular_query: bool = False,
) -> SearchRequestRecord:
    return SearchRequestRecord(
        id=uuid4(),
        parent_request_id=None,
        evaluation_id=None,
        run_id=None,
        origin=origin,
        query_text=query_text,
        mode=mode,
        filters_json=filters_json or {},
        details_json={},
        limit=5,
        tabular_query=tabular_query,
        harness_name="default_v1",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="default_v1",
        harness_config_json={},
        embedding_status="ready",
        embedding_error=None,
        candidate_count=10,
        result_count=result_count,
        table_hit_count=table_hit_count,
        duration_ms=5.0,
        created_at=created_at,
    )


def test_quality_eval_candidates_endpoint_considers_full_history(
    postgres_integration_harness,
) -> None:
    now = datetime.now(UTC)

    with postgres_integration_harness.session_factory() as session:
        document = Document(
            id=uuid4(),
            source_filename="quality-chapter.pdf",
            source_path="/tmp/quality-chapter.pdf",
            sha256=f"sha-{uuid4().hex}",
            mime_type="application/pdf",
            title="Quality Chapter",
            page_count=8,
            active_run_id=None,
            latest_run_id=None,
            created_at=now - timedelta(days=2),
            updated_at=now,
        )
        session.add(document)
        session.flush()

        run = DocumentRun(
            id=uuid4(),
            document_id=document.id,
            run_number=1,
            status="completed",
            attempts=1,
            locked_at=None,
            locked_by=None,
            last_heartbeat_at=None,
            next_attempt_at=None,
            error_message=None,
            failure_stage=None,
            failure_artifact_path=None,
            docling_json_path=None,
            yaml_path=None,
            chunk_count=1,
            table_count=1,
            figure_count=0,
            embedding_model="text-embedding-3-small",
            embedding_dim=1536,
            validation_status="passed",
            validation_results_json={},
            created_at=now - timedelta(days=2),
            started_at=now - timedelta(days=2),
            completed_at=now - timedelta(days=2) + timedelta(minutes=2),
        )
        session.add(run)
        session.flush()
        document.active_run_id = run.id
        document.latest_run_id = run.id

        evaluation = DocumentRunEvaluation(
            id=uuid4(),
            run_id=run.id,
            corpus_name="default",
            fixture_name="quality-fixture",
            eval_version=1,
            status="completed",
            summary_json={},
            error_message=None,
            created_at=now - timedelta(days=1),
            completed_at=now - timedelta(days=1) + timedelta(minutes=1),
        )
        session.add(evaluation)
        session.flush()

        for index in range(5):
            session.add(
                DocumentRunEvaluationQuery(
                    id=uuid4(),
                    evaluation_id=evaluation.id,
                    query_text="vent stack sizing",
                    mode="hybrid",
                    filters_json={"document_id": str(document.id)},
                    expected_result_type="table",
                    expected_top_n=3,
                    passed=False,
                    candidate_rank=None,
                    baseline_rank=None,
                    rank_delta=None,
                    candidate_score=None,
                    baseline_score=None,
                    candidate_result_type=None,
                    baseline_result_type=None,
                    candidate_label=None,
                    baseline_label=None,
                    details_json={"evaluation_kind": "retrieval"},
                    created_at=now - timedelta(hours=6) + timedelta(minutes=index),
                )
            )

        for index in range(150):
            session.add(
                _make_search_request(
                    query_text=f"noise candidate {index} extra words",
                    created_at=now - timedelta(minutes=150 - index),
                    result_count=0,
                    table_hit_count=0,
                )
            )

        session.commit()

    response = postgres_integration_harness.client.get("/quality/eval-candidates?limit=3")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert body[0]["candidate_type"] == "evaluation_failure"
    assert body[0]["query_text"] == "vent stack sizing"
    assert body[0]["occurrence_count"] == 5
    assert body[0]["source_filename"] == "quality-chapter.pdf"


def test_quality_trends_endpoint_aggregates_days_feedback_and_replays(
    postgres_integration_harness,
) -> None:
    now = datetime.now(UTC)

    with postgres_integration_harness.session_factory() as session:
        yesterday_request = _make_search_request(
            query_text="older request example",
            created_at=now - timedelta(days=1),
            result_count=0,
            table_hit_count=0,
            origin="chat",
            mode="hybrid",
        )
        today_request = _make_search_request(
            query_text="table request example",
            created_at=now,
            result_count=3,
            table_hit_count=1,
            origin="api",
            mode="hybrid",
            filters_json={"document_id": str(uuid4())},
            tabular_query=True,
        )
        session.add_all([yesterday_request, today_request])
        session.flush()

        answer = ChatAnswerRecord(
            id=uuid4(),
            search_request_id=today_request.id,
            document_id=None,
            question_text="What changed?",
            mode="hybrid",
            answer_text="A helpful answer.",
            model="gpt-4.1-mini",
            used_fallback=False,
            warning=None,
            citations_json=[],
            harness_name="default_v1",
            reranker_name="linear_feature_reranker",
            reranker_version="v1",
            retrieval_profile_name="default_v1",
            created_at=now,
        )
        session.add(answer)
        session.flush()

        session.add_all(
            [
                SearchFeedback(
                    id=uuid4(),
                    search_request_id=today_request.id,
                    search_request_result_id=None,
                    result_rank=None,
                    feedback_type="missing_table",
                    note=None,
                    created_at=now,
                ),
                SearchFeedback(
                    id=uuid4(),
                    search_request_id=yesterday_request.id,
                    search_request_result_id=None,
                    result_rank=None,
                    feedback_type="relevant",
                    note=None,
                    created_at=now - timedelta(days=1),
                ),
                ChatAnswerFeedback(
                    id=uuid4(),
                    chat_answer_id=answer.id,
                    feedback_type="helpful",
                    note=None,
                    created_at=now,
                ),
                SearchReplayRun(
                    id=uuid4(),
                    source_type="feedback",
                    status="completed",
                    harness_name="default_v1",
                    reranker_name="linear_feature_reranker",
                    reranker_version="v1",
                    retrieval_profile_name="default_v1",
                    harness_config_json={},
                    query_count=3,
                    passed_count=2,
                    failed_count=1,
                    zero_result_count=1,
                    table_hit_count=1,
                    top_result_changes=1,
                    max_rank_shift=2,
                    summary_json={},
                    error_message=None,
                    created_at=now,
                    completed_at=now + timedelta(minutes=1),
                ),
            ]
        )
        session.commit()

    response = postgres_integration_harness.client.get("/quality/trends")

    assert response.status_code == 200
    body = response.json()
    search_days = {entry["bucket_date"]: entry for entry in body["search_request_days"]}
    assert search_days[(now - timedelta(days=1)).date().isoformat()]["request_count"] == 1
    assert search_days[(now - timedelta(days=1)).date().isoformat()]["zero_result_count"] == 1
    assert search_days[now.date().isoformat()]["request_count"] == 1
    assert search_days[now.date().isoformat()]["table_hit_rate"] == 1.0
    assert body["feedback_counts"][0] == {"feedback_type": "missing_table", "count": 1}
    assert body["answer_feedback_counts"][0] == {"feedback_type": "helpful", "count": 1}
    assert body["recent_replay_runs"][0]["source_type"] == "feedback"
