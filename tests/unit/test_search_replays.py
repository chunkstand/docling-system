from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.search import SearchReplayQueryResponse, SearchReplayRunDetailResponse
from app.services.search_replays import (
    CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE,
    TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE,
    ReplayCase,
    _cross_document_prose_replay_case,
    _evaluate_case_passed,
    _feedback_cases,
    _finalize_replay_rank_metrics,
    _live_search_gap_cases,
    _technical_report_claim_feedback_cases,
    _to_replay_run_summary,
    compare_search_replay_runs,
    export_ranking_dataset,
)

_HASH = "a" * 64


def _timestamp() -> datetime:
    return datetime.now(UTC)


def _claim_feedback_metadata(
    *,
    learning_label: str,
    source_search_request_id=None,
) -> dict:
    return {
        "claim_feedback_id": str(uuid4()),
        "learning_label": learning_label,
        "feedback_payload_sha256": _HASH,
        "source_payload_sha256": _HASH,
        "source_search_request_ids": [str(source_search_request_id or uuid4())],
    }


def test_compare_search_replay_runs_reports_improvements(monkeypatch) -> None:
    baseline_id = uuid4()
    candidate_id = uuid4()
    shared_filters = {"document_id": str(uuid4())}

    baseline = SearchReplayRunDetailResponse(
        replay_run_id=baseline_id,
        source_type="feedback",
        status="completed",
        query_count=2,
        passed_count=0,
        failed_count=2,
        zero_result_count=1,
        table_hit_count=0,
        top_result_changes=0,
        max_rank_shift=0,
        created_at=_timestamp(),
        summary={},
        query_results=[
            SearchReplayQueryResponse(
                replay_query_id=uuid4(),
                query_text="vent stack",
                mode="hybrid",
                filters=shared_filters,
                passed=False,
                result_count=0,
                created_at=_timestamp(),
            )
        ],
    )
    candidate = SearchReplayRunDetailResponse(
        replay_run_id=candidate_id,
        source_type="feedback",
        status="completed",
        query_count=2,
        passed_count=1,
        failed_count=1,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        created_at=_timestamp(),
        summary={},
        query_results=[
            SearchReplayQueryResponse(
                replay_query_id=uuid4(),
                query_text="vent stack",
                mode="hybrid",
                filters=shared_filters,
                passed=True,
                result_count=2,
                created_at=_timestamp(),
            )
        ],
    )

    monkeypatch.setattr(
        "app.services.search_replays.get_search_replay_run_detail",
        lambda session, replay_run_id: baseline if replay_run_id == baseline_id else candidate,
    )

    response = compare_search_replay_runs(None, baseline_id, candidate_id)

    assert response.shared_query_count == 1
    assert response.improved_count == 1
    assert response.regressed_count == 0
    assert response.baseline_zero_result_count == 1
    assert response.candidate_zero_result_count == 0


def test_compare_search_replay_runs_keys_claim_feedback_by_feedback_id(monkeypatch) -> None:
    baseline_id = uuid4()
    candidate_id = uuid4()
    feedback_a_id = uuid4()
    feedback_b_id = uuid4()

    def query_row(feedback_id, *, passed: bool, result_count: int):
        return SearchReplayQueryResponse(
            replay_query_id=uuid4(),
            query_text="same generated claim",
            mode="hybrid",
            filters={},
            passed=passed,
            result_count=result_count,
            details={
                "source_reason": TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE,
                "claim_feedback_id": str(feedback_id),
            },
            created_at=_timestamp(),
        )

    baseline = SearchReplayRunDetailResponse(
        replay_run_id=baseline_id,
        source_type=TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE,
        status="completed",
        query_count=2,
        passed_count=1,
        failed_count=1,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        created_at=_timestamp(),
        summary={},
        query_results=[
            query_row(feedback_a_id, passed=False, result_count=1),
            query_row(feedback_b_id, passed=True, result_count=1),
        ],
    )
    candidate = SearchReplayRunDetailResponse(
        replay_run_id=candidate_id,
        source_type=TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE,
        status="completed",
        query_count=2,
        passed_count=1,
        failed_count=1,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        created_at=_timestamp(),
        summary={},
        query_results=[
            query_row(feedback_a_id, passed=True, result_count=1),
            query_row(feedback_b_id, passed=False, result_count=1),
        ],
    )

    monkeypatch.setattr(
        "app.services.search_replays.get_search_replay_run_detail",
        lambda session, replay_run_id: baseline if replay_run_id == baseline_id else candidate,
    )

    response = compare_search_replay_runs(None, baseline_id, candidate_id)

    assert response.shared_query_count == 2
    assert response.improved_count == 1
    assert response.regressed_count == 1


