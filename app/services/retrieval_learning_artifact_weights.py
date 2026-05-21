from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.db.public.retrieval import RetrievalJudgmentKind, RetrievalTrainingRun
from app.schemas.search import (
    RetrievalLearningCandidateEvaluationRequest,
    RetrievalRerankerArtifactRequest,
)


def candidate_request_from_artifact_request(
    request: RetrievalRerankerArtifactRequest,
) -> RetrievalLearningCandidateEvaluationRequest:
    return RetrievalLearningCandidateEvaluationRequest(
        retrieval_training_run_id=request.retrieval_training_run_id,
        candidate_harness_name=request.candidate_harness_name,
        baseline_harness_name=request.baseline_harness_name,
        source_types=list(request.source_types),
        limit=request.limit,
        max_total_regressed_count=request.max_total_regressed_count,
        max_mrr_drop=request.max_mrr_drop,
        max_zero_result_count_increase=request.max_zero_result_count_increase,
        max_foreign_top_result_count_increase=(
            request.max_foreign_top_result_count_increase
        ),
        min_total_shared_query_count=request.min_total_shared_query_count,
        requested_by=request.requested_by,
        review_note=request.review_note,
    )


def _bounded_float(value: float, *, lower: float, upper: float) -> float:
    return round(max(lower, min(upper, value)), 6)


def _rows_from_training_payload(
    training_run: RetrievalTrainingRun,
) -> tuple[list[dict], list[dict]]:
    payload = training_run.training_payload_json or {}
    judgments = payload.get("judgments") if isinstance(payload, dict) else []
    hard_negatives = payload.get("hard_negatives") if isinstance(payload, dict) else []
    return (
        [row for row in judgments or [] if isinstance(row, dict)],
        [row for row in hard_negatives or [] if isinstance(row, dict)],
    )


def _numeric_feature_average(rows: list[dict], feature_name: str) -> float:
    values: list[float] = []
    for row in rows:
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        features = result.get("rerank_features") if isinstance(result, dict) else {}
        value = features.get(feature_name) if isinstance(features, dict) else None
        if isinstance(value, int | float):
            values.append(float(value))
    if not values:
        return 0.0
    return sum(values) / len(values)


def _result_type_rate(rows: list[dict], result_type: str) -> float:
    typed = [
        row
        for row in rows
        if isinstance(row.get("result"), dict) and row["result"].get("result_type")
    ]
    if not typed:
        return 0.0
    return sum(1 for row in typed if row["result"].get("result_type") == result_type) / len(
        typed
    )


def feature_weight_candidate(
    *,
    training_run: RetrievalTrainingRun,
    base_harness_name: str,
    candidate_harness_name: str,
    artifact_name: str,
    get_search_harness_fn: Callable[[str], Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    base_harness = get_search_harness_fn(base_harness_name)
    base_reranker = base_harness.reranker_config.snapshot()
    judgments, hard_negatives = _rows_from_training_payload(training_run)
    positive_judgments = [
        row
        for row in judgments
        if row.get("judgment_kind") == RetrievalJudgmentKind.POSITIVE.value
    ]
    pressure = {
        "positive_table_rate": _result_type_rate(positive_judgments, "table"),
        "hard_negative_table_rate": _result_type_rate(hard_negatives, "table"),
        "positive_chunk_rate": _result_type_rate(positive_judgments, "chunk"),
        "hard_negative_chunk_rate": _result_type_rate(hard_negatives, "chunk"),
    }
    feature_map = {
        "tabular_table_signal": "tabular_table_bonus",
        "title_token_coverage": "title_token_coverage_bonus",
        "source_filename_token_coverage": "source_filename_token_coverage_bonus",
        "document_title_token_coverage": "document_title_token_coverage_bonus",
        "document_cluster_strength": "prose_document_cluster_bonus",
        "heading_token_coverage": "heading_token_coverage_bonus",
        "phrase_overlap": "phrase_overlap_bonus",
        "rare_token_overlap": "rare_token_overlap_bonus",
        "adjacent_chunk_context_signal": "adjacent_chunk_context_bonus",
        "exact_filter_priority": "exact_filter_bonus",
    }
    deltas: dict[str, float] = {}
    observations: dict[str, Any] = {
        "feature_signal_count": len(positive_judgments) + len(hard_negatives),
        "result_type_pressure": pressure,
        "feature_deltas": {},
    }
    for feature_name, weight_name in feature_map.items():
        positive_avg = _numeric_feature_average(positive_judgments, feature_name)
        negative_avg = _numeric_feature_average(hard_negatives, feature_name)
        feature_delta = positive_avg - negative_avg
        observations["feature_deltas"][feature_name] = {
            "positive_average": round(positive_avg, 6),
            "hard_negative_average": round(negative_avg, 6),
            "delta": round(feature_delta, 6),
        }
        if feature_delta <= 0:
            continue
        base_value = float(base_reranker.get(weight_name) or 0.0)
        deltas[weight_name] = _bounded_float(feature_delta * 0.01, lower=0.0, upper=0.015)
        deltas[weight_name] = _bounded_float(
            deltas[weight_name],
            lower=0.0,
            upper=max(0.015, base_value),
        )

    type_pressure = max(
        abs(pressure["positive_table_rate"] - pressure["hard_negative_table_rate"]),
        abs(pressure["positive_chunk_rate"] - pressure["hard_negative_chunk_rate"]),
    )
    hard_negative_pressure = min(training_run.hard_negative_count, 10) / 10
    result_type_delta = max(0.001, (type_pressure + hard_negative_pressure) * 0.004)
    deltas["result_type_priority_bonus"] = _bounded_float(
        result_type_delta,
        lower=0.001,
        upper=0.012,
    )

    proposed_reranker_overrides = {
        key: _bounded_float(float(base_reranker.get(key) or 0.0) + delta, lower=0.0, upper=5.0)
        for key, delta in sorted(deltas.items())
    }
    feature_weights = {
        "schema_name": "retrieval_reranker_feature_weights",
        "schema_version": "1.0",
        "base_harness_name": base_harness_name,
        "base_reranker_name": base_harness.reranker_name,
        "base_reranker_version": base_harness.reranker_version,
        "candidate_harness_name": candidate_harness_name,
        "artifact_name": artifact_name,
        "training_dataset_sha256": training_run.training_dataset_sha256,
        "training_example_count": training_run.example_count,
        "positive_count": training_run.positive_count,
        "negative_count": training_run.negative_count,
        "missing_count": training_run.missing_count,
        "hard_negative_count": training_run.hard_negative_count,
        "observations": observations,
        "base_reranker_config": base_reranker,
        "proposed_reranker_overrides": proposed_reranker_overrides,
    }
    override_spec = {
        "base_harness_name": base_harness_name,
        "override_type": "retrieval_reranker_artifact",
        "override_source": "retrieval_learning",
        "rationale": (
            "Data-derived linear reranker candidate from persisted judgments and "
            "hard negatives."
        ),
        "reranker_overrides": proposed_reranker_overrides,
        "retrieval_profile_overrides": {},
    }
    harness_overrides = {candidate_harness_name: override_spec}
    return feature_weights, harness_overrides, override_spec
