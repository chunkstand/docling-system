from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utcnow
from app.schemas.agent_tasks import VerifySearchHarnessEvaluationTaskInput
from app.schemas.search import (
    SearchHarnessEvaluationRequest,
    SearchHarnessOptimizationAttemptResponse,
    SearchHarnessOptimizationRequest,
    SearchHarnessOptimizationResponse,
)
from app.services.search import get_search_harness
from app.services.search_harness_evaluations import evaluate_search_harness
from app.services.search_release_gate import evaluate_search_harness_release_gate


@dataclass(frozen=True)
class TuningFieldSpec:
    scope: Literal["retrieval_profile_overrides", "reranker_overrides"]
    step: int | float
    min_value: int | float
    max_value: int | float
    value_kind: Literal["int", "float"]
    precision: int = 6


_TUNING_FIELD_SPECS: dict[str, TuningFieldSpec] = {
    "keyword_candidate_multiplier": TuningFieldSpec(
        scope="retrieval_profile_overrides",
        step=1,
        min_value=2,
        max_value=20,
        value_kind="int",
    ),
    "semantic_candidate_multiplier": TuningFieldSpec(
        scope="retrieval_profile_overrides",
        step=1,
        min_value=2,
        max_value=20,
        value_kind="int",
    ),
    "min_candidate_limit": TuningFieldSpec(
        scope="retrieval_profile_overrides",
        step=4,
        min_value=8,
        max_value=80,
        value_kind="int",
    ),
    "tabular_table_bonus": TuningFieldSpec(
        scope="reranker_overrides",
        step=0.01,
        min_value=0.0,
        max_value=0.2,
        value_kind="float",
    ),
    "title_token_coverage_bonus": TuningFieldSpec(
        scope="reranker_overrides",
        step=0.005,
        min_value=0.0,
        max_value=0.1,
        value_kind="float",
    ),
    "source_filename_token_coverage_bonus": TuningFieldSpec(
        scope="reranker_overrides",
        step=0.005,
        min_value=0.0,
        max_value=0.1,
        value_kind="float",
    ),
    "document_title_token_coverage_bonus": TuningFieldSpec(
        scope="reranker_overrides",
        step=0.005,
        min_value=0.0,
        max_value=0.1,
        value_kind="float",
    ),
    "prose_document_cluster_bonus": TuningFieldSpec(
        scope="reranker_overrides",
        step=0.01,
        min_value=0.0,
        max_value=0.15,
        value_kind="float",
    ),
    "phrase_overlap_bonus": TuningFieldSpec(
        scope="reranker_overrides",
        step=0.005,
        min_value=0.0,
        max_value=0.1,
        value_kind="float",
    ),
    "rare_token_overlap_bonus": TuningFieldSpec(
        scope="reranker_overrides",
        step=0.005,
        min_value=0.0,
        max_value=0.1,
        value_kind="float",
    ),
    "adjacent_chunk_context_bonus": TuningFieldSpec(
        scope="reranker_overrides",
        step=0.005,
        min_value=0.0,
        max_value=0.1,
        value_kind="float",
    ),
    "prose_table_penalty": TuningFieldSpec(
        scope="reranker_overrides",
        step=0.005,
        min_value=0.0,
        max_value=0.1,
        value_kind="float",
    ),
    "result_type_priority_bonus": TuningFieldSpec(
        scope="reranker_overrides",
        step=0.001,
        min_value=0.0,
        max_value=0.05,
        value_kind="float",
    ),
}

DEFAULT_TUNING_FIELDS = (
    "keyword_candidate_multiplier",
    "semantic_candidate_multiplier",
    "min_candidate_limit",
    "tabular_table_bonus",
    "title_token_coverage_bonus",
    "source_filename_token_coverage_bonus",
    "document_title_token_coverage_bonus",
    "prose_document_cluster_bonus",
    "phrase_overlap_bonus",
    "rare_token_overlap_bonus",
    "adjacent_chunk_context_bonus",
    "prose_table_penalty",
    "result_type_priority_bonus",
)


def _validate_tuning_fields(fields: list[str]) -> list[str]:
    normalized: list[str] = []
    unknown = sorted({field for field in fields if field not in _TUNING_FIELD_SPECS})
    if unknown:
        available = ", ".join(sorted(_TUNING_FIELD_SPECS))
        msg = f"Unknown tuning field(s): {', '.join(unknown)}. Available: {available}"
        raise ValueError(msg)
    for field in fields:
        if field not in normalized:
            normalized.append(field)
    return normalized


def _base_override_spec(request: SearchHarnessOptimizationRequest) -> dict:
    return {
        "base_harness_name": request.base_harness_name,
        "override_type": "search_harness_optimization",
        "override_source": "search_harness_optimization_loop",
        "rationale": (
            "Bounded local harness optimization loop using replay and evaluation gate criteria."
        ),
        "retrieval_profile_overrides": {},
        "reranker_overrides": {},
    }


def _get_base_field_value(base_harness, field_name: str):
    field_spec = _TUNING_FIELD_SPECS[field_name]
    if field_spec.scope == "retrieval_profile_overrides":
        return getattr(base_harness.retrieval_profile, field_name)
    return getattr(base_harness.reranker_config, field_name)