def test_export_ranking_dataset_includes_feedback_and_replay_rows() -> None:
    request_id = uuid4()
    feedback_id = uuid4()
    result_id = uuid4()
    replay_query_id = uuid4()
    replay_run_id = uuid4()

    feedback_rows = [
        SimpleNamespace(
            id=feedback_id,
            search_request_id=request_id,
            search_request_result_id=result_id,
            feedback_type="relevant",
            note="good hit",
            created_at=_timestamp(),
            result_rank=1,
        )
    ]
    replay_rows = [
        SimpleNamespace(
            id=replay_query_id,
            replay_run_id=replay_run_id,
            query_text="vent stack",
            mode="hybrid",
            filters_json={},
            expected_result_type="chunk",
            expected_top_n=3,
            passed=True,
            result_count=2,
            table_hit_count=0,
            overlap_count=1,
            added_count=0,
            removed_count=0,
            top_result_changed=False,
            max_rank_shift=0,
            details_json={"source_reason": "feedback_label"},
            created_at=_timestamp(),
        )
    ]

    class FakeScalarResult:
        def __init__(self, rows):
            self.rows = rows

        def scalars(self):
            return self

        def all(self):
            return self.rows

    class FakeSession:
        def execute(self, statement):
            entity_name = statement.column_descriptions[0]["entity"].__name__
            mapping = {
                "SearchFeedback": feedback_rows,
                "SearchReplayQuery": replay_rows,
            }
            return FakeScalarResult(mapping[entity_name])

        def get(self, model, key):
            if model.__name__ == "SearchRequestRecord" and key == request_id:
                return SimpleNamespace(
                    id=request_id,
                    query_text="vent stack",
                    mode="hybrid",
                    filters_json={},
                    harness_name="default_v1",
                    reranker_name="linear_feature_reranker",
                    reranker_version="v1",
                    retrieval_profile_name="default_v1",
                    harness_config_json={"harness_name": "default_v1"},
                )
            if model.__name__ == "SearchRequestResult" and key == result_id:
                return SimpleNamespace(
                    id=result_id,
                    result_type="chunk",
                    table_id=None,
                    chunk_id=uuid4(),
                    rerank_features_json={"base_score": 0.2},
                )
            if model.__name__ == "SearchReplayRun" and key == replay_run_id:
                return SimpleNamespace(
                    id=replay_run_id,
                    source_type="feedback",
                    harness_name="wide_v2",
                    reranker_name="linear_feature_reranker",
                    reranker_version="v2",
                    retrieval_profile_name="wide_v2",
                    harness_config_json={"harness_name": "wide_v2"},
                )
            return None

    rows = export_ranking_dataset(FakeSession(), limit=10)

    assert rows[0]["dataset_type"] == "feedback"
    assert rows[0]["row_schema_version"] == 2
    assert rows[0]["metadata_era"] == "harness_v1"
    assert rows[0]["feedback_type"] == "relevant"
    assert rows[1]["dataset_type"] == "replay"
    assert rows[1]["source_type"] == "feedback"
    assert rows[1]["reranker_version"] == "v2"
    assert rows[1]["metadata_era"] == "harness_v1"
    assert rows[1]["passed"] is True


def test_replay_run_summary_prefers_external_source_type_from_summary() -> None:
    row = SimpleNamespace(
        id=uuid4(),
        source_type="evaluation_queries",
        status="completed",
        harness_name="prose_v3",
        reranker_name="linear_feature_reranker",
        reranker_version="v3",
        retrieval_profile_name="prose_v3",
        harness_config_json={},
        query_count=2,
        passed_count=2,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=0,
        top_result_changes=0,
        max_rank_shift=0,
        created_at=_timestamp(),
        completed_at=_timestamp(),
        summary_json={"source_type": CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE},
    )

    summary = _to_replay_run_summary(row)

    assert summary.source_type == CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE


def test_cross_document_prose_answer_case_uses_fixture_expected_result_type() -> None:
    row = SimpleNamespace(
        id=uuid4(),
        query_text="What does Table 1 show in the transportation report?",
        mode="hybrid",
        filters_json={"document_id": str(uuid4())},
    )

    case = _cross_document_prose_replay_case(
        row,
        {
            "evaluation_kind": "answer",
            "expected_result_type": "table",
            "expected_citation_source_filename": "20251216_TK_TransportationReport.pdf",
        },
    )

    assert case is not None
    assert case.expected_result_type == "table"
    assert case.expected_source_filename == "20251216_TK_TransportationReport.pdf"


