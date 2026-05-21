from __future__ import annotations

import json

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.db.public.agent_tasks import AgentTask
from app.schemas.agent_task_search_workflows import (
    TriageReplayRegressionTaskInput,
    VerifySearchHarnessEvaluationTaskInput,
)
from app.schemas.search import SearchHarnessEvaluationRequest


def recommend_triage_next_action(
    *,
    total_shared_query_count: int,
    total_regressed_count: int,
    total_improved_count: int,
    reason_count: int,
    quality_candidate_count: int,
) -> tuple[str, str]:
    if total_shared_query_count == 0:
        return "collect_more_evidence", "low"
    if reason_count > 0 or total_regressed_count > 0:
        return "keep_baseline_and_investigate", "high"
    if total_improved_count > 0:
        return "candidate_ready_for_review", "medium"
    if quality_candidate_count > 0:
        return "investigate_unresolved_gaps", "medium"
    return "no_change", "low"


def _replay_query_key(row) -> tuple[str, str, str]:
    return row.query_text, row.mode, json.dumps(row.filters or {}, sort_keys=True)


def _safe_search_request_explanation(
    session: Session,
    search_request_id,
    *,
    get_search_request_explanation_func,
) -> dict | None:
    if search_request_id is None or not hasattr(session, "execute"):
        return None
    try:
        explanation = get_search_request_explanation_func(session, search_request_id)
    except Exception:
        return None
    return explanation.model_dump(mode="json")


def _repair_case_examples(
    session: Session,
    evaluation,
    *,
    compare_search_replay_runs_func,
    get_search_replay_run_detail_func,
    get_search_request_explanation_func,
    max_examples: int = 5,
) -> tuple[list[dict], list[str], list[str]]:
    if not hasattr(session, "execute"):
        return [], [], []

    examples: list[dict] = []
    affected_result_types: set[str] = set()
    diagnosis_categories: list[str] = []
    for source in evaluation.sources:
        try:
            comparison = compare_search_replay_runs_func(
                session,
                source.baseline_replay_run_id,
                source.candidate_replay_run_id,
            )
            baseline_detail = get_search_replay_run_detail_func(
                session,
                source.baseline_replay_run_id,
            )
            candidate_detail = get_search_replay_run_detail_func(
                session,
                source.candidate_replay_run_id,
            )
        except Exception:
            continue

        baseline_rows = {_replay_query_key(row): row for row in baseline_detail.query_results}
        candidate_rows = {_replay_query_key(row): row for row in candidate_detail.query_results}
        for changed_query in comparison.changed_queries:
            key = _replay_query_key(changed_query)
            baseline_row = baseline_rows.get(key)
            candidate_row = candidate_rows.get(key)
            if baseline_row is None or candidate_row is None:
                continue

            baseline_explanation = _safe_search_request_explanation(
                session,
                baseline_row.replay_search_request_id,
                get_search_request_explanation_func=get_search_request_explanation_func,
            )
            candidate_explanation = _safe_search_request_explanation(
                session,
                candidate_row.replay_search_request_id,
                get_search_request_explanation_func=get_search_request_explanation_func,
            )
            for explanation in (baseline_explanation, candidate_explanation):
                if explanation is None:
                    continue
                diagnosis = explanation.get("diagnosis") or {}
                category = diagnosis.get("category")
                if category and category not in diagnosis_categories:
                    diagnosis_categories.append(category)
                for result in explanation.get("top_result_snapshot") or []:
                    result_type = result.get("result_type")
                    if result_type:
                        affected_result_types.add(result_type)

            examples.append(
                {
                    "source_type": source.source_type,
                    "query_text": changed_query.query_text,
                    "mode": changed_query.mode,
                    "filters": changed_query.filters,
                    "baseline_passed": changed_query.baseline_passed,
                    "candidate_passed": changed_query.candidate_passed,
                    "baseline_result_count": changed_query.baseline_result_count,
                    "candidate_result_count": changed_query.candidate_result_count,
                    "baseline_search_request_id": (
                        str(baseline_row.replay_search_request_id)
                        if baseline_row.replay_search_request_id is not None
                        else None
                    ),
                    "candidate_search_request_id": (
                        str(candidate_row.replay_search_request_id)
                        if candidate_row.replay_search_request_id is not None
                        else None
                    ),
                    "baseline_explanation": baseline_explanation,
                    "candidate_explanation": candidate_explanation,
                }
            )
            if len(examples) >= max_examples:
                return examples, sorted(affected_result_types), diagnosis_categories
    return examples, sorted(affected_result_types), diagnosis_categories