def _get_effective_field_value(base_harness, override_spec: dict, field_name: str):
    field_spec = _TUNING_FIELD_SPECS[field_name]
    overrides = dict(override_spec.get(field_spec.scope) or {})
    if field_name in overrides:
        return overrides[field_name]
    return _get_base_field_value(base_harness, field_name)


def _normalize_candidate_value(field_name: str, value: int | float):
    field_spec = _TUNING_FIELD_SPECS[field_name]
    bounded = max(field_spec.min_value, min(field_spec.max_value, value))
    if field_spec.value_kind == "int":
        return int(round(float(bounded)))
    return round(float(bounded), field_spec.precision)


def _mutate_override_spec(
    *,
    base_harness,
    current_spec: dict,
    field_name: str,
    direction: Literal["increase", "decrease"],
) -> tuple[dict, int | float] | None:
    field_spec = _TUNING_FIELD_SPECS[field_name]
    current_value = _get_effective_field_value(base_harness, current_spec, field_name)
    delta = field_spec.step if direction == "increase" else -field_spec.step
    mutated_value = _normalize_candidate_value(field_name, current_value + delta)
    if mutated_value == current_value:
        return None

    next_spec = json.loads(json.dumps(current_spec))
    overrides = dict(next_spec.get(field_spec.scope) or {})
    base_value = _get_base_field_value(base_harness, field_name)
    if mutated_value == base_value:
        overrides.pop(field_name, None)
    else:
        overrides[field_name] = mutated_value
    next_spec[field_spec.scope] = overrides
    return next_spec, mutated_value


def _override_signature(override_spec: dict) -> str:
    return json.dumps(
        {
            "base_harness_name": override_spec.get("base_harness_name"),
            "retrieval_profile_overrides": override_spec.get("retrieval_profile_overrides") or {},
            "reranker_overrides": override_spec.get("reranker_overrides") or {},
        },
        sort_keys=True,
    )


def _modified_field_count(override_spec: dict) -> int:
    return len(override_spec.get("retrieval_profile_overrides") or {}) + len(
        override_spec.get("reranker_overrides") or {}
    )


def _gate_payload(
    request: SearchHarnessOptimizationRequest,
) -> VerifySearchHarnessEvaluationTaskInput:
    return VerifySearchHarnessEvaluationTaskInput(
        target_task_id=UUID(int=0),
        max_total_regressed_count=request.max_total_regressed_count,
        max_mrr_drop=request.max_mrr_drop,
        max_zero_result_count_increase=request.max_zero_result_count_increase,
        max_foreign_top_result_count_increase=request.max_foreign_top_result_count_increase,
        min_total_shared_query_count=request.min_total_shared_query_count,
    )


def _gate_to_dict(gate_outcome) -> dict:
    return {
        "outcome": gate_outcome.outcome,
        "metrics": gate_outcome.metrics,
        "reasons": gate_outcome.reasons,
        "details": gate_outcome.details,
    }


def _score_evaluation(evaluation, gate_outcome, override_spec: dict) -> dict:
    total_mrr_gain = round(
        sum(source.candidate_mrr - source.baseline_mrr for source in evaluation.sources),
        6,
    )
    total_passed_gain = sum(
        source.candidate_passed_count - source.baseline_passed_count
        for source in evaluation.sources
    )
    total_zero_result_count_increase = sum(
        max(0, source.candidate_zero_result_count - source.baseline_zero_result_count)
        for source in evaluation.sources
    )
    total_foreign_top_result_count_increase = sum(
        max(
            0,
            source.candidate_foreign_top_result_count - source.baseline_foreign_top_result_count,
        )
        for source in evaluation.sources
    )
    reason_count = len(gate_outcome.reasons)
    modified_field_count = _modified_field_count(override_spec)
    sort_key = (
        1 if gate_outcome.outcome == "passed" else 0,
        -reason_count,
        evaluation.total_improved_count - evaluation.total_regressed_count,
        total_passed_gain,
        total_mrr_gain,
        -total_zero_result_count_increase,
        -total_foreign_top_result_count_increase,
        -modified_field_count,
        evaluation.total_shared_query_count,
    )
    return {
        "passed": gate_outcome.outcome == "passed",
        "reason_count": reason_count,
        "total_improved_count": evaluation.total_improved_count,
        "total_regressed_count": evaluation.total_regressed_count,
        "total_unchanged_count": evaluation.total_unchanged_count,
        "total_shared_query_count": evaluation.total_shared_query_count,
        "total_passed_gain": total_passed_gain,
        "total_mrr_gain": total_mrr_gain,
        "total_zero_result_count_increase": total_zero_result_count_increase,
        "total_foreign_top_result_count_increase": total_foreign_top_result_count_increase,
        "modified_field_count": modified_field_count,
        "sort_key": list(sort_key),
    }


def _score_sort_key(score: dict) -> tuple:
    return tuple(score.get("sort_key") or [])


