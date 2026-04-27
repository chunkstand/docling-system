from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.time import utcnow
from app.db.models import AgentTaskVerificationOutcome, SearchHarnessRelease, SearchReplayRun
from app.schemas.search import (
    SearchHarnessEvaluationResponse,
    SearchHarnessReleaseGateRequest,
    SearchHarnessReleaseResponse,
    SearchHarnessReleaseSummaryResponse,
)
from app.services.search_harness_evaluations import get_search_harness_evaluation_detail


@dataclass(frozen=True)
class SearchHarnessReleaseGateOutcome:
    outcome: str
    metrics: dict
    reasons: list[str]
    details: dict


class SearchHarnessReleaseGateThresholds(Protocol):
    max_total_regressed_count: int
    max_mrr_drop: float
    max_zero_result_count_increase: int
    max_foreign_top_result_count_increase: int
    min_total_shared_query_count: int


def _search_harness_release_not_found(release_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "search_harness_release_not_found",
        "Search harness release gate not found.",
        release_id=str(release_id),
    )


def _thresholds_dict(payload: SearchHarnessReleaseGateThresholds) -> dict:
    return {
        "max_total_regressed_count": payload.max_total_regressed_count,
        "max_mrr_drop": payload.max_mrr_drop,
        "max_zero_result_count_increase": payload.max_zero_result_count_increase,
        "max_foreign_top_result_count_increase": (
            payload.max_foreign_top_result_count_increase
        ),
        "min_total_shared_query_count": payload.min_total_shared_query_count,
    }


def _payload_sha256(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _error_detail(exc: HTTPException) -> dict:
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return {
        "status_code": exc.status_code,
        "code": detail.get("code") or detail.get("error_code") or "search_harness_release_error",
        "message": detail.get("message") or detail.get("detail") or str(exc.detail),
        "context": detail.get("context") or detail.get("error_context") or {},
    }


def _error_release_gate_outcome(
    evaluation: SearchHarnessEvaluationResponse,
    payload: SearchHarnessReleaseGateThresholds,
    exc: HTTPException,
) -> SearchHarnessReleaseGateOutcome:
    error = _error_detail(exc)
    metrics = {
        "source_count": len(evaluation.sources),
        "total_shared_query_count": evaluation.total_shared_query_count,
        "total_improved_count": evaluation.total_improved_count,
        "total_regressed_count": evaluation.total_regressed_count,
        "total_unchanged_count": evaluation.total_unchanged_count,
        "max_observed_mrr_drop": 0.0,
        "max_observed_zero_result_count_increase": 0,
        "max_observed_foreign_top_result_count_increase": 0,
    }
    details = {
        "evaluation_id": str(evaluation.evaluation_id) if evaluation.evaluation_id else None,
        "evaluation_status": evaluation.status,
        "candidate_harness_name": evaluation.candidate_harness_name,
        "baseline_harness_name": evaluation.baseline_harness_name,
        "per_source": {},
        "thresholds": _thresholds_dict(payload),
        "error": error,
    }
    return SearchHarnessReleaseGateOutcome(
        outcome=AgentTaskVerificationOutcome.ERROR.value,
        metrics=metrics,
        reasons=[error["message"]],
        details=details,
    )


def _to_release_summary(row: SearchHarnessRelease) -> SearchHarnessReleaseSummaryResponse:
    return SearchHarnessReleaseSummaryResponse(
        release_id=row.id,
        evaluation_id=row.search_harness_evaluation_id,
        outcome=row.outcome,
        baseline_harness_name=row.baseline_harness_name,
        candidate_harness_name=row.candidate_harness_name,
        limit=row.limit,
        source_types=list(row.source_types_json or []),
        thresholds=row.thresholds_json or {},
        metrics=row.metrics_json or {},
        reasons=list(row.reasons_json or []),
        release_package_sha256=row.release_package_sha256,
        requested_by=row.requested_by,
        review_note=row.review_note,
        created_at=row.created_at,
    )


def _to_release_response(row: SearchHarnessRelease) -> SearchHarnessReleaseResponse:
    return SearchHarnessReleaseResponse(
        **_to_release_summary(row).model_dump(),
        details=row.details_json or {},
        evaluation_snapshot=row.evaluation_snapshot_json or {},
    )


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
    payload: SearchHarnessReleaseGateThresholds,
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
        "thresholds": _thresholds_dict(payload),
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


def record_search_harness_release_gate(
    session: Session,
    evaluation: SearchHarnessEvaluationResponse,
    payload: SearchHarnessReleaseGateThresholds,
    *,
    requested_by: str | None = None,
    review_note: str | None = None,
) -> SearchHarnessReleaseResponse:
    if evaluation.evaluation_id is None:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "search_harness_evaluation_missing_id",
            "Cannot create a release gate for an evaluation without a durable evaluation_id.",
        )

    try:
        gate = evaluate_search_harness_release_gate(session, evaluation, payload)
    except HTTPException as exc:
        gate = _error_release_gate_outcome(evaluation, payload, exc)
    thresholds = _thresholds_dict(payload)
    evaluation_snapshot = evaluation.model_dump(mode="json")
    release_package = {
        "schema_name": "search_harness_release_package",
        "schema_version": "1.0",
        "evaluation": evaluation_snapshot,
        "gate": {
            "outcome": gate.outcome,
            "metrics": gate.metrics,
            "reasons": gate.reasons,
            "details": gate.details,
        },
        "thresholds": thresholds,
    }
    release = SearchHarnessRelease(
        id=uuid.uuid4(),
        search_harness_evaluation_id=evaluation.evaluation_id,
        outcome=gate.outcome,
        baseline_harness_name=evaluation.baseline_harness_name,
        candidate_harness_name=evaluation.candidate_harness_name,
        limit=evaluation.limit,
        source_types_json=list(evaluation.source_types),
        thresholds_json=thresholds,
        metrics_json=gate.metrics,
        reasons_json=list(gate.reasons),
        details_json=gate.details,
        evaluation_snapshot_json=evaluation_snapshot,
        release_package_sha256=_payload_sha256(release_package),
        requested_by=requested_by,
        review_note=review_note,
        created_at=utcnow(),
    )
    session.add(release)
    session.flush()
    return _to_release_response(release)


def create_search_harness_release_gate(
    session: Session,
    payload: SearchHarnessReleaseGateRequest,
) -> SearchHarnessReleaseResponse:
    evaluation = get_search_harness_evaluation_detail(session, payload.evaluation_id)
    return record_search_harness_release_gate(
        session,
        evaluation,
        payload,
        requested_by=payload.requested_by,
        review_note=payload.review_note,
    )


def list_search_harness_releases(
    session: Session,
    *,
    limit: int = 20,
    candidate_harness_name: str | None = None,
    outcome: str | None = None,
) -> list[SearchHarnessReleaseSummaryResponse]:
    statement = select(SearchHarnessRelease).order_by(SearchHarnessRelease.created_at.desc())
    if candidate_harness_name:
        statement = statement.where(
            SearchHarnessRelease.candidate_harness_name == candidate_harness_name
        )
    if outcome:
        statement = statement.where(SearchHarnessRelease.outcome == outcome)
    rows = session.execute(statement.limit(limit)).scalars().all()
    return [_to_release_summary(row) for row in rows]


def get_search_harness_release_detail(
    session: Session,
    release_id: UUID,
) -> SearchHarnessReleaseResponse:
    release = session.get(SearchHarnessRelease, release_id)
    if release is None:
        raise _search_harness_release_not_found(release_id)
    return _to_release_response(release)
