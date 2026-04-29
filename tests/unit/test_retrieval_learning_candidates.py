from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.models import RetrievalLearningCandidateEvaluation, RetrievalTrainingRun
from app.schemas.search import (
    RetrievalLearningCandidateEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessReleaseResponse,
)
from app.services import retrieval_learning


class FakeSession:
    def __init__(self, training_run: RetrievalTrainingRun) -> None:
        self.training_run = training_run
        self.added = []

    def get(self, model, key):
        if model is RetrievalTrainingRun and key == self.training_run.id:
            return self.training_run
        return None

    def add(self, row) -> None:
        self.added.append(row)

    def flush(self) -> None:
        return None


def test_evaluate_retrieval_learning_candidate_records_governed_link(monkeypatch) -> None:
    now = datetime.now(UTC)
    training_run = RetrievalTrainingRun(
        id=uuid4(),
        judgment_set_id=uuid4(),
        status="completed",
        training_dataset_sha256="training-sha",
        training_payload_json={"judgments": []},
        summary_json={"training_example_count": 7},
        example_count=7,
        positive_count=2,
        negative_count=2,
        missing_count=1,
        hard_negative_count=2,
        created_by="materializer",
        created_at=now,
        completed_at=now,
    )
    evaluation_id = uuid4()
    release_id = uuid4()
    governance_event_id = uuid4()
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()

    def fake_evaluate_search_harness(session, request):
        assert request.candidate_harness_name == "wide_v2"
        assert request.baseline_harness_name == "default_v1"
        return SearchHarnessEvaluationResponse(
            evaluation_id=evaluation_id,
            status="completed",
            baseline_harness_name=request.baseline_harness_name,
            candidate_harness_name=request.candidate_harness_name,
            source_types=list(request.source_types),
            limit=request.limit,
            total_shared_query_count=3,
            total_improved_count=1,
            total_regressed_count=0,
            total_unchanged_count=2,
            created_at=now,
            completed_at=now,
            sources=[
                {
                    "source_type": "feedback",
                    "baseline_replay_run_id": baseline_replay_run_id,
                    "candidate_replay_run_id": candidate_replay_run_id,
                    "shared_query_count": 3,
                    "improved_count": 1,
                    "regressed_count": 0,
                    "unchanged_count": 2,
                }
            ],
        )

    def fake_record_release(session, evaluation, payload, *, requested_by=None, review_note=None):
        assert evaluation.evaluation_id == evaluation_id
        assert payload.max_total_regressed_count == 0
        return SearchHarnessReleaseResponse(
            release_id=release_id,
            evaluation_id=evaluation_id,
            outcome="passed",
            baseline_harness_name=evaluation.baseline_harness_name,
            candidate_harness_name=evaluation.candidate_harness_name,
            limit=evaluation.limit,
            source_types=list(evaluation.source_types),
            thresholds={"max_total_regressed_count": 0},
            metrics={"total_shared_query_count": 3},
            reasons=[],
            release_package_sha256="release-sha",
            requested_by=requested_by,
            review_note=review_note,
            created_at=now,
            details={"evaluation_id": str(evaluation_id)},
            evaluation_snapshot=evaluation.model_dump(mode="json"),
        )

    monkeypatch.setattr(
        retrieval_learning,
        "evaluate_search_harness",
        fake_evaluate_search_harness,
    )
    monkeypatch.setattr(
        retrieval_learning,
        "record_search_harness_release_gate",
        fake_record_release,
    )
    monkeypatch.setattr(
        retrieval_learning,
        "record_semantic_governance_event",
        lambda *args, **kwargs: SimpleNamespace(id=governance_event_id),
    )

    session = FakeSession(training_run)
    response = retrieval_learning.evaluate_retrieval_learning_candidate(
        session,
        RetrievalLearningCandidateEvaluationRequest(
            retrieval_training_run_id=training_run.id,
            candidate_harness_name="wide_v2",
            source_types=["feedback"],
            limit=3,
            requested_by="operator",
            review_note="learning gate",
        ),
    )

    rows = [row for row in session.added if isinstance(row, RetrievalLearningCandidateEvaluation)]
    assert len(rows) == 1
    assert rows[0].retrieval_training_run_id == training_run.id
    assert rows[0].judgment_set_id == training_run.judgment_set_id
    assert rows[0].search_harness_evaluation_id == evaluation_id
    assert rows[0].search_harness_release_id == release_id
    assert rows[0].semantic_governance_event_id == governance_event_id
    assert rows[0].learning_package_sha256
    assert training_run.search_harness_evaluation_id == evaluation_id
    assert training_run.search_harness_release_id == release_id
    assert response.gate_outcome == "passed"
    assert response.training_dataset_sha256 == "training-sha"
    assert response.release is not None
    assert response.release.release_id == release_id


def test_claim_support_expected_judgment_rejects_unknown_verdict() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported claim-support replay-alert fixture expected_verdict",
    ):
        retrieval_learning._claim_support_expected_judgment(
            {"expected_verdict": "needs_review"}
        )
