from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.db.models import (
    Document,
    DocumentRun,
    DocumentRunEvaluation,
    DocumentRunEvaluationQuery,
    SearchFeedback,
    SearchRequestRecord,
)
from app.services.search_replays import (
    _feedback_cases,
    _latest_evaluation_queries,
    _live_search_gap_cases,
)


def _make_search_request(
    *,
    query_text: str,
    created_at: datetime,
    result_count: int,
    table_hit_count: int,
    origin: str = "api",
    mode: str = "keyword",
) -> SearchRequestRecord:
    return SearchRequestRecord(
        id=uuid4(),
        parent_request_id=None,
        evaluation_id=None,
        run_id=None,
        origin=origin,
        query_text=query_text,
        mode=mode,
        filters_json={},
        details_json={},
        limit=5,
        tabular_query=False,
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


def _make_document_run(
    session,
    *,
    name: str,
    now: datetime,
    updated_at: datetime,
) -> tuple[Document, DocumentRun]:
    document = Document(
        id=uuid4(),
        source_filename=f"{name}.pdf",
        source_path=f"/tmp/{name}.pdf",
        sha256=f"sha-{uuid4().hex}",
        mime_type="application/pdf",
        title=name.title(),
        page_count=3,
        active_run_id=None,
        latest_run_id=None,
        created_at=now - timedelta(days=2),
        updated_at=updated_at,
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
        completed_at=now - timedelta(days=2) + timedelta(minutes=1),
    )
    session.add(run)
    session.flush()
    document.active_run_id = run.id
    document.latest_run_id = run.id
    return document, run


def test_live_search_gap_cases_skip_smoke_test_history_in_postgres(
    postgres_integration_harness,
) -> None:
    now = datetime.now(UTC)

    with postgres_integration_harness.session_factory() as session:
        real_request = _make_search_request(
            query_text="annual road maintenance costs",
            created_at=now - timedelta(hours=6),
            result_count=0,
            table_hit_count=0,
        )
        session.add(real_request)
        session.flush()
        real_request_id = real_request.id

        for index in range(150):
            smoke_request = _make_search_request(
                query_text=f"smoke gap {index} extra words",
                created_at=now - timedelta(minutes=150 - index),
                result_count=0,
                table_hit_count=0,
            )
            session.add(smoke_request)
            session.flush()
            session.add(
                SearchFeedback(
                    id=uuid4(),
                    search_request_id=smoke_request.id,
                    search_request_result_id=None,
                    result_rank=None,
                    feedback_type="no_answer",
                    note="smoke test no answer",
                    created_at=smoke_request.created_at,
                )
            )

        session.commit()

    with postgres_integration_harness.session_factory() as session:
        cases = _live_search_gap_cases(session, limit=1)

    assert len(cases) == 1
    assert cases[0].query_text == "annual road maintenance costs"
    assert cases[0].source_reason == "zero_result_gap"
    assert cases[0].source_search_request_id == real_request_id


def test_feedback_cases_skip_smoke_test_history_in_postgres(postgres_integration_harness) -> None:
    now = datetime.now(UTC)

    with postgres_integration_harness.session_factory() as session:
        real_request = _make_search_request(
            query_text="vent stack sizing",
            created_at=now - timedelta(hours=6),
            result_count=2,
            table_hit_count=1,
        )
        session.add(real_request)
        session.flush()
        real_feedback = SearchFeedback(
            id=uuid4(),
            search_request_id=real_request.id,
            search_request_result_id=None,
            result_rank=None,
            feedback_type="missing_chunk",
            note="real issue",
            created_at=real_request.created_at,
        )
        session.add(real_feedback)
        real_feedback_id = real_feedback.id

        for index in range(150):
            smoke_request = _make_search_request(
                query_text=f"smoke feedback {index} extra words",
                created_at=now - timedelta(minutes=150 - index),
                result_count=1,
                table_hit_count=0,
            )
            session.add(smoke_request)
            session.flush()
            session.add(
                SearchFeedback(
                    id=uuid4(),
                    search_request_id=smoke_request.id,
                    search_request_result_id=None,
                    result_rank=None,
                    feedback_type="relevant",
                    note="smoke test relevance",
                    created_at=smoke_request.created_at,
                )
            )

        session.commit()

    with postgres_integration_harness.session_factory() as session:
        cases = _feedback_cases(session, limit=1)

    assert len(cases) == 1
    assert cases[0].query_text == "vent stack sizing"
    assert cases[0].feedback_type == "missing_chunk"
    assert cases[0].feedback_id == real_feedback_id


def test_latest_evaluation_queries_use_latest_eval_and_document_order(
    postgres_integration_harness,
) -> None:
    now = datetime.now(UTC)

    with postgres_integration_harness.session_factory() as session:
        newer_document, newer_run = _make_document_run(
            session,
            name="newer-doc",
            now=now,
            updated_at=now,
        )
        older_document, older_run = _make_document_run(
            session,
            name="older-doc",
            now=now,
            updated_at=now - timedelta(days=1),
        )

        older_eval = DocumentRunEvaluation(
            id=uuid4(),
            run_id=newer_run.id,
            corpus_name="default",
            fixture_name="older-fixture",
            eval_version=1,
            status="completed",
            summary_json={},
            error_message=None,
            created_at=now - timedelta(hours=4),
            completed_at=now - timedelta(hours=4) + timedelta(minutes=1),
        )
        newer_eval = DocumentRunEvaluation(
            id=uuid4(),
            run_id=newer_run.id,
            corpus_name="default",
            fixture_name="newer-fixture",
            eval_version=2,
            status="completed",
            summary_json={},
            error_message=None,
            created_at=now - timedelta(hours=1),
            completed_at=now - timedelta(hours=1) + timedelta(minutes=1),
        )
        older_doc_eval = DocumentRunEvaluation(
            id=uuid4(),
            run_id=older_run.id,
            corpus_name="default",
            fixture_name="older-doc-fixture",
            eval_version=1,
            status="completed",
            summary_json={},
            error_message=None,
            created_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=2) + timedelta(minutes=1),
        )
        session.add_all([older_eval, newer_eval, older_doc_eval])
        session.flush()

        session.add_all(
            [
                DocumentRunEvaluationQuery(
                    id=uuid4(),
                    evaluation_id=older_eval.id,
                    query_text="stale query",
                    mode="hybrid",
                    filters_json={"document_id": str(newer_document.id)},
                    expected_result_type="chunk",
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
                    created_at=older_eval.created_at,
                ),
                DocumentRunEvaluationQuery(
                    id=uuid4(),
                    evaluation_id=newer_eval.id,
                    query_text="fresh retrieval query",
                    mode="hybrid",
                    filters_json={"document_id": str(newer_document.id)},
                    expected_result_type="chunk",
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
                    created_at=newer_eval.created_at,
                ),
                DocumentRunEvaluationQuery(
                    id=uuid4(),
                    evaluation_id=newer_eval.id,
                    query_text="fresh answer query",
                    mode="hybrid",
                    filters_json={"document_id": str(newer_document.id)},
                    expected_result_type="chunk",
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
                    details_json={"evaluation_kind": "answer"},
                    created_at=newer_eval.created_at + timedelta(seconds=1),
                ),
                DocumentRunEvaluationQuery(
                    id=uuid4(),
                    evaluation_id=older_doc_eval.id,
                    query_text="older document query",
                    mode="keyword",
                    filters_json={"document_id": str(older_document.id)},
                    expected_result_type="chunk",
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
                    created_at=older_doc_eval.created_at,
                ),
            ]
        )
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        cases = _latest_evaluation_queries(session, limit=2)

    assert [case.query_text for case in cases] == [
        "fresh retrieval query",
        "older document query",
    ]
