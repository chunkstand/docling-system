from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.schemas.search import RetrievalRerankerArtifactRequest
from app.services.retrieval_learning_artifact_weights import (
    candidate_request_from_artifact_request,
    feature_weight_candidate,
)


def test_candidate_request_from_artifact_request_preserves_gate_fields() -> None:
    request = RetrievalRerankerArtifactRequest(
        retrieval_training_run_id=uuid4(),
        artifact_name="fixture-artifact",
        candidate_harness_name="candidate_v2",
        baseline_harness_name="default_v1",
        base_harness_name="default_v1",
        source_types=["feedback"],
        limit=5,
        max_total_regressed_count=1,
        max_mrr_drop=0.05,
        max_zero_result_count_increase=2,
        max_foreign_top_result_count_increase=3,
        min_total_shared_query_count=7,
        requested_by="operator",
        review_note="fixture",
    )

    candidate_request = candidate_request_from_artifact_request(request)

    assert candidate_request.max_total_regressed_count == 1
    assert candidate_request.max_mrr_drop == 0.05
    assert candidate_request.max_zero_result_count_increase == 2
    assert candidate_request.max_foreign_top_result_count_increase == 3
    assert candidate_request.min_total_shared_query_count == 7


def test_feature_weight_candidate_uses_positive_vs_negative_signal() -> None:
    training_run = SimpleNamespace(
        training_dataset_sha256="dataset-sha",
        example_count=2,
        positive_count=1,
        negative_count=0,
        missing_count=0,
        hard_negative_count=1,
        training_payload_json={
            "judgments": [
                {
                    "judgment_kind": "positive",
                    "result": {
                        "result_type": "table",
                        "rerank_features": {
                            "phrase_overlap": 0.9,
                            "tabular_table_signal": 1.0,
                        },
                    },
                }
            ],
            "hard_negatives": [
                {
                    "result": {
                        "result_type": "chunk",
                        "rerank_features": {
                            "phrase_overlap": 0.1,
                            "tabular_table_signal": 0.0,
                        },
                    },
                }
            ],
        },
    )
    harness = SimpleNamespace(
        reranker_name="linear",
        reranker_version="v1",
        reranker_config=SimpleNamespace(
            snapshot=lambda: {
                "phrase_overlap_bonus": 0.02,
                "tabular_table_bonus": 0.01,
                "result_type_priority_bonus": 0.0,
            }
        ),
    )

    feature_weights, harness_overrides, override_spec = feature_weight_candidate(
        training_run=training_run,
        base_harness_name="default_v1",
        candidate_harness_name="candidate_v2",
        artifact_name="artifact",
        get_search_harness_fn=lambda _name: harness,
    )

    overrides = feature_weights["proposed_reranker_overrides"]
    assert overrides["phrase_overlap_bonus"] > 0.02
    assert overrides["result_type_priority_bonus"] >= 0.001
    assert harness_overrides["candidate_v2"]["override_type"] == "retrieval_reranker_artifact"
    assert override_spec["reranker_overrides"] == harness_overrides["candidate_v2"][
        "reranker_overrides"
    ]
