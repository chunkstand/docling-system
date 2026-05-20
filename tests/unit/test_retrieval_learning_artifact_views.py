from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services import retrieval_learning_artifact_views as artifact_views


def test_to_reranker_artifact_summary_serializes_row_metadata() -> None:
    now = datetime.now(UTC)
    artifact_id = uuid4()
    training_run_id = uuid4()
    candidate_evaluation_id = uuid4()
    evaluation_id = uuid4()
    release_id = uuid4()
    event_id = uuid4()

    row = SimpleNamespace(
        id=artifact_id,
        retrieval_training_run_id=training_run_id,
        judgment_set_id=uuid4(),
        retrieval_learning_candidate_evaluation_id=candidate_evaluation_id,
        search_harness_evaluation_id=evaluation_id,
        search_harness_release_id=release_id,
        semantic_governance_event_id=event_id,
        artifact_kind="linear_feature_weight_candidate",
        artifact_name="learned-reranker",
        artifact_version="wide_v2+dataset",
        status="evaluated",
        gate_outcome="passed",
        baseline_harness_name="default_v1",
        candidate_harness_name="wide_v2",
        source_types_json=["feedback"],
        limit=5,
        training_dataset_sha256="dataset-sha",
        training_example_count=7,
        positive_count=2,
        negative_count=1,
        missing_count=0,
        hard_negative_count=1,
        thresholds_json={"max_total_regressed_count": 0},
        metrics_json={"total_shared_query_count": 3},
        reasons_json=["gate passed"],
        artifact_sha256="artifact-sha",
        change_impact_sha256="impact-sha",
        created_by="operator",
        review_note="fixture",
        created_at=now,
        completed_at=now,
    )

    response = artifact_views.to_reranker_artifact_summary(row)

    assert response.artifact_id == artifact_id
    assert response.retrieval_training_run_id == training_run_id
    assert response.search_harness_release_id == release_id
    assert response.semantic_governance_event_id == event_id
    assert response.source_types == ["feedback"]
    assert response.metrics == {"total_shared_query_count": 3}
    assert response.reasons == ["gate passed"]


def test_get_retrieval_reranker_artifact_detail_raises_machine_readable_error() -> None:
    artifact_id = uuid4()

    class FakeSession:
        def get(self, _model, lookup_id):
            assert lookup_id == artifact_id
            return None

    with pytest.raises(HTTPException) as exc_info:
        artifact_views.get_retrieval_reranker_artifact_detail(FakeSession(), artifact_id)

    error = exc_info.value
    assert error.status_code == 404
    assert error.detail["code"] == "retrieval_reranker_artifact_not_found"
    assert error.detail["context"]["artifact_id"] == str(artifact_id)