def _evaluate_override_candidate(
    session: Session,
    request: SearchHarnessOptimizationRequest,
    override_spec: dict,
):
    harness_overrides = {request.candidate_harness_name: override_spec}
    evaluation = evaluate_search_harness(
        session,
        SearchHarnessEvaluationRequest(
            candidate_harness_name=request.candidate_harness_name,
            baseline_harness_name=request.baseline_harness_name,
            source_types=request.source_types,
            limit=request.limit,
        ),
        harness_overrides=harness_overrides,
    )
    gate_outcome = evaluate_search_harness_release_gate(session, evaluation, _gate_payload(request))
    score = _score_evaluation(evaluation, gate_outcome, override_spec)
    return evaluation, gate_outcome, score


def _artifact_path(candidate_harness_name: str) -> Path:
    timestamp = utcnow().strftime("%Y%m%dT%H%M%SZ")
    safe_name = "".join(
        char if char.isalnum() or char in {"-", "_"} else "_" for char in candidate_harness_name
    )
    return (
        get_settings().storage_root.resolve()
        / "search_harness_loops"
        / f"{timestamp}_{safe_name}.json"
    )


def run_search_harness_optimization_loop(
    session: Session,
    request: SearchHarnessOptimizationRequest,
) -> SearchHarnessOptimizationResponse:
    if request.candidate_harness_name == request.baseline_harness_name:
        raise ValueError("candidate_harness_name must differ from baseline_harness_name.")

    base_harness = get_search_harness(request.base_harness_name)
    tuned_fields = _validate_tuning_fields(request.tune_fields or list(DEFAULT_TUNING_FIELDS))

    best_override_spec = _base_override_spec(request)
    best_evaluation, best_gate_outcome, best_score = _evaluate_override_candidate(
        session,
        request,
        best_override_spec,
    )
    best_gate = _gate_to_dict(best_gate_outcome)
    attempts = [
        SearchHarnessOptimizationAttemptResponse(
            iteration=0,
            field_name="baseline",
            direction="baseline",
            scope="baseline",
            proposed_value=None,
            accepted=True,
            score=best_score,
            evaluation=best_evaluation,
            gate=best_gate,
            override_spec=best_override_spec,
        )
    ]
    seen_signatures = {_override_signature(best_override_spec)}
    iterations_completed = 0
    stopped_reason = "iteration_limit_reached"

    for iteration in range(1, request.iterations + 1):
        candidate_attempts: list[tuple[SearchHarnessOptimizationAttemptResponse, dict, dict]] = []
        for field_name in tuned_fields:
            field_spec = _TUNING_FIELD_SPECS[field_name]
            for direction in ("increase", "decrease"):
                mutation = _mutate_override_spec(
                    base_harness=base_harness,
                    current_spec=best_override_spec,
                    field_name=field_name,
                    direction=direction,
                )
                if mutation is None:
                    continue
                candidate_override_spec, proposed_value = mutation
                signature = _override_signature(candidate_override_spec)
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)

                evaluation, gate_outcome, score = _evaluate_override_candidate(
                    session,
                    request,
                    candidate_override_spec,
                )
                attempt = SearchHarnessOptimizationAttemptResponse(
                    iteration=iteration,
                    field_name=field_name,
                    direction=direction,
                    scope=field_spec.scope,
                    proposed_value=proposed_value,
                    accepted=False,
                    score=score,
                    evaluation=evaluation,
                    gate=_gate_to_dict(gate_outcome),
                    override_spec=candidate_override_spec,
                )
                attempts.append(attempt)
                candidate_attempts.append((attempt, candidate_override_spec, score))

        if not candidate_attempts:
            stopped_reason = "no_mutations_available"
            break

        iterations_completed = iteration
        improving_candidates = [
            (attempt, override_spec, score)
            for attempt, override_spec, score in candidate_attempts
            if _score_sort_key(score) > _score_sort_key(best_score)
        ]
        if not improving_candidates:
            stopped_reason = "no_improving_candidates"
            break

        best_attempt, next_override_spec, next_score = max(
            improving_candidates,
            key=lambda item: _score_sort_key(item[2]),
        )
        best_attempt.accepted = True
        best_override_spec = next_override_spec
        best_score = next_score
        best_evaluation = best_attempt.evaluation
        best_gate = best_attempt.gate

    response = SearchHarnessOptimizationResponse(
        base_harness_name=request.base_harness_name,
        baseline_harness_name=request.baseline_harness_name,
        candidate_harness_name=request.candidate_harness_name,
        source_types=request.source_types,
        limit=request.limit,
        iterations_requested=request.iterations,
        iterations_completed=iterations_completed,
        tuned_fields=tuned_fields,
        stopped_reason=stopped_reason,
        best_override_spec=best_override_spec,
        best_score=best_score,
        best_evaluation=best_evaluation,
        best_gate=best_gate,
        attempts=attempts,
    )

    artifact_path = _artifact_path(request.candidate_harness_name)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    response.artifact_path = str(artifact_path)
    artifact_path.write_text(json.dumps(response.model_dump(mode="json"), indent=2, sort_keys=True))
    return response
