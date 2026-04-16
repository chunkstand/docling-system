from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import yaml
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskDependency,
    AgentTaskVerification,
    SearchReplayRun,
)
from app.schemas.agent_tasks import (
    ApplyHarnessConfigUpdateTaskOutput,
    ContextFreshnessStatus,
    ContextRef,
    DraftHarnessConfigUpdateTaskOutput,
    EvaluateSearchHarnessTaskOutput,
    TaskContextEnvelope,
    TaskContextSummary,
    VerifyDraftHarnessConfigTaskOutput,
    VerifySearchHarnessEvaluationTaskOutput,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.storage import StorageService


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _payload_sha256(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _derive_freshness_status(refs: list[ContextRef]) -> ContextFreshnessStatus | None:
    statuses = [row.freshness_status for row in refs if row.freshness_status is not None]
    if not statuses:
        return None
    if ContextFreshnessStatus.SCHEMA_MISMATCH in statuses:
        return ContextFreshnessStatus.SCHEMA_MISMATCH
    if ContextFreshnessStatus.MISSING in statuses:
        return ContextFreshnessStatus.MISSING
    if ContextFreshnessStatus.STALE in statuses:
        return ContextFreshnessStatus.STALE
    return ContextFreshnessStatus.FRESH


def _get_context_artifact_row(session: Session, task_id: UUID) -> AgentTaskArtifact | None:
    return (
        session.execute(
            select(AgentTaskArtifact)
            .where(
                AgentTaskArtifact.task_id == task_id,
                AgentTaskArtifact.artifact_kind == "context",
            )
            .order_by(AgentTaskArtifact.created_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )


def get_agent_task_context_artifact(session: Session, task_id: UUID) -> AgentTaskArtifact:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found.")
    row = _get_context_artifact_row(session, task_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent task context not found.",
        )
    return row


def get_agent_task_context(session: Session, task_id: UUID) -> TaskContextEnvelope:
    artifact = get_agent_task_context_artifact(session, task_id)
    envelope = TaskContextEnvelope.model_validate(artifact.payload_json or {})
    return refresh_task_context_freshness(session, envelope)


def get_agent_task_context_yaml_path(
    storage_service: StorageService,
    *,
    task_id: UUID,
) -> Path:
    return storage_service.get_agent_task_context_yaml_path(task_id)


def _verification_payload(row: AgentTaskVerification) -> dict:
    return {
        "verification_id": str(row.id),
        "target_task_id": str(row.target_task_id),
        "verification_task_id": (
            str(row.verification_task_id) if row.verification_task_id is not None else None
        ),
        "verifier_type": row.verifier_type,
        "outcome": row.outcome,
        "metrics": row.metrics_json or {},
        "reasons": row.reasons_json or [],
        "details": row.details_json or {},
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at is not None else None,
    }


def _search_replay_run_payload(row: SearchReplayRun) -> dict:
    return {
        "replay_run_id": str(row.id),
        "source_type": row.source_type,
        "status": row.status,
        "harness_name": row.harness_name,
        "reranker_name": row.reranker_name,
        "reranker_version": row.reranker_version,
        "retrieval_profile_name": row.retrieval_profile_name,
        "harness_config": row.harness_config_json or {},
        "query_count": row.query_count,
        "passed_count": row.passed_count,
        "failed_count": row.failed_count,
        "zero_result_count": row.zero_result_count,
        "table_hit_count": row.table_hit_count,
        "top_result_changes": row.top_result_changes,
        "max_rank_shift": row.max_rank_shift,
        "summary": row.summary_json or {},
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at is not None else None,
    }


def _refresh_context_ref(session: Session, ref: ContextRef) -> ContextRef:
    updated = ref.model_copy(deep=True)
    updated.checked_at = _utcnow()

    if ref.ref_kind == "task_output":
        if ref.task_id is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        task = session.get(AgentTask, ref.task_id)
        if task is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        from app.services.agent_task_actions import get_agent_task_action

        action = get_agent_task_action(task.task_type)
        if ref.schema_name and action.output_schema_name and ref.schema_name != action.output_schema_name:
            updated.freshness_status = ContextFreshnessStatus.SCHEMA_MISMATCH
            return updated
        if (
            ref.schema_version
            and action.output_schema_version
            and ref.schema_version != action.output_schema_version
        ):
            updated.freshness_status = ContextFreshnessStatus.SCHEMA_MISMATCH
            return updated
        if action.output_model is not None:
            source_context_row = _get_context_artifact_row(session, task.id)
            if source_context_row is None:
                updated.freshness_status = ContextFreshnessStatus.MISSING
                return updated
            source_context = TaskContextEnvelope.model_validate(source_context_row.payload_json or {})
            current_payload = source_context.output
        else:
            current_payload = task.result_json or {}
        current_hash = _payload_sha256(current_payload)
        if current_hash != ref.observed_sha256:
            updated.freshness_status = ContextFreshnessStatus.STALE
            return updated
        updated.freshness_status = ContextFreshnessStatus.FRESH
        updated.source_updated_at = task.updated_at
        return updated

    if ref.ref_kind == "artifact":
        if ref.artifact_id is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        artifact = session.get(AgentTaskArtifact, ref.artifact_id)
        if artifact is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        if ref.artifact_kind and artifact.artifact_kind != ref.artifact_kind:
            updated.freshness_status = ContextFreshnessStatus.SCHEMA_MISMATCH
            return updated
        current_hash = _payload_sha256(artifact.payload_json or {})
        if current_hash != ref.observed_sha256:
            updated.freshness_status = ContextFreshnessStatus.STALE
            return updated
        updated.freshness_status = ContextFreshnessStatus.FRESH
        updated.source_updated_at = artifact.created_at
        return updated

    if ref.ref_kind == "verification_record":
        if ref.verification_id is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        verification_row = session.get(AgentTaskVerification, ref.verification_id)
        if verification_row is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        current_hash = _payload_sha256(_verification_payload(verification_row))
        if current_hash != ref.observed_sha256:
            updated.freshness_status = ContextFreshnessStatus.STALE
            return updated
        updated.freshness_status = ContextFreshnessStatus.FRESH
        updated.source_updated_at = verification_row.completed_at or verification_row.created_at
        return updated

    if ref.ref_kind == "replay_run":
        if ref.replay_run_id is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        replay_run = session.get(SearchReplayRun, ref.replay_run_id)
        if replay_run is None:
            updated.freshness_status = ContextFreshnessStatus.MISSING
            return updated
        current_hash = _payload_sha256(_search_replay_run_payload(replay_run))
        if current_hash != ref.observed_sha256:
            updated.freshness_status = ContextFreshnessStatus.STALE
            return updated
        updated.freshness_status = ContextFreshnessStatus.FRESH
        updated.source_updated_at = replay_run.completed_at or replay_run.created_at
        return updated

    updated.freshness_status = ref.freshness_status or ContextFreshnessStatus.FRESH
    return updated


def refresh_task_context_freshness(
    session: Session,
    envelope: TaskContextEnvelope,
) -> TaskContextEnvelope:
    refreshed_refs = [_refresh_context_ref(session, ref) for ref in envelope.refs]
    refreshed = envelope.model_copy(deep=True)
    refreshed.refs = refreshed_refs
    refreshed.freshness_status = _derive_freshness_status(refreshed_refs)
    return refreshed


def resolve_required_task_output_context(
    session: Session,
    *,
    task_id: UUID,
    expected_task_type: str,
    expected_schema_name: str,
    expected_schema_version: str,
    rerun_message: str,
) -> TaskContextEnvelope:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target task not found: {task_id}")
    if task.task_type != expected_task_type:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Target task must be a {expected_task_type} task.",
        )
    if task.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Target task must be completed before it can be consumed.",
        )
    context_row = _get_context_artifact_row(session, task.id)
    if context_row is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=rerun_message)
    context = refresh_task_context_freshness(
        session,
        TaskContextEnvelope.model_validate(context_row.payload_json or {}),
    )
    if context.output_schema_name != expected_schema_name:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=rerun_message)
    if context.output_schema_version != expected_schema_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=rerun_message)
    return context