def _repair_case_failure_classification(
    *,
    evaluation,
    verification_outcome,
    quality_candidate_count: int,
) -> str:
    if evaluation.total_regressed_count > 0:
        return "replay_regression"
    if verification_outcome.reasons:
        return "release_gate_failure"
    if quality_candidate_count > 0:
        return "unresolved_quality_gap"
    if evaluation.total_improved_count > 0:
        return "candidate_improvement"
    return "no_actionable_gap"


def build_repair_case_payload(
    session: Session,
    *,
    candidate_harness_name: str,
    baseline_harness_name: str,
    evaluation,
    verification_outcome,
    recommendation: str,
    quality_candidate_count: int,
    compare_search_replay_runs_func,
    get_search_replay_run_detail_func,
    get_search_request_explanation_func,
) -> dict:
    examples, affected_result_types, diagnosis_categories = _repair_case_examples(
        session,
        evaluation,
        compare_search_replay_runs_func=compare_search_replay_runs_func,
        get_search_replay_run_detail_func=get_search_replay_run_detail_func,
        get_search_request_explanation_func=get_search_request_explanation_func,
    )
    classification = _repair_case_failure_classification(
        evaluation=evaluation,
        verification_outcome=verification_outcome,
        quality_candidate_count=quality_candidate_count,
    )
    likely_root_cause = None
    if diagnosis_categories:
        likely_root_cause = "Observed diagnostic categories: " + ", ".join(diagnosis_categories)
    elif classification == "unresolved_quality_gap":
        likely_root_cause = "Quality candidates remain unresolved outside the replay comparison."
    elif classification == "candidate_improvement":
        likely_root_cause = (
            "Candidate harness improves replay outcomes without observed regressions."
        )

    return {
        "schema_name": "search_harness_repair_case",
        "schema_version": "1.0",
        "candidate_harness_name": candidate_harness_name,
        "baseline_harness_name": baseline_harness_name,
        "failure_classification": classification,
        "problem_statement": (
            f"{candidate_harness_name} vs {baseline_harness_name}: "
            f"{evaluation.total_improved_count} improved, "
            f"{evaluation.total_regressed_count} regressed, "
            f"{evaluation.total_unchanged_count} unchanged query outcome(s)."
        ),
        "observed_metric_delta": {
            "total_shared_query_count": evaluation.total_shared_query_count,
            "total_improved_count": evaluation.total_improved_count,
            "total_regressed_count": evaluation.total_regressed_count,
            "total_unchanged_count": evaluation.total_unchanged_count,
            "quality_candidate_count": quality_candidate_count,
        },
        "affected_result_types": affected_result_types,
        "likely_root_cause": likely_root_cause,
        "allowed_repair_surface": [
            "retrieval_profile_overrides",
            "reranker_overrides",
        ],
        "blocked_repair_surfaces": [
            "canonical_document_artifacts",
            "document_ingest_contracts",
            "evaluation_corpus_weakening",
            "yaml_as_source_of_truth",
        ],
        "recommended_next_action": recommendation,
        "diagnostic_examples": examples,
        "evidence_refs": [
            {
                "ref_kind": "harness_evaluation",
                "candidate_harness_name": candidate_harness_name,
                "baseline_harness_name": baseline_harness_name,
                "source_count": len(evaluation.sources),
            },
            *[
                {
                    "ref_kind": "replay_run_pair",
                    "source_type": source.source_type,
                    "baseline_replay_run_id": str(source.baseline_replay_run_id),
                    "candidate_replay_run_id": str(source.candidate_replay_run_id),
                    "shared_query_count": source.shared_query_count,
                    "improved_count": source.improved_count,
                    "regressed_count": source.regressed_count,
                }
                for source in evaluation.sources
            ],
        ],
    }