def test_replay_run_summary_uses_native_cross_document_source_type() -> None:
    row = SimpleNamespace(
        id=uuid4(),
        source_type=CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE,
        status="completed",
        harness_name="prose_v3",
        reranker_name="linear_feature_reranker",
        reranker_version="v3",
        retrieval_profile_name="prose_v3",
        harness_config_json={},
        query_count=2,
        passed_count=2,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=0,
        top_result_changes=0,
        max_rank_shift=0,
        created_at=_timestamp(),
        completed_at=_timestamp(),
        summary_json={},
    )

    summary = _to_replay_run_summary(row)

    assert summary.source_type == CROSS_DOCUMENT_PROSE_REGRESSIONS_SOURCE_TYPE


def test_evaluate_case_passed_enforces_source_purity_constraints() -> None:
    execution = SimpleNamespace(
        results=[
            SimpleNamespace(result_type="chunk", source_filename="wrong.pdf"),
            SimpleNamespace(result_type="chunk", source_filename="expected.pdf"),
        ],
        table_hit_count=0,
    )

    passed, details = _evaluate_case_passed(
        ReplayCase(
            query_text="main claim",
            mode="keyword",
            filters={},
            limit=10,
            evaluation_query_id=uuid4(),
            expected_result_type="chunk",
            expected_top_n=3,
            expected_source_filename="expected.pdf",
            expected_top_result_source_filename="expected.pdf",
            minimum_top_n_hits_from_expected_document=1,
            maximum_foreign_results_before_first_expected_hit=0,
        ),
        execution,
    )

    assert passed is False
    assert details["matching_rank"] == 2
    assert details["top_result_source_filename"] == "wrong.pdf"
    assert details["foreign_results_before_first_expected_hit"] == 1


def test_evaluate_case_passed_enforces_claim_feedback_labels() -> None:
    target_id = uuid4()
    execution = SimpleNamespace(
        results=[
            SimpleNamespace(result_type="chunk", chunk_id=target_id, table_id=None),
            SimpleNamespace(result_type="chunk", chunk_id=uuid4(), table_id=None),
        ],
        table_hit_count=0,
    )

    positive_passed, positive_details = _evaluate_case_passed(
        ReplayCase(
            query_text="claim",
            mode="hybrid",
            filters={},
            limit=10,
            expected_top_n=1,
            target_result_type="chunk",
            target_result_id=target_id,
            source_reason=TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE,
            source_metadata=_claim_feedback_metadata(learning_label="positive"),
        ),
        execution,
    )
    negative_passed, negative_details = _evaluate_case_passed(
        ReplayCase(
            query_text="claim",
            mode="hybrid",
            filters={},
            limit=10,
            expected_top_n=1,
            target_result_type="chunk",
            target_result_id=target_id,
            source_reason=TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE,
            source_metadata=_claim_feedback_metadata(learning_label="negative"),
        ),
        execution,
    )
    missing_passed, missing_details = _evaluate_case_passed(
        ReplayCase(
            query_text="claim",
            mode="hybrid",
            filters={},
            limit=10,
            source_reason=TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE,
            source_metadata=_claim_feedback_metadata(learning_label="missing"),
        ),
        SimpleNamespace(results=[], table_hit_count=0),
    )

    assert positive_passed is True
    assert positive_details["target_rank"] == 1
    assert positive_details["matching_rank"] == 1
    assert negative_passed is False
    assert negative_details["claim_feedback_replay_verdict"] == "negative_target_still_prominent"
    assert missing_passed is False
    assert missing_details["claim_feedback_replay_verdict"] == "missing_evidence_still_empty"


