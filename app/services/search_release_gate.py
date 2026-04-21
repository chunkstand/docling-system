from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.db.models import AgentTaskVerificationOutcome, SearchReplayRun
from app.schemas.agent_tasks import VerifySearchHarnessEvaluationTaskInput
from app.schemas.search import SearchHarnessEvaluationResponse


@dataclass(frozen=True)
class SearchHarnessReleaseGateOutcome:
    outcome: str
    metrics: dict
    reasons: list[str]
    details: dict


def _rank_metrics(row: SearchReplayRun) -> dict:
    return (row.summary_json or {}).get("rank_metrics") or {}


def _load_replay_run(
    session: Session,
    replay_run_id: UUID,
    *,
    label: str,
) -> SearchReplayRun | None:
    replay_run = session.get(SearchReplayRun, replay_run_id)
    if replay_run is None:
        return None
    if replay_run.status != "completed":
        msg = f"{label} replay run {replay_run_id} is not completed."
        raise api_error(
            409,
            "search_replay_run_not_completed",
            msg,
            replay_run_id=str(replay_run_id),
            replay_run_status=replay_run.status,
            label=label,
        )
    return replay_run


def evaluate_search_harness_release_gate(
    session: Session,
    evaluation: SearchHarnessEvaluationResponse,
    payload: VerifySearchHarnessEvaluationTaskInput,
) -> SearchHarnessReleaseGateOutcome:
    reasons: list[str] = []
    per_source: dict[str, dict] = {}
    max_observed_mrr_drop = 0.0
    max_observed_zero_result_increase = 0
    max_observed_foreign_top_result_increase = 0

    if evaluation.status != "completed":
        reasons.append(
            f"search harness evaluation {evaluation.evaluation_id or 'unknown'} "
            f"is {evaluation.status}."
        )

    for source in evaluation.sources:
        baseline_run = _load_replay_run(
            session,
            source.baseline_replay_run_id,
            label=f"{source.source_type} baseline",
        )
        candidate_run = _load_replay_run(
            session,
            source.candidate_replay_run_id,
            label=f"{source.source_type} candidate",
        )
        if baseline_run is None or candidate_run is None:
            missing = "baseline" if baseline_run is None else "candidate"
            reasons.append(f"{source.source_type}: {missing} replay run is missing.")
            continue

        baseline_rank_metrics = _rank_metrics(baseline_run)
        candidate_rank_metrics = _rank_metrics(candidate_run)
        baseline_mrr = float(baseline_rank_metrics.get("mrr") or 0.0)
        candidate_mrr = float(candidate_rank_metrics.get("mrr") or 0.0)
        mrr_drop = max(0.0, baseline_mrr - candidate_mrr)
        zero_result_increase = max(
            0,
            candidate_run.zero_result_count - baseline_run.zero_result_count,
        )
        foreign_top_result_increase = max(
            0,
            int(candidate_rank_metrics.get("foreign_top_result_count") or 0)
            - int(baseline_rank_metrics.get("foreign_top_result_count") or 0),
        )
        max_observed_mrr_drop = max(max_observed_mrr_drop, mrr_drop)
        max_observed_zero_result_increase = max(
            max_observed_zero_result_increase,
            zero_result_increase,
        )
        max_observed_foreign_top_result_increase = max(
            max_observed_foreign_top_result_increase,
            foreign_top_result_increase,
        )
        per_source[source.source_type] = {
            "baseline_replay_run_id": str(baseline_run.id),
            "candidate_replay_run_id": str(candidate_run.id),
            "shared_query_count": source.shared_query_count,
            "regressed_count": source.regressed_count,
            "baseline_mrr": baseline_mrr,
            "candidate_mrr": candidate_mrr,
            "mrr_drop": mrr_drop,
            "baseline_zero_result_count": baseline_run.zero_result_count,
            "candidate_zero_result_count": candidate_run.zero_result_count,
            "zero_result_count_increase": zero_result_increase,
            "foreign_top_result_count_increase": foreign_top_result_increase,
        }

        if source.regressed_count > payload.max_total_regressed_count:
            reasons.append(
                f"{source.source_type}: regressed_count {source.regressed_count} exceeds "
                f"{payload.max_total_regressed_count}."
            )
        if mrr_drop > payload.max_mrr_drop:
            reasons.append(
                f"{source.source_type}: mrr_drop {mrr_drop:.6f} exceeds {payload.max_mrr_drop:.6f}."
            )
        if zero_result_increase > payload.max_zero_result_count_increase:
            reasons.append(
                f"{source.source_type}: zero_result_count_increase {zero_result_increase} exceeds "
                f"{payload.max_zero_result_count_increase}."
            )
        if foreign_top_result_increase > payload.max_foreign_top_result_count_increase:
            reasons.append(
                f"{source.source_type}: foreign_top_result_count_increase "
                f"{foreign_top_result_increase} exceeds "
                f"{payload.max_foreign_top_result_count_increase}."
            )

    if evaluation.total_shared_query_count < payload.min_total_shared_query_count:
        reasons.append(
            "total_shared_query_count "
            f"{evaluation.total_shared_query_count} is below "
            f"{payload.min_total_shared_query_count}."
        )

    metrics = {
        "source_count": len(evaluation.sources),
        "total_shared_query_count": evaluation.total_shared_query_count,
        "total_improved_count": evaluation.total_improved_count,
        "total_regressed_count": evaluation.total_regressed_count,
        "total_unchanged_count": evaluation.total_unchanged_count,
        "max_observed_mrr_drop": max_observed_mrr_drop,
        "max_observed_zero_result_count_increase": max_observed_zero_result_increase,
        "max_observed_foreign_top_result_count_increase": (
            max_observed_foreign_top_result_increase
        ),
    }
    details = {
        "evaluation_id": str(evaluation.evaluation_id) if evaluation.evaluation_id else None,
        "evaluation_status": evaluation.status,
        "candidate_harness_name": evaluation.candidate_harness_name,
        "baseline_harness_name": evaluation.baseline_harness_name,
        "per_source": per_source,
        "thresholds": payload.model_dump(mode="json"),
    }
    outcome = (
        AgentTaskVerificationOutcome.PASSED.value
        if not reasons
        else AgentTaskVerificationOutcome.FAILED.value
    )
    return SearchHarnessReleaseGateOutcome(
        outcome=outcome,
        metrics=metrics,
        reasons=reasons,
        details=details,
    )
