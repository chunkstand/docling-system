from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import UUID

import yaml
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskDependency,
    AgentTaskVerification,
    SearchReplayRun,
)
from app.schemas.agent_tasks import (
    ApplyHarnessConfigUpdateTaskOutput,
    ApplySemanticRegistryUpdateTaskOutput,
    ContextFreshnessStatus,
    ContextRef,
    DraftHarnessConfigUpdateTaskOutput,
    DraftSemanticGroundedDocumentTaskOutput,
    DraftSemanticRegistryUpdateTaskOutput,
    EvaluateSearchHarnessTaskOutput,
    LatestSemanticPassTaskOutput,
    PrepareSemanticGenerationBriefTaskOutput,
    TaskContextEnvelope,
    TaskContextSummary,
    TriageReplayRegressionTaskOutput,
    TriageSemanticPassTaskOutput,
    VerifyDraftHarnessConfigTaskOutput,
    VerifyDraftSemanticRegistryUpdateTaskOutput,
    VerifySearchHarnessEvaluationTaskOutput,
    VerifySemanticGroundedDocumentTaskOutput,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.storage import StorageService


def _payload_sha256(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
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
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "agent_task_not_found",
            "Agent task not found.",
            task_id=str(task_id),
        )
    row = _get_context_artifact_row(session, task_id)
    if row is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "agent_task_context_not_found",
            "Agent task context not found.",
            task_id=str(task_id),
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
    updated.checked_at = utcnow()

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
        if (
            ref.schema_name
            and action.output_schema_name
            and ref.schema_name != action.output_schema_name
        ):
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
            source_context = TaskContextEnvelope.model_validate(
                source_context_row.payload_json or {}
            )
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


def _target_task_not_found(task_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "agent_task_context_target_task_not_found",
        "Target task not found.",
        task_id=str(task_id),
    )


def _target_task_type_mismatch(
    task_id: UUID,
    *,
    expected_task_type: str,
    actual_task_type: str,
) -> HTTPException:
    return api_error(
        status.HTTP_409_CONFLICT,
        "agent_task_context_target_task_type_mismatch",
        f"Target task must be a {expected_task_type} task.",
        task_id=str(task_id),
        expected_task_type=expected_task_type,
        actual_task_type=actual_task_type,
    )


def _target_task_not_completed(task_id: UUID, *, task_status: str | None) -> HTTPException:
    return api_error(
        status.HTTP_409_CONFLICT,
        "agent_task_context_target_task_not_completed",
        "Target task must be completed before it can be consumed.",
        task_id=str(task_id),
        task_status=task_status,
    )


def _rerun_required(
    code: str,
    *,
    task_id: UUID,
    message: str,
    expected_schema_name: str,
    expected_schema_version: str,
    actual_schema_name: str | None = None,
    actual_schema_version: str | None = None,
) -> HTTPException:
    return api_error(
        status.HTTP_409_CONFLICT,
        code,
        message,
        task_id=str(task_id),
        expected_schema_name=expected_schema_name,
        expected_schema_version=expected_schema_version,
        actual_schema_name=actual_schema_name,
        actual_schema_version=actual_schema_version,
    )


def _dependency_mismatch(
    *,
    task_id: UUID,
    depends_on_task_id: UUID,
    expected_dependency_kind: str,
    actual_dependency_kind: str | None,
    message: str,
) -> HTTPException:
    return api_error(
        status.HTTP_409_CONFLICT,
        "agent_task_context_dependency_mismatch",
        message,
        task_id=str(task_id),
        depends_on_task_id=str(depends_on_task_id),
        expected_dependency_kind=expected_dependency_kind,
        actual_dependency_kind=actual_dependency_kind,
    )


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
        raise _target_task_not_found(task_id)
    if task.task_type != expected_task_type:
        raise _target_task_type_mismatch(
            task_id,
            expected_task_type=expected_task_type,
            actual_task_type=task.task_type,
        )
    if task.status != "completed":
        raise _target_task_not_completed(task_id, task_status=task.status)
    context_row = _get_context_artifact_row(session, task.id)
    if context_row is None:
        raise _rerun_required(
            "agent_task_context_output_missing",
            task_id=task.id,
            message=rerun_message,
            expected_schema_name=expected_schema_name,
            expected_schema_version=expected_schema_version,
        )
    context = refresh_task_context_freshness(
        session,
        TaskContextEnvelope.model_validate(context_row.payload_json or {}),
    )
    if context.output_schema_name != expected_schema_name:
        raise _rerun_required(
            "agent_task_context_output_schema_mismatch",
            task_id=task.id,
            message=rerun_message,
            expected_schema_name=expected_schema_name,
            expected_schema_version=expected_schema_version,
            actual_schema_name=context.output_schema_name,
            actual_schema_version=context.output_schema_version,
        )
    if context.output_schema_version != expected_schema_version:
        raise _rerun_required(
            "agent_task_context_output_schema_version_mismatch",
            task_id=task.id,
            message=rerun_message,
            expected_schema_name=expected_schema_name,
            expected_schema_version=expected_schema_version,
            actual_schema_name=context.output_schema_name,
            actual_schema_version=context.output_schema_version,
        )
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
        raise _dependency_mismatch(
            task_id=task_id,
            depends_on_task_id=depends_on_task_id,
            expected_dependency_kind=dependency_kind,
            actual_dependency_kind=(
                dependency_row.dependency_kind if dependency_row is not None else None
            ),
            message=dependency_error_message,
        )
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
    now = utcnow()
    refs: list[ContextRef] = []

    if output.draft.source_task_id is not None:
        source_task = session.get(AgentTask, output.draft.source_task_id)
        if source_task is not None:
            from app.services.agent_task_actions import get_agent_task_action

            source_action = get_agent_task_action(source_task.task_type)
            source_context_row = _get_context_artifact_row(session, source_task.id)
            if source_context_row is not None:
                source_context = TaskContextEnvelope.model_validate(
                    source_context_row.payload_json or {}
                )
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


def _build_draft_semantic_registry_update_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = DraftSemanticRegistryUpdateTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    source_task = session.get(AgentTask, output.draft.source_task_id)
    if source_task is not None:
        from app.services.agent_task_actions import get_agent_task_action

        source_action = get_agent_task_action(source_task.task_type)
        source_context_row = _get_context_artifact_row(session, source_task.id)
        observed_payload = (
            TaskContextEnvelope.model_validate(source_context_row.payload_json or {}).output
            if source_context_row is not None
            else source_task.result_json or {}
        )
        refs.append(
            ContextRef(
                ref_key="source_task",
                ref_kind="task_output",
                summary="Semantic triage task that motivated this registry draft.",
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
                summary="Persisted semantic registry draft artifact for operator review.",
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
            f"Draft semantic registry {output.draft.proposed_registry_version} from "
            f"{output.draft.base_registry_version}."
        ),
        goal="Draft additive registry updates without mutating the live semantic contract.",
        decision="Draft created and ready for read-only verification.",
        next_action="Run verify_draft_semantic_registry_update against active documents.",
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "document_count": len(output.draft.document_ids),
            "operation_count": len(output.draft.operations),
            "success_metric_pass_count": sum(
                1 for item in output.draft.success_metrics if item.passed
            ),
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
    now = utcnow()
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


def _build_latest_semantic_pass_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    del session
    output = LatestSemanticPassTaskOutput.model_validate(payload)
    semantic_pass = output.semantic_pass
    now = utcnow()
    summary = TaskContextSummary(
        headline=(
            f"Loaded semantic pass {semantic_pass.semantic_pass_id} for document "
            f"{semantic_pass.document_id}."
        ),
        goal="Expose the active semantic pass as typed context for downstream orchestration.",
        decision=(
            "The semantic pass is ready for bounded triage."
            if semantic_pass.status == "completed"
            else "The semantic pass needs attention before triage."
        ),
        next_action="Create triage_semantic_pass to convert semantic evidence into a gap report.",
        approval_state="not_required",
        verification_state=semantic_pass.evaluation_status,
        metrics={
            "assertion_count": semantic_pass.assertion_count,
            "evidence_count": semantic_pass.evidence_count,
            "all_expectations_passed": semantic_pass.evaluation_summary.get(
                "all_expectations_passed"
            ),
            "success_metric_pass_count": sum(1 for item in output.success_metrics if item.passed),
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
        freshness_status=ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=[],
        output=output.model_dump(mode="json"),
    )


def _build_prepare_semantic_generation_brief_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = PrepareSemanticGenerationBriefTaskOutput.model_validate(payload)
    brief = output.brief
    now = utcnow()
    summary = TaskContextSummary(
        headline=(
            f"Prepared semantic generation brief {brief.title!r} across "
            f"{len(brief.document_refs)} document(s)."
        ),
        goal="Compress semantic passes into a typed dossier for knowledge-brief drafting.",
        decision="The brief is ready for draft_semantic_grounded_document.",
        next_action="Create draft_semantic_grounded_document to render a grounded knowledge brief.",
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "document_count": len(brief.document_refs),
            "concept_count": len(brief.semantic_dossier),
            "claim_count": len(brief.claim_candidates),
            "success_metric_pass_count": sum(1 for item in brief.success_metrics if item.passed),
        },
    )
    refs: list[ContextRef] = []
    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="brief_artifact",
                ref_kind="artifact",
                summary="Persisted semantic generation brief artifact for downstream drafting.",
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


def _build_draft_semantic_grounded_document_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = DraftSemanticGroundedDocumentTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    brief_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.draft.brief_task_id,
        dependency_kind="target_task",
        expected_task_type="prepare_semantic_generation_brief",
        expected_schema_name="prepare_semantic_generation_brief_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Grounded document drafts must declare the requested brief as a target_task dependency."
        ),
        rerun_message=(
            "Semantic generation brief must be rerun after the context migration before drafting."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="brief_task_output",
            ref_kind="task_output",
            summary="Typed semantic generation brief consumed by this grounded document draft.",
            task_id=brief_context.task_id,
            schema_name=brief_context.output_schema_name,
            schema_version=brief_context.output_schema_version,
            observed_sha256=_payload_sha256(brief_context.output),
            source_updated_at=brief_context.task_updated_at,
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
                summary="Persisted semantic-grounded document draft artifact.",
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
            f"Drafted grounded document {output.draft.title!r} with "
            f"{len(output.draft.claims)} claim(s)."
        ),
        goal="Render the typed semantic dossier into a reusable knowledge-brief draft.",
        decision="Draft created and ready for semantic-grounding verification.",
        next_action=(
            "Create verify_semantic_grounded_document to enforce traceability and coverage."
        ),
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "section_count": len(output.draft.sections),
            "claim_count": len(output.draft.claims),
            "evidence_count": len(output.draft.evidence_pack),
            "success_metric_pass_count": sum(
                1 for item in output.draft.success_metrics if item.passed
            ),
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
    now = utcnow()
    refs: list[ContextRef] = []

    draft_context = resolve_required_task_output_context(
        session,
        task_id=output.verification.target_task_id,
        expected_task_type="draft_harness_config_update",
        expected_schema_name="draft_harness_config_update_output",
        expected_schema_version="1.0",
        rerun_message=(
            "Target draft task must be rerun after the context migration before it can be verified."
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


def _build_verify_draft_semantic_registry_update_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = VerifyDraftSemanticRegistryUpdateTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.verification.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_semantic_registry_update",
        expected_schema_name="draft_semantic_registry_update_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Semantic draft verification must declare the requested draft "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Semantic draft task must be rerun after the context migration before verification."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="draft_task_output",
            ref_kind="task_output",
            summary="Migrated semantic registry draft output consumed by this verification.",
            task_id=draft_context.task_id,
            schema_name=draft_context.output_schema_name,
            schema_version=draft_context.output_schema_version,
            observed_sha256=_payload_sha256(draft_context.output),
            source_updated_at=draft_context.task_updated_at,
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
                summary="Verifier record persisted for the semantic registry draft gate.",
                task_id=output.verification.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=_payload_sha256(_verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="verification_artifact",
                ref_kind="artifact",
                summary="Persisted verification artifact for the semantic registry draft.",
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
        headline=(f"Verified semantic registry draft {output.draft.proposed_registry_version}."),
        goal="Validate additive registry updates against active documents before publication.",
        decision=(
            "Verification passed; the draft can move to approval review."
            if output.verification.outcome == "passed"
            else "Verification failed; revise the draft before publishing."
        ),
        next_action=(
            "Create apply_semantic_registry_update if the operator wants to publish the draft."
            if output.verification.outcome == "passed"
            else "Revise the draft registry update and rerun verification."
        ),
        approval_state="not_required",
        verification_state=output.verification.outcome,
        metrics={
            "document_count": len(output.document_deltas),
            "improved_document_count": output.summary.get("improved_document_count"),
            "regressed_document_count": output.summary.get("regressed_document_count"),
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
    now = utcnow()
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


def _build_verify_semantic_grounded_document_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = VerifySemanticGroundedDocumentTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.verification.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_semantic_grounded_document",
        expected_schema_name="draft_semantic_grounded_document_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Grounded-document verification must declare the requested draft "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Grounded-document draft must be rerun after the context migration before verification."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="draft_task_output",
            ref_kind="task_output",
            summary="Typed grounded-document draft consumed by this verification task.",
            task_id=draft_context.task_id,
            schema_name=draft_context.output_schema_name,
            schema_version=draft_context.output_schema_version,
            observed_sha256=_payload_sha256(draft_context.output),
            source_updated_at=draft_context.task_updated_at,
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
                summary="Verifier record persisted for the semantic grounded-document gate.",
                task_id=output.verification.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=_payload_sha256(_verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="verification_artifact",
                ref_kind="artifact",
                summary="Persisted verification artifact for the grounded document draft.",
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
            f"Verified grounded document {output.draft.title!r} with "
            f"{output.summary.get('claim_count', 0)} claim(s)."
        ),
        goal="Verify that the grounded document remains fully traceable to typed semantic support.",
        decision=(
            "Verification passed; the draft is ready for downstream use."
            if output.verification.outcome == "passed"
            else "Verification failed; revise the grounded draft before reuse."
        ),
        next_action=(
            "Use the verified draft as input to downstream authoring or review workflows."
            if output.verification.outcome == "passed"
            else "Revise the grounded draft and rerun verification."
        ),
        approval_state="not_required",
        verification_state=output.verification.outcome,
        metrics={
            "claim_count": output.summary.get("claim_count"),
            "unsupported_claim_count": output.summary.get("unsupported_claim_count"),
            "required_concept_coverage_ratio": output.summary.get(
                "required_concept_coverage_ratio"
            ),
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


def _build_triage_semantic_pass_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = TriageSemanticPassTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    target_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.verification.target_task_id,
        dependency_kind="target_task",
        expected_task_type="get_latest_semantic_pass",
        expected_schema_name="get_latest_semantic_pass_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Semantic triage must declare the requested semantic-pass task "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Target semantic-pass task must be rerun after the context migration before triage."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="target_task_output",
            ref_kind="task_output",
            summary="Typed semantic-pass output consumed by this gap report.",
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
                summary="Verifier record persisted for the semantic gap gate.",
                task_id=output.verification.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=_payload_sha256(_verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="semantic_gap_report_artifact",
                ref_kind="artifact",
                summary=(
                    "Persisted semantic gap report artifact for downstream review and draft work."
                ),
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
            f"Semantic triage recommends {output.recommendation.next_action} for "
            f"document {output.document_id}."
        ),
        goal=(
            "Compress semantic evidence, evaluation gaps, and continuity "
            "changes into bounded actions."
        ),
        decision=output.recommendation.summary,
        next_action=output.recommendation.next_action,
        approval_state="not_required",
        verification_state=output.verification.outcome,
        metrics={
            "issue_count": output.gap_report.issue_count,
            "success_metric_pass_count": sum(
                1 for item in output.gap_report.success_metrics if item.passed
            ),
            "registry_update_hint_count": sum(
                len(issue.registry_update_hints) for issue in output.gap_report.issues
            ),
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


def _build_apply_semantic_registry_update_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = ApplySemanticRegistryUpdateTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.draft_task_id,
        dependency_kind="draft_task",
        expected_task_type="draft_semantic_registry_update",
        expected_schema_name="draft_semantic_registry_update_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Semantic registry apply must declare the requested draft as a draft_task dependency."
        ),
        rerun_message=(
            "Semantic registry draft must be rerun after the context migration before apply."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="draft_task_output",
            ref_kind="task_output",
            summary="Migrated semantic registry draft output applied to the live registry file.",
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
        expected_task_type="verify_draft_semantic_registry_update",
        expected_schema_name="verify_draft_semantic_registry_update_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Semantic registry apply must declare the requested verification "
            "as a verification_task dependency."
        ),
        rerun_message=(
            "Semantic registry verification must be rerun after the context migration before apply."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="verification_task_output",
            ref_kind="task_output",
            summary=(
                "Migrated semantic registry verification output authorizing the live apply step."
            ),
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
                summary="Persisted apply artifact for the live semantic registry update.",
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

    verification_output = VerifyDraftSemanticRegistryUpdateTaskOutput.model_validate(
        verification_context.output
    )
    summary = TaskContextSummary(
        headline=f"Applied semantic registry {output.applied_registry_version}.",
        goal="Publish a verified semantic registry update after approval.",
        decision="Live semantic registry updated and ready for follow-on reprocessing.",
        next_action=(
            "Create enqueue_document_reprocess for affected documents if "
            "refreshed semantics are needed."
        ),
        approval_state="approved" if task.approved_at is not None else "pending",
        verification_state=verification_output.verification.outcome,
        metrics={
            "operation_count": len(output.applied_operations),
            "improved_document_count": verification_output.summary.get("improved_document_count"),
            "regressed_document_count": verification_output.summary.get("regressed_document_count"),
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


def _build_triage_replay_regression_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = TriageReplayRegressionTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    for source in output.evaluation.sources:
        baseline_run = session.get(SearchReplayRun, source.baseline_replay_run_id)
        if baseline_run is not None:
            refs.append(
                ContextRef(
                    ref_key=f"{source.source_type}_baseline_replay_run",
                    ref_kind="replay_run",
                    summary=(f"Baseline replay run for {source.source_type} used by triage."),
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
                    summary=(f"Candidate replay run for {source.source_type} used by triage."),
                    replay_run_id=candidate_run.id,
                    observed_sha256=_payload_sha256(_search_replay_run_payload(candidate_run)),
                    source_updated_at=candidate_run.completed_at or candidate_run.created_at,
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
                summary="Verifier record captured for the shadow-mode triage gate.",
                task_id=task.id,
                verification_id=verification_row.id,
                observed_sha256=_payload_sha256(_verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="triage_summary_artifact",
                ref_kind="artifact",
                summary="Deep triage evidence artifact with recommendation and supporting details.",
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
            f"Triage recommends {output.recommendation.next_action} for "
            f"{output.candidate_harness_name}."
        ),
        goal="Summarize replay-regression evidence and unresolved quality gaps in shadow mode.",
        decision=output.recommendation.summary,
        next_action=output.recommendation.next_action,
        approval_state="not_required",
        verification_state=output.verification.outcome,
        metrics={
            "confidence": output.recommendation.confidence,
            "quality_candidate_count": output.quality_candidate_count,
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


def _build_apply_harness_config_update_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = ApplyHarnessConfigUpdateTaskOutput.model_validate(payload)
    now = utcnow()
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
            "Verification task must be rerun after the context migration before it can be applied."
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

    verification_output = VerifyDraftHarnessConfigTaskOutput.model_validate(
        verification_context.output
    )
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


def _build_generic_task_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    del session
    now = utcnow()
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
    builder = action.context_builder or _build_generic_task_context
    return builder(session, task, payload, action=action)


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
    envelope.task_updated_at = utcnow()
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
