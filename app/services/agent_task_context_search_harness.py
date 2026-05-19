from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.orm import Session

import app.services.agent_task_context_search_harness_drafting as drafting_owner
import app.services.agent_task_context_search_harness_triage as triage_owner
from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskVerification, SearchReplayRun
from app.schemas import agent_task_core as task_core
from app.schemas.agent_task_search_workflows import (
    EvaluateSearchHarnessTaskOutput,
    VerifySearchHarnessEvaluationTaskOutput,
)
from app.services.agent_task_context_registry import (
    AgentTaskContextBuilder,
    resolve_context_builder_registry,
)
from app.services.agent_task_context_resolvers import (
    resolve_required_dependency_task_output_context,
)
from app.services.agent_task_context_store import (
    derive_freshness_status,
    payload_sha256,
    search_harness_evaluation_context_ref,
    search_replay_run_payload,
    verification_payload,
)

SEARCH_HARNESS_CONTEXT_BUILDER_SYMBOLS = {
    "draft_harness_config": "_build_draft_harness_config_context",
    "evaluate_search_harness": "_build_evaluate_search_harness_context",
    "verify_search_harness_evaluation": "_build_verify_search_harness_evaluation_context",
    "verify_draft_harness_config": "_build_verify_draft_harness_config_context",
    "triage_replay_regression": "_build_triage_replay_regression_context",
    "apply_harness_config_update": "_build_apply_harness_config_update_context",
}

_build_draft_harness_config_context = drafting_owner._build_draft_harness_config_context
_build_verify_draft_harness_config_context = (
    drafting_owner._build_verify_draft_harness_config_context
)
_build_apply_harness_config_update_context = (
    drafting_owner._build_apply_harness_config_update_context
)
_build_triage_replay_regression_context = triage_owner._build_triage_replay_regression_context