def test_evaluate_case_passed_handles_claim_feedback_weak_missing_and_traceability() -> None:
    target_id = uuid4()
    weak_execution = SimpleNamespace(
        results=[
            SimpleNamespace(result_type="chunk", chunk_id=uuid4(), table_id=None),
            SimpleNamespace(result_type="chunk", chunk_id=uuid4(), table_id=None),
            SimpleNamespace(result_type="chunk", chunk_id=target_id, table_id=None),
        ],
        table_hit_count=0,
    )

    weak_passed, weak_details = _evaluate_case_passed(
        ReplayCase(
            query_text="weak claim",
            mode="hybrid",
            filters={},
            limit=10,
            expected_top_n=3,
            target_result_type="chunk",
            target_result_id=target_id,
            source_reason=TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE,
            source_metadata=_claim_feedback_metadata(learning_label="positive"),
        ),
        weak_execution,
    )
    missing_passed, missing_details = _evaluate_case_passed(
        ReplayCase(
            query_text="missing claim",
            mode="hybrid",
            filters={},
            limit=10,
            source_reason=TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE,
            source_metadata=_claim_feedback_metadata(learning_label="missing"),
        ),
        SimpleNamespace(
            results=[SimpleNamespace(result_type="chunk", chunk_id=uuid4(), table_id=None)],
            table_hit_count=0,
        ),
    )
    dangling_passed, dangling_details = _evaluate_case_passed(
        ReplayCase(
            query_text="dangling negative",
            mode="hybrid",
            filters={},
            limit=10,
            expected_top_n=1,
            source_reason=TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE,
            source_metadata=_claim_feedback_metadata(learning_label="negative"),
        ),
        SimpleNamespace(results=[], table_hit_count=0),
    )

    assert weak_passed is True
    assert weak_details["target_rank"] == 3
    assert weak_details["claim_feedback_traceability_complete"] is True
    assert missing_passed is True
    assert missing_details["claim_feedback_replay_verdict"] == "missing_evidence_query_recovered"
    assert dangling_passed is False
    assert dangling_details["claim_feedback_replay_verdict"] == (
        "claim_feedback_traceability_incomplete"
    )
    assert "target_result_missing" in dangling_details["claim_feedback_traceability_issues"]


def test_technical_report_claim_feedback_cases_preserve_audit_metadata() -> None:
    feedback_id = uuid4()
    request_id = uuid4()
    result_id = uuid4()
    table_id = uuid4()
    span_id = uuid4()
    feedback = SimpleNamespace(
        id=feedback_id,
        technical_report_verification_task_id=uuid4(),
        claim_evidence_derivation_id=uuid4(),
        evidence_manifest_id=uuid4(),
        prov_export_artifact_id=uuid4(),
        release_readiness_db_gate_id=uuid4(),
        semantic_governance_event_id=uuid4(),
        claim_id="claim:weak",
        claim_text="The cited table only weakly supports this claim.",
        support_verdict="supported",
        support_score=0.42,
        feedback_status="weak",
        learning_label="positive",
        hard_negative_kind=None,
        source_search_request_id=request_id,
        search_request_result_id=result_id,
        source_search_request_ids_json=[str(request_id)],
        source_search_request_result_ids_json=[str(result_id)],
        search_request_result_span_ids_json=[str(span_id)],
        retrieval_evidence_span_ids_json=[],
        retrieval_context_json={
            "primary_query_text": "weakly supported generated claim",
            "primary_mode": "hybrid",
        },
        feedback_payload_sha256=_HASH,
        source_payload_sha256=_HASH,
    )
    result = SimpleNamespace(
        id=result_id,
        result_type="table",
        table_id=table_id,
        chunk_id=None,
        rank=2,
        source_filename="audit.pdf",
    )

    class FakeScalarResult:
        def __init__(self, rows):
            self.rows = rows

        def scalars(self):
            return self

        def all(self):
            return self.rows

    class FakeSession:
        def execute(self, _statement):
            return FakeScalarResult([feedback])

        def get(self, model, key):
            if model.__name__ == "SearchRequestRecord":
                return None
            if model.__name__ == "SearchRequestResult" and key == result_id:
                return result
            return None

    cases = _technical_report_claim_feedback_cases(FakeSession(), limit=5)

    assert len(cases) == 1
    assert cases[0].query_text == "weakly supported generated claim"
    assert cases[0].source_search_request_id == request_id
    assert cases[0].target_result_type == "table"
    assert cases[0].target_result_id == table_id
    assert cases[0].expected_top_n == 3
    assert cases[0].source_metadata["claim_feedback_id"] == str(feedback_id)
    assert cases[0].source_metadata["feedback_payload_sha256"] == _HASH
    assert cases[0].source_metadata["source_search_request_result_ids"] == [str(result_id)]
    assert cases[0].source_metadata["search_request_result_span_ids"] == [str(span_id)]
    assert cases[0].source_metadata["target_source_filename"] == "audit.pdf"


def test_finalize_replay_rank_metrics_computes_mrr() -> None:
    metrics = _finalize_replay_rank_metrics(
        {
            "query_count": 2,
            "reciprocal_rank_sum": 1.5,
            "foreign_top_result_count": 1,
            "source_constrained_query_count": 1,
        }
    )

    assert metrics["mrr"] == 0.75
    assert metrics["foreign_top_result_count"] == 1