def resolve_required_dependency_task_output_context(
    session: Session,
    *,
    task_id: UUID,
    depends_on_task_id: UUID,
    dependency_kind: str,
    expected_task_type: str,
    expected_schema_name: str,
    expected_schema_version: str,
    dependency_error_message: str,
    rerun_message: str,
) -> TaskContextEnvelope:
    dependency_row = (
        session.execute(
            select(AgentTaskDependency)
            .where(
                AgentTaskDependency.task_id == task_id,
                AgentTaskDependency.depends_on_task_id == depends_on_task_id,
            )
            .limit(1)
        )
        .scalars()
        .first()
    )
    if dependency_row is None or dependency_row.dependency_kind != dependency_kind:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=dependency_error_message)
    return resolve_required_task_output_context(
        session,
        task_id=depends_on_task_id,
        expected_task_type=expected_task_type,
        expected_schema_name=expected_schema_name,
        expected_schema_version=expected_schema_version,
        rerun_message=rerun_message,
    )


def _build_draft_harness_config_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = DraftHarnessConfigUpdateTaskOutput.model_validate(payload)
    now = _utcnow()
    refs: list[ContextRef] = []

    if output.draft.source_task_id is not None:
        source_task = session.get(AgentTask, output.draft.source_task_id)
        if source_task is not None:
            from app.services.agent_task_actions import get_agent_task_action

            source_action = get_agent_task_action(source_task.task_type)
            source_context_row = _get_context_artifact_row(session, source_task.id)
            if source_context_row is not None:
                source_context = TaskContextEnvelope.model_validate(source_context_row.payload_json or {})
                observed_payload = source_context.output
            else:
                observed_payload = source_task.result_json or {}
            refs.append(
                ContextRef(
                    ref_key="source_task",
                    ref_kind="task_output",
                    summary="Source task that motivated this harness draft.",
                    task_id=source_task.id,
                    schema_name=source_action.output_schema_name,
                    schema_version=source_action.output_schema_version,
                    observed_sha256=_payload_sha256(observed_payload),
                    source_updated_at=source_task.updated_at,
                    checked_at=now,
                    freshness_status=ContextFreshnessStatus.FRESH,
                )
            )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="draft_artifact",
                ref_kind="artifact",
                summary="Persisted draft-harness artifact for operator review.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=_payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    summary = TaskContextSummary(
        headline=(
            f"Draft harness {output.draft.draft_harness_name} derived from "
            f"{output.draft.base_harness_name}."
        ),
        goal=output.draft.rationale or "Create a review harness without changing live search.",
        decision="Draft created and ready for verification.",
        next_action="Run verify_draft_harness_config against replay evidence.",
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "has_source_task": output.draft.source_task_id is not None,
            "retrieval_override_count": len(output.draft.override_spec.retrieval_profile_overrides),
            "reranker_override_count": len(output.draft.override_spec.reranker_overrides),
        },
    )
    return TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=_derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_evaluate_search_harness_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = EvaluateSearchHarnessTaskOutput.model_validate(payload)
    now = _utcnow()
    refs: list[ContextRef] = []

    for source in output.evaluation.sources:
        baseline_run = session.get(SearchReplayRun, source.baseline_replay_run_id)
        if baseline_run is not None:
            refs.append(
                ContextRef(
                    ref_key=f"{source.source_type}_baseline_replay_run",
                    ref_kind="replay_run",
                    summary=(
                        f"Baseline replay run for {source.source_type} using "
                        f"{output.baseline_harness_name}."
                    ),
                    replay_run_id=baseline_run.id,
                    observed_sha256=_payload_sha256(_search_replay_run_payload(baseline_run)),
                    source_updated_at=baseline_run.completed_at or baseline_run.created_at,
                    checked_at=now,
                    freshness_status=ContextFreshnessStatus.FRESH,
                )
            )
        candidate_run = session.get(SearchReplayRun, source.candidate_replay_run_id)
        if candidate_run is not None:
            refs.append(
                ContextRef(
                    ref_key=f"{source.source_type}_candidate_replay_run",
                    ref_kind="replay_run",
                    summary=(
                        f"Candidate replay run for {source.source_type} using "
                        f"{output.candidate_harness_name}."
                    ),
                    replay_run_id=candidate_run.id,
                    observed_sha256=_payload_sha256(_search_replay_run_payload(candidate_run)),
                    source_updated_at=candidate_run.completed_at or candidate_run.created_at,
                    checked_at=now,
                    freshness_status=ContextFreshnessStatus.FRESH,
                )
            )

    summary = TaskContextSummary(
        headline=(
            f"Evaluated {output.candidate_harness_name} against "
            f"{output.baseline_harness_name} across {len(output.evaluation.sources)} replay "
            "source type(s)."
        ),
        goal="Compare a candidate harness to a baseline without changing live search behavior.",
        decision="Review the evaluation deltas before deciding whether to run the verification gate.",
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
    return TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=_derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_verify_draft_harness_config_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = VerifyDraftHarnessConfigTaskOutput.model_validate(payload)
    now = _utcnow()
    refs: list[ContextRef] = []

    draft_context = resolve_required_task_output_context(
        session,
        task_id=output.verification.target_task_id,
        expected_task_type="draft_harness_config_update",
        expected_schema_name="draft_harness_config_update_output",
        expected_schema_version="1.0",
        rerun_message=(
            "Target draft task must be rerun after the context migration before it can be "
            "verified."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="draft_task_output",
            ref_kind="task_output",
            summary="Migrated draft-harness output consumed by this verification.",
            task_id=draft_context.task_id,
            schema_name=draft_context.output_schema_name,
            schema_version=draft_context.output_schema_version,
            observed_sha256=_payload_sha256(draft_context.output),
            source_updated_at=draft_context.task_updated_at,
            checked_at=now,
            freshness_status=ContextFreshnessStatus.FRESH,
        )
    )

    for ref in draft_context.refs:
        if ref.ref_key != "draft_artifact":
            continue
        refs.append(
            ContextRef(
                ref_key="draft_artifact",
                ref_kind="artifact",
                summary="Persisted draft artifact used as verification evidence.",
                task_id=ref.task_id,
                artifact_id=ref.artifact_id,
                artifact_kind=ref.artifact_kind,
                schema_name=ref.schema_name,
                schema_version=ref.schema_version,
                observed_sha256=ref.observed_sha256,
                source_updated_at=ref.source_updated_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )
        break

    verification_row = session.get(AgentTaskVerification, output.verification.verification_id)
    if verification_row is not None:
        refs.append(
            ContextRef(
                ref_key="verification_record",
                ref_kind="verification_record",
                summary="Verifier record persisted for the draft review gate.",
                task_id=output.verification.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=_payload_sha256(_verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    verification_outcome = output.verification.outcome
    summary = TaskContextSummary(
        headline=(
            f"Verified draft harness {output.draft.draft_harness_name} against "
            f"{output.evaluation.get('baseline_harness_name') or output.draft.base_harness_name}."
        ),
        goal="Evaluate the draft harness before any approval-gated apply step.",
        decision=(
            "Verification passed; draft can move to apply review."
            if verification_outcome == "passed"
            else "Verification failed; revise the draft before applying."
        ),
        next_action=(
            "Create apply_harness_config_update if the operator wants to publish the draft."
            if verification_outcome == "passed"
            else "Revise the draft harness and rerun verification."
        ),
        approval_state="not_required",
        verification_state=verification_outcome,
        metrics={
            "total_shared_query_count": (output.verification.metrics or {}).get(
                "total_shared_query_count"
            ),
            "regressed_count": output.evaluation.get("total_regressed_count"),
            "improved_count": output.evaluation.get("total_improved_count"),
        },
    )
    return TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=_derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
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
) -> TaskContextEnvelope:
    output = VerifySearchHarnessEvaluationTaskOutput.model_validate(payload)
    now = _utcnow()
    refs: list[ContextRef] = []

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
        ContextRef(
            ref_key="target_task_output",
            ref_kind="task_output",
            summary="Migrated evaluation output consumed by the rollout gate verifier.",
            task_id=target_context.task_id,
            schema_name=target_context.output_schema_name,
            schema_version=target_context.output_schema_version,
            observed_sha256=_payload_sha256(target_context.output),
            source_updated_at=target_context.task_updated_at,
            checked_at=now,
            freshness_status=ContextFreshnessStatus.FRESH,
        )
    )

    verification_row = session.get(AgentTaskVerification, output.verification.verification_id)
    if verification_row is not None:
        refs.append(
            ContextRef(
                ref_key="verification_record",
                ref_kind="verification_record",
                summary="Verifier record persisted for the evaluation rollout gate.",
                task_id=output.verification.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=_payload_sha256(_verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    thresholds = (output.verification.details or {}).get("thresholds") or {}
    summary = TaskContextSummary(
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
        metrics={
            "total_shared_query_count": output.evaluation.total_shared_query_count,
            "total_regressed_count": output.evaluation.total_regressed_count,
            "max_total_regressed_count": thresholds.get("max_total_regressed_count"),
            "max_mrr_drop": thresholds.get("max_mrr_drop"),
            "min_total_shared_query_count": thresholds.get("min_total_shared_query_count"),
        },
    )
    return TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=_derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_apply_harness_config_update_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = ApplyHarnessConfigUpdateTaskOutput.model_validate(payload)
    now = _utcnow()
    refs: list[ContextRef] = []

    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.draft_task_id,
        dependency_kind="draft_task",
        expected_task_type="draft_harness_config_update",
        expected_schema_name="draft_harness_config_update_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply task must declare the requested draft task as a draft_task dependency."
        ),
        rerun_message=(
            "Draft task must be rerun after the context migration before it can be applied."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="draft_task_output",
            ref_kind="task_output",
            summary="Migrated draft-harness output applied to the live override store.",
            task_id=draft_context.task_id,
            schema_name=draft_context.output_schema_name,
            schema_version=draft_context.output_schema_version,
            observed_sha256=_payload_sha256(draft_context.output),
            source_updated_at=draft_context.task_updated_at,
            checked_at=now,
            freshness_status=ContextFreshnessStatus.FRESH,
        )
    )

    verification_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.verification_task_id,
        dependency_kind="verification_task",
        expected_task_type="verify_draft_harness_config",
        expected_schema_name="verify_draft_harness_config_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply task must declare the requested verification task as a "
            "verification_task dependency."
        ),
        rerun_message=(
            "Verification task must be rerun after the context migration before it can be "
            "applied."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="verification_task_output",
            ref_kind="task_output",
            summary="Migrated verification output that approved this live apply step.",
            task_id=verification_context.task_id,
            schema_name=verification_context.output_schema_name,
            schema_version=verification_context.output_schema_version,
            observed_sha256=_payload_sha256(verification_context.output),
            source_updated_at=verification_context.task_updated_at,
            checked_at=now,
            freshness_status=ContextFreshnessStatus.FRESH,
        )
    )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="applied_artifact",
                ref_kind="artifact",
                summary="Persisted apply artifact for the live harness override.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=_payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    verification_output = VerifyDraftHarnessConfigTaskOutput.model_validate(verification_context.output)
    summary = TaskContextSummary(
        headline=f"Applied verified harness {output.draft_harness_name} to live search.",
        goal="Publish a verified draft harness after approval without changing the workflow model.",
        decision="Live override written and ready for post-apply monitoring.",
        next_action=(
            f"Monitor search traffic and run follow-up evaluation for {output.draft_harness_name}."
        ),
        approval_state="approved" if task.approved_at is not None else "pending",
        verification_state=verification_output.verification.outcome,
        metrics={
            "total_shared_query_count": (verification_output.verification.metrics or {}).get(
                "total_shared_query_count"
            ),
            "regressed_count": verification_output.evaluation.get("total_regressed_count"),
            "improved_count": verification_output.evaluation.get("total_improved_count"),
        },
    )
    return TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=_derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_generic_task_context(task: AgentTask, payload: dict, *, action) -> TaskContextEnvelope:
    now = _utcnow()
    return TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=ContextFreshnessStatus.FRESH,
        summary=TaskContextSummary(
            headline=f"{task.task_type} produced typed output.",
            decision="Output captured as typed context.",
        ),
        refs=[],
        output=payload,
    )


def build_agent_task_context(
    session: Session,
    task: AgentTask,
    result: dict,
) -> TaskContextEnvelope | None:
    from app.services.agent_task_actions import get_agent_task_action

    action = get_agent_task_action(task.task_type)
    if action.output_model is None:
        return None

    payload = (result or {}).get("payload") or {}
    if task.task_type == "draft_harness_config_update":
        return _build_draft_harness_config_context(session, task, payload, action=action)
    if task.task_type == "evaluate_search_harness":
        return _build_evaluate_search_harness_context(session, task, payload, action=action)
    if task.task_type == "verify_search_harness_evaluation":
        return _build_verify_search_harness_evaluation_context(
            session,
            task,
            payload,
            action=action,
        )
    if task.task_type == "verify_draft_harness_config":
        return _build_verify_draft_harness_config_context(session, task, payload, action=action)
    if task.task_type == "apply_harness_config_update":
        return _build_apply_harness_config_update_context(session, task, payload, action=action)
    return _build_generic_task_context(task, payload, action=action)


def write_agent_task_context(
    session: Session,
    task: AgentTask,
    result: dict,
    *,
    storage_service: StorageService,
) -> AgentTaskArtifact | None:
    envelope = build_agent_task_context(session, task, result)
    if envelope is None:
        return None

    envelope.task_status = "completed"
    envelope.task_updated_at = _utcnow()
    payload = envelope.model_dump(mode="json")
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="context",
        payload=payload,
        storage_service=storage_service,
        filename="context.json",
    )
    yaml_path = storage_service.get_agent_task_context_yaml_path(task.id)
    yaml_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    return artifact