def _build_evaluate_search_harness_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = EvaluateSearchHarnessTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    evaluation_ref = search_harness_evaluation_context_ref(
        session,
        output.evaluation.evaluation_id,
        now=now,
    )
    if evaluation_ref is not None:
        refs.append(evaluation_ref)

    for source in output.evaluation.sources:
        baseline_run = session.get(SearchReplayRun, source.baseline_replay_run_id)
        if baseline_run is not None:
            refs.append(
                task_core.ContextRef(
                    ref_key=f"{source.source_type}_baseline_replay_run",
                    ref_kind="replay_run",
                    summary=(
                        f"Baseline replay run for {source.source_type} using "
                        f"{output.baseline_harness_name}."
                    ),
                    replay_run_id=baseline_run.id,
                    observed_sha256=payload_sha256(search_replay_run_payload(baseline_run)),
                    source_updated_at=baseline_run.completed_at or baseline_run.created_at,
                    checked_at=now,
                    freshness_status=task_core.ContextFreshnessStatus.FRESH,
                )
            )
        candidate_run = session.get(SearchReplayRun, source.candidate_replay_run_id)
        if candidate_run is not None:
            refs.append(
                task_core.ContextRef(
                    ref_key=f"{source.source_type}_candidate_replay_run",
                    ref_kind="replay_run",
                    summary=(
                        f"Candidate replay run for {source.source_type} using "
                        f"{output.candidate_harness_name}."
                    ),
                    replay_run_id=candidate_run.id,
                    observed_sha256=payload_sha256(search_replay_run_payload(candidate_run)),
                    source_updated_at=candidate_run.completed_at or candidate_run.created_at,
                    checked_at=now,
                    freshness_status=task_core.ContextFreshnessStatus.FRESH,
                )
            )

    summary = task_core.TaskContextSummary(
        headline=(
            f"Evaluated {output.candidate_harness_name} against "
            f"{output.baseline_harness_name} across {len(output.evaluation.sources)} replay "
            "source type(s)."
        ),
        goal="Compare a candidate harness to a baseline without changing live search behavior.",
        decision=(
            "Review the evaluation deltas before deciding whether to run the verification gate."
        ),
        next_action="Create verify_search_harness_evaluation to enforce rollout thresholds.",
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "source_count": len(output.evaluation.sources),
            "total_shared_query_count": output.evaluation.total_shared_query_count,
            "total_improved_count": output.evaluation.total_improved_count,
            "total_regressed_count": output.evaluation.total_regressed_count,
        },
    )
    return task_core.TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=derive_freshness_status(refs) or task_core.ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_verify_search_harness_evaluation_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = VerifySearchHarnessEvaluationTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    target_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.verification.target_task_id,
        dependency_kind="target_task",
        expected_task_type="evaluate_search_harness",
        expected_schema_name="evaluate_search_harness_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Verification task must declare the requested evaluation task as a "
            "target_task dependency."
        ),
        rerun_message=(
            "Target evaluation task must be rerun after the context migration before it can "
            "be verified."
        ),
    )
    refs.append(
        task_core.ContextRef(
            ref_key="target_task_output",
            ref_kind="task_output",
            summary="Migrated evaluation output consumed by the rollout gate verifier.",
            task_id=target_context.task_id,
            schema_name=target_context.output_schema_name,
            schema_version=target_context.output_schema_version,
            observed_sha256=payload_sha256(target_context.output),
            source_updated_at=target_context.task_updated_at,
            checked_at=now,
            freshness_status=task_core.ContextFreshnessStatus.FRESH,
        )
    )
    evaluation_ref = search_harness_evaluation_context_ref(
        session,
        output.evaluation.evaluation_id,
        now=now,
    )
    if evaluation_ref is not None:
        refs.append(evaluation_ref)

    verification_row = session.get(AgentTaskVerification, output.verification.verification_id)
    if verification_row is not None:
        refs.append(
            task_core.ContextRef(
                ref_key="verification_record",
                ref_kind="verification_record",
                summary="Verifier record persisted for the evaluation rollout gate.",
                task_id=output.verification.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=payload_sha256(verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    thresholds = (output.verification.details or {}).get("thresholds") or {}
    summary = task_core.TaskContextSummary(
        headline=(
            f"Verified {output.evaluation.candidate_harness_name} against "
            f"{output.evaluation.baseline_harness_name} rollout thresholds."
        ),
        goal="Gate a harness evaluation before any follow-on rollout or draft action.",
        decision=(
            "Evaluation passed the rollout gate."
            if output.verification.outcome == "passed"
            else "Evaluation failed the rollout gate."
        ),
        next_action=(
            "Proceed with downstream review or rollout planning."
            if output.verification.outcome == "passed"
            else "Revise the harness or thresholds before retrying verification."
        ),
        approval_state="not_required",
        verification_state=output.verification.outcome,
        problem="; ".join(output.verification.reasons) if output.verification.reasons else None,
        evidence=(
            f"Thresholds: max_regressed={thresholds.get('max_total_regressed_count')}, "
            f"max_mrr_drop={thresholds.get('max_mrr_drop')}, "
            f"min_shared={thresholds.get('min_total_shared_query_count')}"
        ),
        metrics={
            "total_shared_query_count": output.evaluation.total_shared_query_count,
            "total_regressed_count": output.evaluation.total_regressed_count,
            "max_total_regressed_count": thresholds.get("max_total_regressed_count"),
            "max_mrr_drop": thresholds.get("max_mrr_drop"),
            "min_total_shared_query_count": thresholds.get("min_total_shared_query_count"),
        },
    )
    return task_core.TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=derive_freshness_status(refs) or task_core.ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def build_search_harness_context_builders(
    available_symbols: Mapping[str, object],
) -> dict[str, AgentTaskContextBuilder]:
    return resolve_context_builder_registry(
        {**dict(available_symbols), **globals()},
        builder_symbols=SEARCH_HARNESS_CONTEXT_BUILDER_SYMBOLS,
        registry_name="search_harness",
    )