def test_feedback_cases_skip_smoke_test_labels() -> None:
    smoke_request_id = uuid4()
    keep_request_id = uuid4()
    smoke_feedback_id = uuid4()
    keep_feedback_id = uuid4()

    feedback_rows = [
        SimpleNamespace(
            id=smoke_feedback_id,
            search_request_id=smoke_request_id,
            search_request_result_id=None,
            feedback_type="relevant",
            note="smoke test relevance",
            created_at=_timestamp(),
            result_rank=1,
        ),
        SimpleNamespace(
            id=keep_feedback_id,
            search_request_id=keep_request_id,
            search_request_result_id=None,
            feedback_type="missing_chunk",
            note="real issue",
            created_at=_timestamp(),
            result_rank=None,
        ),
    ]

    class FakeScalarResult:
        def __init__(self, rows):
            self.rows = rows

        def scalars(self):
            return self

        def all(self):
            return self.rows

    class FakeSession:
        def execute(self, statement):
            entity_name = statement.column_descriptions[0]["entity"].__name__
            if entity_name == "SearchFeedback":
                return FakeScalarResult(feedback_rows)
            raise AssertionError(f"unexpected entity {entity_name}")

        def get(self, model, key):
            if model.__name__ != "SearchRequestRecord":
                raise AssertionError(f"unexpected model {model.__name__}")
            if key == smoke_request_id:
                return SimpleNamespace(
                    id=smoke_request_id,
                    query_text="applicability",
                    mode="keyword",
                    filters_json={},
                    limit=5,
                )
            if key == keep_request_id:
                return SimpleNamespace(
                    id=keep_request_id,
                    query_text="vent stack",
                    mode="keyword",
                    filters_json={},
                    limit=5,
                )
            return None

    cases = _feedback_cases(FakeSession(), limit=10)

    assert [case.query_text for case in cases] == ["vent stack"]
    assert cases[0].feedback_type == "missing_chunk"


def test_live_search_gap_cases_skip_smoke_test_and_low_signal_zero_result_queries() -> None:
    smoke_request_id = uuid4()
    low_signal_request_id = uuid4()
    keep_request_id = uuid4()
    keep_table_gap_request_id = uuid4()

    request_rows = [
        SimpleNamespace(
            id=smoke_request_id,
            origin="api",
            query_text="docling",
            mode="keyword",
            filters_json={},
            limit=5,
            result_count=0,
            tabular_query=False,
            table_hit_count=0,
            created_at=_timestamp(),
        ),
        SimpleNamespace(
            id=low_signal_request_id,
            origin="api",
            query_text="zzzzzznotfound",
            mode="keyword",
            filters_json={},
            limit=5,
            result_count=0,
            tabular_query=False,
            table_hit_count=0,
            created_at=_timestamp(),
        ),
        SimpleNamespace(
            id=keep_request_id,
            origin="api",
            query_text="annual road maintenance costs",
            mode="keyword",
            filters_json={},
            limit=5,
            result_count=0,
            tabular_query=False,
            table_hit_count=0,
            created_at=_timestamp(),
        ),
        SimpleNamespace(
            id=keep_table_gap_request_id,
            origin="api",
            query_text="vent stack",
            mode="keyword",
            filters_json={},
            limit=5,
            result_count=4,
            tabular_query=True,
            table_hit_count=0,
            created_at=_timestamp(),
        ),
    ]
    feedback_rows = [
        SimpleNamespace(
            id=uuid4(),
            search_request_id=smoke_request_id,
            search_request_result_id=None,
            feedback_type="no_answer",
            note="smoke test no answer",
            created_at=_timestamp(),
            result_rank=None,
        )
    ]

    class FakeScalarResult:
        def __init__(self, rows):
            self.rows = rows

        def scalars(self):
            return self

        def all(self):
            return self.rows

    class FakeSession:
        def execute(self, statement):
            entity_name = statement.column_descriptions[0]["entity"].__name__
            if entity_name == "SearchRequestRecord":
                return FakeScalarResult(request_rows)
            if entity_name == "SearchFeedback":
                return FakeScalarResult(feedback_rows)
            raise AssertionError(f"unexpected entity {entity_name}")

    cases = _live_search_gap_cases(FakeSession(), limit=10)

    assert [(case.query_text, case.source_reason) for case in cases] == [
        ("annual road maintenance costs", "zero_result_gap"),
        ("vent stack", "missing_table_gap"),
    ]