def triage_replay_regression(
    session: Session,
    task: AgentTask,
    payload: TriageReplayRegressionTaskInput,
    *,
    list_quality_eval_candidates_func,
    evaluate_search_harness_func,
    evaluate_search_harness_verification_func,
    create_agent_task_verification_record_func,
    create_agent_task_artifact_func,
    storage_service_factory,
    compare_search_replay_runs_func,
    get_search_replay_run_detail_func,
    get_search_request_explanation_func,
) -> dict:
    quality_candidates = list_quality_eval_candidates_func(
        session,
        limit=payload.quality_candidate_limit,
        include_resolved=payload.include_resolved_candidates,
    )
    evaluation = evaluate_search_harness_func(
        session,
        SearchHarnessEvaluationRequest(
            candidate_harness_name=payload.candidate_harness_name,
            baseline_harness_name=payload.baseline_harness_name,
            source_types=payload.source_types,
            limit=payload.replay_limit,
        ),
    )
    verification_outcome = evaluate_search_harness_verification_func(
        session,
        evaluation,
        VerifySearchHarnessEvaluationTaskInput(
            target_task_id=task.id,
            max_total_regressed_count=payload.max_total_regressed_count,
            max_mrr_drop=payload.max_mrr_drop,
            max_zero_result_count_increase=payload.max_zero_result_count_increase,
            max_foreign_top_result_count_increase=payload.max_foreign_top_result_count_increase,
            min_total_shared_query_count=payload.min_total_shared_query_count,
        ),
    )
    recommendation, confidence = recommend_triage_next_action(
        total_shared_query_count=evaluation.total_shared_query_count,
        total_regressed_count=evaluation.total_regressed_count,
        total_improved_count=evaluation.total_improved_count,
        reason_count=len(verification_outcome.reasons),
        quality_candidate_count=len(quality_candidates),
    )
    top_candidates = quality_candidates[:3]
    repair_case_payload = build_repair_case_payload(
        session,
        candidate_harness_name=payload.candidate_harness_name,
        baseline_harness_name=payload.baseline_harness_name,
        evaluation=evaluation,
        verification_outcome=verification_outcome,
        recommendation=recommendation,
        quality_candidate_count=len(quality_candidates),
        compare_search_replay_runs_func=compare_search_replay_runs_func,
        get_search_replay_run_detail_func=get_search_replay_run_detail_func,
        get_search_request_explanation_func=get_search_request_explanation_func,
    )
    triage_payload = {
        "shadow_mode": True,
        "triage_kind": "replay_regression",
        "candidate_harness_name": payload.candidate_harness_name,
        "baseline_harness_name": payload.baseline_harness_name,
        "source_types": payload.source_types,
        "replay_limit": payload.replay_limit,
        "quality_candidate_count": len(quality_candidates),
        "top_quality_candidates": jsonable_encoder(top_candidates),
        "evaluation": jsonable_encoder(evaluation),
        "verification": {
            "verifier_type": "shadow_mode_triage_gate",
            "outcome": verification_outcome.outcome,
            "metrics": verification_outcome.metrics,
            "reasons": verification_outcome.reasons,
            "details": verification_outcome.details,
        },
        "recommendation": {
            "next_action": recommendation,
            "confidence": confidence,
            "summary": (
                f"{payload.candidate_harness_name} vs {payload.baseline_harness_name} "
                f"across {len(payload.source_types)} source type(s)."
            ),
        },
        "repair_case": repair_case_payload,
    }
    verification_record = create_agent_task_verification_record_func(
        session,
        target_task_id=task.id,
        verification_task_id=task.id,
        verifier_type="shadow_mode_triage_gate",
        outcome=verification_outcome.outcome,
        metrics=verification_outcome.metrics,
        reasons=verification_outcome.reasons,
        details=verification_outcome.details,
    )
    artifact = create_agent_task_artifact_func(
        session,
        task_id=task.id,
        artifact_kind="triage_summary",
        payload=triage_payload,
        storage_service=storage_service_factory(),
        filename="triage_summary.json",
    )
    repair_case_artifact = create_agent_task_artifact_func(
        session,
        task_id=task.id,
        artifact_kind="repair_case",
        payload=repair_case_payload,
        storage_service=storage_service_factory(),
        filename="repair_case.json",
    )
    return {
        "shadow_mode": True,
        "triage_kind": "replay_regression",
        "candidate_harness_name": payload.candidate_harness_name,
        "baseline_harness_name": payload.baseline_harness_name,
        "quality_candidate_count": len(quality_candidates),
        "top_quality_candidates": jsonable_encoder(top_candidates),
        "evaluation": jsonable_encoder(evaluation),
        "verification": verification_record.model_dump(mode="json"),
        "recommendation": triage_payload["recommendation"],
        "repair_case": repair_case_payload,
        "repair_case_artifact_id": str(repair_case_artifact.id),
        "repair_case_artifact_kind": repair_case_artifact.artifact_kind,
        "repair_case_artifact_path": repair_case_artifact.storage_path,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
    }
