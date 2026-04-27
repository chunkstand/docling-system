from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.db.models import (
    SearchHarnessEvaluation,
    SearchHarnessEvaluationSource,
    SearchReplayRun,
)


def _replay_run(*, replay_run_id, harness_name: str) -> SearchReplayRun:
    now = datetime.now(UTC)
    return SearchReplayRun(
        id=replay_run_id,
        source_type="evaluation_queries",
        status="completed",
        harness_name=harness_name,
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name=harness_name,
        harness_config_json={},
        query_count=4,
        passed_count=4,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        summary_json={"rank_metrics": {"mrr": 1.0, "foreign_top_result_count": 0}},
        error_message=None,
        created_at=now,
        completed_at=now + timedelta(seconds=1),
    )


def test_search_harness_release_gate_roundtrip(postgres_integration_harness) -> None:
    now = datetime.now(UTC)
    evaluation_id = uuid4()
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()

    with postgres_integration_harness.session_factory() as session:
        session.add_all(
            [
                _replay_run(
                    replay_run_id=baseline_replay_run_id,
                    harness_name="default_v1",
                ),
                _replay_run(
                    replay_run_id=candidate_replay_run_id,
                    harness_name="wide_v2",
                ),
                SearchHarnessEvaluation(
                    id=evaluation_id,
                    status="completed",
                    baseline_harness_name="default_v1",
                    candidate_harness_name="wide_v2",
                    limit=4,
                    source_types_json=["evaluation_queries"],
                    harness_overrides_json={},
                    total_shared_query_count=4,
                    total_improved_count=1,
                    total_regressed_count=0,
                    total_unchanged_count=3,
                    summary_json={},
                    error_message=None,
                    created_at=now,
                    completed_at=now + timedelta(seconds=2),
                ),
            ]
        )
        session.flush()
        session.add(
            SearchHarnessEvaluationSource(
                id=uuid4(),
                search_harness_evaluation_id=evaluation_id,
                source_index=0,
                source_type="evaluation_queries",
                baseline_replay_run_id=baseline_replay_run_id,
                candidate_replay_run_id=candidate_replay_run_id,
                baseline_status="completed",
                candidate_status="completed",
                baseline_query_count=4,
                candidate_query_count=4,
                baseline_passed_count=4,
                candidate_passed_count=4,
                baseline_zero_result_count=0,
                candidate_zero_result_count=0,
                baseline_table_hit_count=1,
                candidate_table_hit_count=1,
                baseline_top_result_changes=0,
                candidate_top_result_changes=0,
                baseline_mrr=1.0,
                candidate_mrr=1.0,
                baseline_foreign_top_result_count=0,
                candidate_foreign_top_result_count=0,
                acceptance_checks_json={"no_regressions": True},
                shared_query_count=4,
                improved_count=1,
                regressed_count=0,
                unchanged_count=3,
                created_at=now,
            )
        )
        session.commit()

    response = postgres_integration_harness.client.post(
        "/search/harness-releases",
        json={
            "evaluation_id": str(evaluation_id),
            "max_total_regressed_count": 0,
            "min_total_shared_query_count": 1,
            "requested_by": "integration",
            "review_note": "roundtrip",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "passed"
    assert body["evaluation_id"] == str(evaluation_id)
    assert body["evaluation_snapshot"]["evaluation_id"] == str(evaluation_id)
    assert body["release_package_sha256"]
    release_id = body["release_id"]

    list_response = postgres_integration_harness.client.get("/search/harness-releases")
    assert list_response.status_code == 200
    assert list_response.json()[0]["release_id"] == release_id

    detail_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}"
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["details"]["per_source"]["evaluation_queries"][
        "shared_query_count"
    ] == 4
