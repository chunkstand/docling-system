from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app


def test_quality_summary_route_uses_quality_service(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.main.get_quality_summary",
        lambda session: {
            "document_count": 8,
            "latest_runs_completed": 8,
            "documents_with_latest_evaluation": 7,
            "missing_latest_evaluations": 1,
            "completed_latest_evaluations": 7,
            "failed_latest_evaluations": 0,
            "skipped_latest_evaluations": 0,
            "total_failed_queries": 3,
            "documents_with_failed_queries": 2,
            "total_failed_structural_checks": 1,
            "documents_with_structural_failures": 1,
            "failed_run_count": 4,
            "failed_runs_by_stage": [{"failure_stage": "validation", "run_count": 2}],
        },
    )

    client = TestClient(app)
    response = client.get("/quality/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["document_count"] == 8
    assert body["failed_runs_by_stage"][0]["failure_stage"] == "validation"


def test_quality_evaluations_route_uses_quality_service(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()
    evaluation_id = uuid4()
    monkeypatch.setattr(
        "app.api.main.list_quality_evaluations",
        lambda session: [
            {
                "document_id": str(document_id),
                "source_filename": "chapter-1.pdf",
                "title": "Chapter 1",
                "latest_run_id": str(run_id),
                "latest_run_status": "completed",
                "latest_validation_status": "passed",
                "evaluation_id": str(evaluation_id),
                "evaluation_status": "completed",
                "fixture_name": "fixture",
                "query_count": 4,
                "passed_queries": 3,
                "failed_queries": 1,
                "regressed_queries": 0,
                "improved_queries": 1,
                "stable_queries": 2,
                "failed_structural_checks": 0,
                "structural_passed": True,
                "error_message": None,
                "updated_at": "2026-04-12T00:00:00Z",
            }
        ],
    )

    client = TestClient(app)
    response = client.get("/quality/evaluations")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["document_id"] == str(document_id)
    assert body[0]["evaluation_status"] == "completed"


def test_quality_failures_route_uses_quality_service(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()
    monkeypatch.setattr(
        "app.api.main.get_quality_failures",
        lambda session: {
            "evaluation_failures": [
                {
                    "document_id": str(document_id),
                    "source_filename": "chapter-2.pdf",
                    "title": "Chapter 2",
                    "latest_run_id": str(run_id),
                    "latest_run_status": "completed",
                    "latest_validation_status": "passed",
                    "evaluation_id": None,
                    "evaluation_status": "missing",
                    "fixture_name": None,
                    "query_count": 0,
                    "passed_queries": 0,
                    "failed_queries": 0,
                    "regressed_queries": 0,
                    "improved_queries": 0,
                    "stable_queries": 0,
                    "failed_structural_checks": 0,
                    "structural_passed": None,
                    "error_message": None,
                    "updated_at": "2026-04-12T00:00:00Z",
                }
            ],
            "run_failures": [
                {
                    "document_id": str(document_id),
                    "source_filename": "chapter-2.pdf",
                    "title": "Chapter 2",
                    "run_id": str(run_id),
                    "run_number": 2,
                    "status": "failed",
                    "failure_stage": "validation",
                    "error_message": "boom",
                    "has_failure_artifact": True,
                    "created_at": "2026-04-12T00:00:00Z",
                    "completed_at": "2026-04-12T00:00:01Z",
                }
            ],
        },
    )

    client = TestClient(app)
    response = client.get("/quality/failures")

    assert response.status_code == 200
    body = response.json()
    assert body["evaluation_failures"][0]["evaluation_status"] == "missing"
    assert body["run_failures"][0]["failure_stage"] == "validation"


def test_quality_eval_candidates_route_uses_quality_service(monkeypatch) -> None:
    search_request_id = uuid4()

    monkeypatch.setattr(
        "app.api.main.list_quality_eval_candidates",
        lambda session: [
            {
                "candidate_type": "live_search_gap",
                "reason": "tabular search returned no table hits",
                "query_text": "table 701.2",
                "mode": "hybrid",
                "filters": {},
                "expected_result_type": "table",
                "fixture_name": None,
                "occurrence_count": 3,
                "latest_seen_at": "2026-04-12T00:00:00Z",
                "document_id": None,
                "source_filename": None,
                "evaluation_id": None,
                "search_request_id": str(search_request_id),
            }
        ],
    )

    client = TestClient(app)
    response = client.get("/quality/eval-candidates")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["candidate_type"] == "live_search_gap"
    assert body[0]["search_request_id"] == str(search_request_id)


def test_quality_trends_route_uses_quality_service(monkeypatch) -> None:
    replay_run_id = uuid4()

    monkeypatch.setattr(
        "app.api.main.get_quality_trends",
        lambda session: {
            "search_request_days": [
                {
                    "bucket_date": "2026-04-12",
                    "request_count": 4,
                    "zero_result_count": 1,
                    "table_hit_rate": 0.5,
                }
            ],
            "feedback_counts": [{"feedback_type": "missing_table", "count": 2}],
            "answer_feedback_counts": [{"feedback_type": "helpful", "count": 1}],
            "recent_replay_runs": [
                {
                    "replay_run_id": str(replay_run_id),
                    "source_type": "feedback",
                    "status": "completed",
                    "query_count": 3,
                    "passed_count": 2,
                    "failed_count": 1,
                    "created_at": "2026-04-12T00:00:00Z",
                }
            ],
        },
    )

    client = TestClient(app)
    response = client.get("/quality/trends")

    assert response.status_code == 200
    body = response.json()
    assert body["search_request_days"][0]["bucket_date"] == "2026-04-12"
    assert body["feedback_counts"][0]["feedback_type"] == "missing_table"
    assert body["recent_replay_runs"][0]["replay_run_id"] == str(replay_run_id)
