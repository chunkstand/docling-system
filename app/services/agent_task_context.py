from __future__ import annotations

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
    ApplyGraphPromotionsTaskOutput,
    ApplyHarnessConfigUpdateTaskOutput,
    ApplyOntologyExtensionTaskOutput,
    ApplySemanticRegistryUpdateTaskOutput,
    BuildDocumentFactGraphTaskOutput,
    BuildReportEvidenceCardsTaskOutput,
    BuildShadowSemanticGraphTaskOutput,
    ContextFreshnessStatus,
    ContextRef,
    DiscoverSemanticBootstrapCandidatesTaskOutput,
    DraftGraphPromotionsTaskOutput,
    DraftHarnessConfigUpdateTaskOutput,
    DraftOntologyExtensionTaskOutput,
    DraftSemanticGroundedDocumentTaskOutput,
    DraftSemanticRegistryUpdateTaskOutput,
    DraftTechnicalReportTaskOutput,
    EvaluateClaimSupportJudgeTaskOutput,
    EvaluateSearchHarnessTaskOutput,
    EvaluateSemanticCandidateExtractorTaskOutput,
    EvaluateSemanticRelationExtractorTaskOutput,
    ExportSemanticSupervisionCorpusTaskOutput,
    GetActiveOntologySnapshotTaskOutput,
    InitializeWorkspaceOntologyTaskOutput,
    LatestSemanticPassTaskOutput,
    PlanTechnicalReportTaskOutput,
    PrepareReportAgentHarnessTaskOutput,
    PrepareSemanticGenerationBriefTaskOutput,
    TaskContextEnvelope,
    TaskContextSummary,
    TriageReplayRegressionTaskOutput,
    TriageSemanticCandidateDisagreementsTaskOutput,
    TriageSemanticGraphDisagreementsTaskOutput,
    TriageSemanticPassTaskOutput,
    VerifyDraftGraphPromotionsTaskOutput,
    VerifyDraftHarnessConfigTaskOutput,
    VerifyDraftOntologyExtensionTaskOutput,
    VerifyDraftSemanticRegistryUpdateTaskOutput,
    VerifySearchHarnessEvaluationTaskOutput,
    VerifySemanticGroundedDocumentTaskOutput,
    VerifyTechnicalReportTaskOutput,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context_store import (
    artifact_context_ref,
    derive_freshness_status,
    get_context_artifact_row,
    payload_sha256,
    refresh_task_context_freshness,
    search_harness_evaluation_context_ref,
    search_replay_run_payload,
    task_output_context_ref,
    verification_payload,
)
from app.services.agent_task_context_store import (
    get_agent_task_context as get_agent_task_context,
)
from app.services.agent_task_context_store import (
    get_agent_task_context_artifact as get_agent_task_context_artifact,
)
from app.services.agent_task_context_store import (
    get_agent_task_context_yaml_path as get_agent_task_context_yaml_path,
)
from app.services.storage import StorageService


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
    expected_task_type: str | tuple[str, ...],
    expected_schema_name: str | tuple[str, ...],
    expected_schema_version: str,
    rerun_message: str,
) -> TaskContextEnvelope:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise _target_task_not_found(task_id)
    expected_task_types = (
        (expected_task_type,) if isinstance(expected_task_type, str) else expected_task_type
    )
    expected_schema_names = (
        (expected_schema_name,)
        if isinstance(expected_schema_name, str)
        else expected_schema_name
    )
    if task.task_type not in expected_task_types:
        raise _target_task_type_mismatch(
            task_id,
            expected_task_type=", ".join(expected_task_types),
            actual_task_type=task.task_type,
        )
    if task.status != "completed":
        raise _target_task_not_completed(task_id, task_status=task.status)
    context_row = get_context_artifact_row(session, task.id)
    if context_row is None:
        raise _rerun_required(
            "agent_task_context_output_missing",
            task_id=task.id,
            message=rerun_message,
            expected_schema_name=", ".join(expected_schema_names),
            expected_schema_version=expected_schema_version,
        )
    context = refresh_task_context_freshness(
        session,
        TaskContextEnvelope.model_validate(context_row.payload_json or {}),
    )
    if context.output_schema_name not in expected_schema_names:
        raise _rerun_required(
            "agent_task_context_output_schema_mismatch",
            task_id=task.id,
            message=rerun_message,
            expected_schema_name=", ".join(expected_schema_names),
            expected_schema_version=expected_schema_version,
            actual_schema_name=context.output_schema_name,
            actual_schema_version=context.output_schema_version,
        )
    if context.output_schema_version != expected_schema_version:
        raise _rerun_required(
            "agent_task_context_output_schema_version_mismatch",
            task_id=task.id,
            message=rerun_message,
            expected_schema_name=", ".join(expected_schema_names),
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
    expected_task_type: str | tuple[str, ...],
    expected_schema_name: str | tuple[str, ...],
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
            source_context_row = get_context_artifact_row(session, source_task.id)
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
                    observed_sha256=payload_sha256(observed_payload),
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
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
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
        problem=(
            "Draft is evidence-backed by a source task."
            if output.draft.source_task_id is not None
            else "Draft has no source repair task."
        ),
        evidence=(
            "Source task context is attached as a freshness-checked ref."
            if output.draft.source_task_id is not None
            else None
        ),
        proposed_change=(
            "retrieval overrides="
            f"{sorted(output.draft.override_spec.retrieval_profile_overrides)}, "
            f"reranker overrides={sorted(output.draft.override_spec.reranker_overrides)}"
        ),
        predicted_risk="Verification must pass replay and comprehension gates before apply.",
        follow_up_status="not_started",
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
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
        source_context_row = get_context_artifact_row(session, source_task.id)
        observed_payload = (
            TaskContextEnvelope.model_validate(source_context_row.payload_json or {}).output
            if source_context_row is not None
            else source_task.result_json or {}
        )
        refs.append(
            ContextRef(
                ref_key="source_task",
                ref_kind="task_output",
                summary="Source task that motivated this semantic registry draft.",
                task_id=source_task.id,
                schema_name=source_action.output_schema_name,
                schema_version=source_action.output_schema_version,
                observed_sha256=payload_sha256(observed_payload),
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
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
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
                ContextRef(
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
                    observed_sha256=payload_sha256(search_replay_run_payload(candidate_run)),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
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


def _build_initialize_workspace_ontology_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = InitializeWorkspaceOntologyTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="active_ontology_snapshot_artifact",
                ref_kind="artifact",
                summary="Persisted artifact for the initialized active ontology snapshot.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    snapshot = output.snapshot
    summary = TaskContextSummary(
        headline=f"Initialized workspace ontology {snapshot.ontology_version}.",
        goal="Seed the workspace ontology from the configured upper ontology.",
        decision="The workspace now has an active ontology snapshot and can process domain data.",
        next_action=(
            "Ingest documents or create discover_semantic_bootstrap_candidates "
            "after active semantic passes exist."
        ),
        approval_state="not_required",
        verification_state="completed",
        metrics={
            "concept_count": snapshot.concept_count,
            "category_count": snapshot.category_count,
            "relation_count": snapshot.relation_count,
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_get_active_ontology_snapshot_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    del session
    output = GetActiveOntologySnapshotTaskOutput.model_validate(payload)
    now = utcnow()
    snapshot = output.snapshot
    next_action = (
        "Create discover_semantic_bootstrap_candidates or draft_ontology_extension "
        "after reviewing active corpus evidence."
        if snapshot.source_kind == "upper_seed"
        else "Use the active ontology for reprocessing, fact-graph builds, or grounded generation."
    )
    summary = TaskContextSummary(
        headline=f"Active ontology snapshot {snapshot.ontology_version} is loaded.",
        goal="Expose the live workspace ontology as typed, reusable agent context.",
        decision="The current ontology snapshot is available for semantic passes and generation.",
        next_action=next_action,
        approval_state="not_required",
        verification_state="completed",
        metrics={
            "concept_count": snapshot.concept_count,
            "category_count": snapshot.category_count,
            "relation_count": snapshot.relation_count,
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


def _resolve_ontology_source_task_context(
    session: Session,
    *,
    task_id: UUID,
    source_task_id: UUID | None,
    source_task_type: str | None,
) -> TaskContextEnvelope | None:
    if source_task_id is None:
        return None
    resolved_source_task_type = source_task_type
    if resolved_source_task_type is None:
        source_task = session.get(AgentTask, source_task_id)
        resolved_source_task_type = source_task.task_type if source_task is not None else None
    if resolved_source_task_type == "triage_semantic_pass":
        return resolve_required_dependency_task_output_context(
            session,
            task_id=task_id,
            depends_on_task_id=source_task_id,
            dependency_kind="source_task",
            expected_task_type="triage_semantic_pass",
            expected_schema_name="triage_semantic_pass_output",
            expected_schema_version="1.0",
            dependency_error_message=(
                "Ontology extension draft must declare the semantic triage task "
                "as a source_task dependency."
            ),
            rerun_message=(
                "Semantic triage task must be rerun after the context migration "
                "before ontology drafting."
            ),
        )
    if resolved_source_task_type == "discover_semantic_bootstrap_candidates":
        return resolve_required_dependency_task_output_context(
            session,
            task_id=task_id,
            depends_on_task_id=source_task_id,
            dependency_kind="source_task",
            expected_task_type="discover_semantic_bootstrap_candidates",
            expected_schema_name="discover_semantic_bootstrap_candidates_output",
            expected_schema_version="1.0",
            dependency_error_message=(
                "Ontology extension draft must declare the bootstrap discovery task "
                "as a source_task dependency."
            ),
            rerun_message=(
                "Bootstrap discovery task must be rerun after the context migration "
                "before ontology drafting."
            ),
        )
    return None


def _build_draft_ontology_extension_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = DraftOntologyExtensionTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    source_context = _resolve_ontology_source_task_context(
        session,
        task_id=task.id,
        source_task_id=output.draft.source_task_id,
        source_task_type=output.draft.source_task_type,
    )
    if source_context is not None:
        refs.append(
            ContextRef(
                ref_key="source_task",
                ref_kind="task_output",
                summary="Typed source task that motivated this ontology extension draft.",
                task_id=source_context.task_id,
                schema_name=source_context.output_schema_name,
                schema_version=source_context.output_schema_version,
                observed_sha256=payload_sha256(source_context.output),
                source_updated_at=source_context.task_updated_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="ontology_extension_draft_artifact",
                ref_kind="artifact",
                summary="Persisted additive ontology extension draft artifact.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    summary = TaskContextSummary(
        headline=(
            f"Drafted ontology extension {output.draft.proposed_ontology_version} with "
            f"{len(output.draft.operations)} operation(s)."
        ),
        goal="Capture a reviewable additive ontology extension without changing live state.",
        decision="The ontology draft is ready for verification against active documents.",
        next_action=(
            "Create verify_draft_ontology_extension before any ontology publication step."
        ),
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "operation_count": len(output.draft.operations),
            "document_count": len(output.draft.document_ids),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_verify_draft_ontology_extension_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = VerifyDraftOntologyExtensionTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.verification.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_ontology_extension",
        expected_schema_name="draft_ontology_extension_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Ontology extension verification must declare the requested ontology draft "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Ontology extension draft must be rerun after the context migration "
            "before verification."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="target_task_output",
            ref_kind="task_output",
            summary="Typed ontology extension draft consumed by this verification task.",
            task_id=draft_context.task_id,
            schema_name=draft_context.output_schema_name,
            schema_version=draft_context.output_schema_version,
            observed_sha256=payload_sha256(draft_context.output),
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
                summary="Verifier record persisted for the ontology extension verification gate.",
                task_id=output.verification.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=payload_sha256(verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="ontology_extension_verification_artifact",
                ref_kind="artifact",
                summary="Persisted ontology extension verification artifact.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    summary = TaskContextSummary(
        headline=(
            f"Ontology verification {output.verification.outcome} for "
            f"{output.draft.proposed_ontology_version}."
        ),
        goal="Verify a draft ontology extension against active document semantics.",
        decision=(
            "The ontology draft is ready for approval and apply."
            if output.verification.outcome == "passed"
            else "Revise the ontology draft before any publication step."
        ),
        next_action=(
            "Create apply_ontology_extension after approval."
            if output.verification.outcome == "passed"
            else "Refine the ontology draft and rerun verification."
        ),
        approval_state="not_required",
        verification_state=output.verification.outcome,
        metrics={
            "improved_document_count": output.summary.get("improved_document_count"),
            "regressed_document_count": output.summary.get("regressed_document_count"),
            "operation_count": len(output.draft.operations),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_apply_ontology_extension_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = ApplyOntologyExtensionTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.draft_task_id,
        dependency_kind="draft_task",
        expected_task_type="draft_ontology_extension",
        expected_schema_name="draft_ontology_extension_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply ontology task must declare the requested ontology draft "
            "as a draft_task dependency."
        ),
        rerun_message=(
            "Ontology draft task must be rerun after the context migration before apply."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="draft_task_output",
            ref_kind="task_output",
            summary="Typed ontology draft output applied to the active workspace snapshot.",
            task_id=draft_context.task_id,
            schema_name=draft_context.output_schema_name,
            schema_version=draft_context.output_schema_version,
            observed_sha256=payload_sha256(draft_context.output),
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
        expected_task_type="verify_draft_ontology_extension",
        expected_schema_name="verify_draft_ontology_extension_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply ontology task must declare the requested ontology verification "
            "as a verification_task dependency."
        ),
        rerun_message=(
            "Ontology verification task must be rerun after the context migration before apply."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="verification_task_output",
            ref_kind="task_output",
            summary="Typed ontology verification output authorizing the apply step.",
            task_id=verification_context.task_id,
            schema_name=verification_context.output_schema_name,
            schema_version=verification_context.output_schema_version,
            observed_sha256=payload_sha256(verification_context.output),
            source_updated_at=verification_context.task_updated_at,
            checked_at=now,
            freshness_status=ContextFreshnessStatus.FRESH,
        )
    )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="applied_ontology_artifact",
                ref_kind="artifact",
                summary="Persisted apply artifact for the active ontology snapshot update.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    verification_output = VerifyDraftOntologyExtensionTaskOutput.model_validate(
        verification_context.output
    )
    summary = TaskContextSummary(
        headline=f"Applied ontology snapshot {output.applied_ontology_version}.",
        goal="Publish a verified ontology extension after approval.",
        decision="The active ontology snapshot is updated and ready for downstream reprocessing.",
        next_action=(
            "Create enqueue_document_reprocess for affected documents or "
            "refresh grounded artifacts against the new ontology."
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_build_document_fact_graph_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = BuildDocumentFactGraphTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="semantic_fact_graph_artifact",
                ref_kind="artifact",
                summary="Persisted semantic fact graph artifact for the active document.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    summary = TaskContextSummary(
        headline=f"Built {output.fact_count} semantic fact(s) for document {output.document_id}.",
        goal="Compact approved semantic assertions into a reusable fact graph for agents.",
        decision="The fact graph is ready for grounded generation and later orchestration.",
        next_action=(
            "Create prepare_semantic_generation_brief or refresh grounded outputs "
            "to consume approved facts."
        ),
        approval_state="not_required",
        verification_state="completed",
        metrics={
            "fact_count": output.fact_count,
            "approved_fact_count": output.approved_fact_count,
            "entity_count": output.entity_count,
            "relation_type_count": len(output.relation_counts),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_build_shadow_semantic_graph_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = BuildShadowSemanticGraphTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="shadow_semantic_graph_artifact",
                ref_kind="artifact",
                summary=(
                    "Persisted shadow semantic graph artifact for cross-document memory review."
                ),
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    graph = output.shadow_graph
    summary = TaskContextSummary(
        headline=(
            f"Built shadow semantic graph {graph.graph_version} with {graph.edge_count} "
            f"cross-document edge(s)."
        ),
        goal="Compact semantic evidence into a typed, reviewable shadow graph memory layer.",
        decision=(
            "The shadow graph is ready for extractor evaluation or bounded promotion drafting."
        ),
        next_action=(
            "Create evaluate_semantic_relation_extractor or draft_graph_promotions "
            "to compare and promote graph memory."
        ),
        approval_state="not_required",
        verification_state="completed",
        metrics={
            "document_count": graph.document_count,
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "success_metric_pass_count": sum(1 for item in graph.success_metrics if item.passed),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_evaluate_semantic_relation_extractor_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = EvaluateSemanticRelationExtractorTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="semantic_relation_evaluation_artifact",
                ref_kind="artifact",
                summary="Persisted relation-extractor evaluation artifact with typed edge reports.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    summary_payload = output.summary
    summary = TaskContextSummary(
        headline=(
            f"Evaluated graph extractors on {summary_payload.get('document_count', 0)} "
            f"document(s) with {summary_payload.get('expected_edge_count', 0)} expected edge(s)."
        ),
        goal=(
            "Measure shadow relation extraction against a deterministic baseline "
            "and fixed expectations."
        ),
        decision=(
            "The candidate extractor is ready for disagreement triage."
            if summary_payload.get("candidate_expected_recall", 0.0)
            >= summary_payload.get("baseline_expected_recall", 0.0)
            else "The candidate extractor needs revision before any promotion work."
        ),
        next_action=(
            "Create triage_semantic_graph_disagreements to compact candidate-vs-live graph gaps."
        ),
        approval_state="not_required",
        verification_state="completed",
        metrics={
            "expected_edge_count": summary_payload.get("expected_edge_count"),
            "candidate_expected_recall": summary_payload.get("candidate_expected_recall"),
            "baseline_expected_recall": summary_payload.get("baseline_expected_recall"),
            "candidate_only_edge_count": summary_payload.get("candidate_only_edge_count"),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_triage_semantic_graph_disagreements_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = TriageSemanticGraphDisagreementsTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    evaluation_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.evaluation_task_id,
        dependency_kind="target_task",
        expected_task_type="evaluate_semantic_relation_extractor",
        expected_schema_name="evaluate_semantic_relation_extractor_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Graph disagreement triage must declare the requested graph evaluation "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Graph evaluation task must be rerun after the context migration before triage."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="target_task_output",
            ref_kind="task_output",
            summary="Typed graph evaluation output consumed by this disagreement triage.",
            task_id=evaluation_context.task_id,
            schema_name=evaluation_context.output_schema_name,
            schema_version=evaluation_context.output_schema_version,
            observed_sha256=payload_sha256(evaluation_context.output),
            source_updated_at=evaluation_context.task_updated_at,
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
                summary="Verifier record for the bounded shadow-graph disagreement gate.",
                task_id=task.id,
                verification_id=verification_row.id,
                observed_sha256=payload_sha256(verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="semantic_graph_disagreement_artifact",
                ref_kind="artifact",
                summary="Persisted semantic graph disagreement artifact with typed issue records.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    report = output.disagreement_report
    summary = TaskContextSummary(
        headline=f"Triaged {report.issue_count} graph disagreement issue(s).",
        goal="Compact graph-evaluation gaps into bounded, typed promotion candidates.",
        decision=(
            "The graph triage produced actionable promotion candidates."
            if report.issue_count
            else "No graph promotions are currently justified."
        ),
        next_action=(
            "Create draft_graph_promotions to review the suggested graph edges."
            if report.issue_count
            else "Observe the shadow graph until new semantic evidence arrives."
        ),
        approval_state="not_required",
        verification_state=output.verification.outcome,
        metrics={
            "issue_count": report.issue_count,
            "followup_count": len(report.recommended_followups),
            "success_metric_pass_count": sum(1 for item in report.success_metrics if item.passed),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_draft_graph_promotions_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = DraftGraphPromotionsTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    source_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.draft.source_task_id,
        dependency_kind="source_task",
        expected_task_type=output.draft.source_task_type,
        expected_schema_name=(
            "build_shadow_semantic_graph_output"
            if output.draft.source_task_type == "build_shadow_semantic_graph"
            else "triage_semantic_graph_disagreements_output"
        ),
        expected_schema_version="1.0",
        dependency_error_message=(
            "Graph promotion drafts must declare the source graph task as a source_task dependency."
        ),
        rerun_message=(
            "Source graph task must be rerun after the context migration before drafting."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="source_task",
            ref_kind="task_output",
            summary="Typed source graph task that motivated this promotion draft.",
            task_id=source_context.task_id,
            schema_name=source_context.output_schema_name,
            schema_version=source_context.output_schema_version,
            observed_sha256=payload_sha256(source_context.output),
            source_updated_at=source_context.task_updated_at,
            checked_at=now,
            freshness_status=ContextFreshnessStatus.FRESH,
        )
    )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="semantic_graph_promotion_draft_artifact",
                ref_kind="artifact",
                summary="Persisted semantic graph promotion draft artifact.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    summary = TaskContextSummary(
        headline=(
            f"Drafted graph promotion {output.draft.proposed_graph_version} with "
            f"{len(output.draft.promoted_edges)} edge(s)."
        ),
        goal="Prepare a reviewable graph-memory update without mutating live graph state.",
        decision="The graph promotion draft is ready for verification against the live ontology.",
        next_action="Create verify_draft_graph_promotions before any apply step.",
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "promoted_edge_count": len(output.draft.promoted_edges),
            "effective_edge_count": output.draft.effective_graph.edge_count,
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_verify_draft_graph_promotions_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = VerifyDraftGraphPromotionsTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.verification.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_graph_promotions",
        expected_schema_name="draft_graph_promotions_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Graph promotion verification must declare the requested graph draft "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Graph promotion draft must be rerun after the context migration before verification."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="target_task_output",
            ref_kind="task_output",
            summary="Typed graph promotion draft consumed by this verification task.",
            task_id=draft_context.task_id,
            schema_name=draft_context.output_schema_name,
            schema_version=draft_context.output_schema_version,
            observed_sha256=payload_sha256(draft_context.output),
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
                summary="Verifier record for the semantic graph promotion gate.",
                task_id=output.verification.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=payload_sha256(verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="semantic_graph_promotion_verification_artifact",
                ref_kind="artifact",
                summary="Persisted graph promotion verification artifact.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    summary = TaskContextSummary(
        headline=(
            f"Graph promotion verification {output.verification.outcome} for "
            f"{output.draft.proposed_graph_version}."
        ),
        goal=(
            "Verify graph-memory promotions against ontology, traceability, and "
            "conflict constraints."
        ),
        decision=(
            "The graph promotion draft is ready for approval and apply."
            if output.verification.outcome == "passed"
            else "Revise the graph promotion draft before any apply step."
        ),
        next_action=(
            "Create apply_graph_promotions after approval."
            if output.verification.outcome == "passed"
            else "Refine the graph promotion draft and rerun verification."
        ),
        approval_state="not_required",
        verification_state=output.verification.outcome,
        metrics={
            "promoted_edge_count": output.summary.get("promoted_edge_count"),
            "supported_edge_count": output.summary.get("supported_edge_count"),
            "conflict_count": output.summary.get("conflict_count"),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_apply_graph_promotions_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = ApplyGraphPromotionsTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.draft_task_id,
        dependency_kind="draft_task",
        expected_task_type="draft_graph_promotions",
        expected_schema_name="draft_graph_promotions_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply graph promotions must declare the requested graph draft as "
            "a draft_task dependency."
        ),
        rerun_message=(
            "Graph promotion draft task must be rerun after the context migration before apply."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="draft_task_output",
            ref_kind="task_output",
            summary="Typed graph promotion draft applied to the active workspace graph snapshot.",
            task_id=draft_context.task_id,
            schema_name=draft_context.output_schema_name,
            schema_version=draft_context.output_schema_version,
            observed_sha256=payload_sha256(draft_context.output),
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
        expected_task_type="verify_draft_graph_promotions",
        expected_schema_name="verify_draft_graph_promotions_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Apply graph promotions must declare the requested graph verification "
            "as a verification_task dependency."
        ),
        rerun_message=(
            "Graph promotion verification task must be rerun after the context "
            "migration before apply."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="verification_task_output",
            ref_kind="task_output",
            summary="Typed graph promotion verification output authorizing the apply step.",
            task_id=verification_context.task_id,
            schema_name=verification_context.output_schema_name,
            schema_version=verification_context.output_schema_version,
            observed_sha256=payload_sha256(verification_context.output),
            source_updated_at=verification_context.task_updated_at,
            checked_at=now,
            freshness_status=ContextFreshnessStatus.FRESH,
        )
    )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="applied_semantic_graph_artifact",
                ref_kind="artifact",
                summary="Persisted apply artifact for the active semantic graph snapshot update.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    verification_output = VerifyDraftGraphPromotionsTaskOutput.model_validate(
        verification_context.output
    )
    summary = TaskContextSummary(
        headline=f"Applied semantic graph snapshot {output.applied_graph_version}.",
        goal="Publish verified graph-memory promotions after explicit approval.",
        decision=(
            "The active graph snapshot is updated and ready for downstream "
            "generation and orchestration."
        ),
        next_action=(
            "Refresh semantic generation briefs or build new graph-aware tasks "
            "against the active snapshot."
        ),
        approval_state="approved" if task.approved_at is not None else "pending",
        verification_state=verification_output.verification.outcome,
        metrics={
            "applied_edge_count": output.applied_edge_count,
            "supported_edge_count": verification_output.summary.get("supported_edge_count"),
            "conflict_count": verification_output.summary.get("conflict_count"),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_discover_semantic_bootstrap_candidates_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = DiscoverSemanticBootstrapCandidatesTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="bootstrap_candidate_report_artifact",
                ref_kind="artifact",
                summary="Persisted semantic bootstrap candidate report artifact.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    summary = TaskContextSummary(
        headline=(
            f"Discovered {output.report.candidate_count} bootstrap semantic candidate(s) across "
            f"{output.report.document_count} document(s)."
        ),
        goal=(
            "Surface domain-agnostic semantic candidates as typed, reviewable context before "
            "any registry mutation."
        ),
        decision=(
            "Bootstrap candidates are ready for additive registry drafting."
            if output.report.candidate_count
            else "Bootstrap discovery needs broader evidence before drafting registry updates."
        ),
        next_action=(
            "Create draft_semantic_registry_update to turn selected bootstrap candidates into "
            "a reviewable additive registry draft."
        ),
        approval_state="not_required",
        verification_state="completed",
        metrics={
            "document_count": output.report.document_count,
            "candidate_count": output.report.candidate_count,
            "total_source_count": output.report.total_source_count,
            "success_metric_pass_count": sum(
                1 for item in output.report.success_metrics if item.passed
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_export_semantic_supervision_corpus_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = ExportSemanticSupervisionCorpusTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="corpus_artifact",
                ref_kind="artifact",
                summary="Persisted semantic supervision corpus export and JSON summary artifact.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    summary = TaskContextSummary(
        headline=(
            f"Exported semantic supervision corpus with {output.corpus.row_count} row(s) across "
            f"{output.corpus.document_count} document(s)."
        ),
        goal=(
            "Package reusable semantic supervision signals for shadow-model evaluation and review."
        ),
        decision=(
            "The supervision corpus is ready for candidate-extractor "
            "evaluation or offline analysis."
        ),
        next_action=(
            "Create evaluate_semantic_candidate_extractor to compare a "
            "shadow extractor against the baseline."
        ),
        approval_state="not_required",
        verification_state="completed",
        metrics={
            "document_count": output.corpus.document_count,
            "row_count": output.corpus.row_count,
            "success_metric_pass_count": sum(
                1 for item in output.corpus.success_metrics if item.passed
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_evaluate_semantic_candidate_extractor_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = EvaluateSemanticCandidateExtractorTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="evaluation_artifact",
                ref_kind="artifact",
                summary="Persisted shadow semantic candidate evaluation artifact.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    summary = TaskContextSummary(
        headline=(
            f"Evaluated {output.candidate_extractor.extractor_name} against "
            f"{output.baseline_extractor.extractor_name} across "
            f"{len(output.document_reports)} document(s)."
        ),
        goal=(
            "Compare a shadow semantic candidate extractor to the lexical "
            "baseline without mutating live semantics."
        ),
        decision="The candidate evaluation is ready for disagreement triage.",
        next_action=(
            "Create triage_semantic_candidate_disagreements to compact useful shadow gaps."
        ),
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "document_count": len(output.document_reports),
            "candidate_expected_recall": output.summary.get("candidate_expected_recall"),
            "baseline_expected_recall": output.summary.get("baseline_expected_recall"),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
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
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
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
            observed_sha256=payload_sha256(brief_context.output),
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
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
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
        expected_task_type=(
            "draft_harness_config_update",
            "draft_harness_config_update_from_optimization",
        ),
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
            observed_sha256=payload_sha256(draft_context.output),
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

    evaluation_ref = search_harness_evaluation_context_ref(
        session,
        output.evaluation.get("evaluation_id"),
        now=now,
    )
    if evaluation_ref is not None:
        refs.append(evaluation_ref)

    verification_row = session.get(AgentTaskVerification, output.verification.verification_id)
    if verification_row is not None:
        refs.append(
            ContextRef(
                ref_key="verification_record",
                ref_kind="verification_record",
                summary="Verifier record persisted for the draft review gate.",
                task_id=output.verification.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=payload_sha256(verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    verification_outcome = output.verification.outcome
    comprehension_gate = output.comprehension_gate
    changed_scopes = (
        comprehension_gate.predicted_blast_radius.get("changed_scopes") or []
        if comprehension_gate is not None
        else []
    )
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
        problem=(
            comprehension_gate.repair_case.problem_statement
            if comprehension_gate is not None and comprehension_gate.repair_case is not None
            else None
        ),
        evidence=(
            comprehension_gate.claim_evidence_alignment if comprehension_gate is not None else None
        ),
        proposed_change=(
            comprehension_gate.change_justification if comprehension_gate is not None else None
        ),
        predicted_risk=(
            f"Changed scopes: {', '.join(changed_scopes)}"
            if comprehension_gate is not None
            else None
        ),
        follow_up_status="planned" if output.follow_up_plan else "not_started",
        metrics={
            "total_shared_query_count": (output.verification.metrics or {}).get(
                "total_shared_query_count"
            ),
            "regressed_count": output.evaluation.get("total_regressed_count"),
            "improved_count": output.evaluation.get("total_improved_count"),
            "comprehension_passed": (
                comprehension_gate.comprehension_passed if comprehension_gate is not None else None
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
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
            observed_sha256=payload_sha256(draft_context.output),
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
                observed_sha256=payload_sha256(verification_payload(verification_row)),
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
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
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
            observed_sha256=payload_sha256(target_context.output),
            source_updated_at=target_context.task_updated_at,
            checked_at=now,
            freshness_status=ContextFreshnessStatus.FRESH,
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
            ContextRef(
                ref_key="verification_record",
                ref_kind="verification_record",
                summary="Verifier record persisted for the evaluation rollout gate.",
                task_id=output.verification.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=payload_sha256(verification_payload(verification_row)),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
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
            observed_sha256=payload_sha256(draft_context.output),
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
                observed_sha256=payload_sha256(verification_payload(verification_row)),
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
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_plan_technical_report_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = PlanTechnicalReportTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []
    artifact_ref = artifact_context_ref(
        session,
        task=task,
        artifact_id=output.artifact_id,
        action=action,
        ref_key="technical_report_plan_artifact",
        summary="Persisted technical report plan and semantic source brief.",
        now=now,
    )
    if artifact_ref is not None:
        refs.append(artifact_ref)
    summary = TaskContextSummary(
        headline=(
            f"Planned technical report {output.plan.title!r} with "
            f"{len(output.plan.sections)} section(s)."
        ),
        goal="Turn the semantic dossier into a section, claim, graph, and retrieval plan.",
        decision="The report plan is ready for evidence-card construction.",
        next_action="Create build_report_evidence_cards to bind planned claims to evidence cards.",
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "section_count": len(output.plan.sections),
            "expected_claim_count": len(output.plan.expected_claims),
            "expected_graph_edge_count": len(output.plan.expected_graph_edge_ids),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_build_report_evidence_cards_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = BuildReportEvidenceCardsTaskOutput.model_validate(payload)
    now = utcnow()
    plan_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.evidence_bundle.plan_task_id,
        dependency_kind="target_task",
        expected_task_type="plan_technical_report",
        expected_schema_name="plan_technical_report_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Evidence-card construction must declare the report plan as a target_task dependency."
        ),
        rerun_message=(
            "Technical report plan must be rerun after the context migration "
            "before evidence cards can be built."
        ),
    )
    refs: list[ContextRef] = [
        task_output_context_ref(
            ref_key="plan_task_output",
            summary="Typed technical report plan consumed by this evidence-card task.",
            context=plan_context,
            now=now,
        )
    ]
    artifact_ref = artifact_context_ref(
        session,
        task=task,
        artifact_id=output.artifact_id,
        action=action,
        ref_key="evidence_cards_artifact",
        summary="Persisted technical report evidence-card bundle.",
        now=now,
    )
    if artifact_ref is not None:
        refs.append(artifact_ref)
    summary = TaskContextSummary(
        headline=(
            f"Built {len(output.evidence_bundle.evidence_cards)} evidence card(s) "
            f"for {output.evidence_bundle.plan.title!r}."
        ),
        goal="Bind report claims to typed source evidence, facts, tables, and graph edges.",
        decision="Evidence cards are ready for wake-up harness packaging.",
        next_action="Create prepare_report_agent_harness to package the LLM wake-up context.",
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "evidence_card_count": len(output.evidence_bundle.evidence_cards),
            "claim_contract_count": len(output.evidence_bundle.claim_evidence_map),
            "graph_edge_count": len(output.evidence_bundle.graph_context),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_prepare_report_agent_harness_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = PrepareReportAgentHarnessTaskOutput.model_validate(payload)
    now = utcnow()
    evidence_task_id = UUID(str(output.harness.workflow_state["evidence_task_id"]))
    evidence_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=evidence_task_id,
        dependency_kind="target_task",
        expected_task_type="build_report_evidence_cards",
        expected_schema_name="build_report_evidence_cards_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Report harness packaging must declare the evidence-card task "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Report evidence cards must be rerun after the context migration "
            "before harness packaging."
        ),
    )
    refs: list[ContextRef] = [
        task_output_context_ref(
            ref_key="evidence_cards_task_output",
            summary="Typed evidence-card bundle consumed by this report harness.",
            context=evidence_context,
            now=now,
        )
    ]
    artifact_ref = artifact_context_ref(
        session,
        task=task,
        artifact_id=output.artifact_id,
        action=action,
        ref_key="report_agent_harness_artifact",
        summary="LLM wake-up harness with tools, skills, evidence cards, and checks.",
        now=now,
    )
    if artifact_ref is not None:
        refs.append(artifact_ref)
    summary = TaskContextSummary(
        headline=(
            f"Prepared report wake-up harness for {output.harness.report_request['title']!r}."
        ),
        goal=(
            "Package the correct context, tools, skills, evidence, "
            "graph memory, and verifier gate."
        ),
        decision="The harness is ready for draft_technical_report.",
        next_action="Create draft_technical_report to render a verification-ready report draft.",
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "tool_count": len(output.harness.allowed_tools),
            "skill_count": len(output.harness.required_skills),
            "evidence_card_count": len(output.harness.evidence_cards),
            "claim_contract_count": len(output.harness.claim_contract),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_draft_technical_report_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = DraftTechnicalReportTaskOutput.model_validate(payload)
    now = utcnow()
    harness_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.draft.harness_task_id,
        dependency_kind="target_task",
        expected_task_type="prepare_report_agent_harness",
        expected_schema_name="prepare_report_agent_harness_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Technical report drafting must declare the report harness "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Report agent harness must be rerun after the context migration before drafting."
        ),
    )
    refs: list[ContextRef] = [
        task_output_context_ref(
            ref_key="report_agent_harness_task_output",
            summary="Typed report wake-up harness consumed by this draft task.",
            context=harness_context,
            now=now,
        )
    ]
    artifact_ref = artifact_context_ref(
        session,
        task=task,
        artifact_id=output.artifact_id,
        action=action,
        ref_key="technical_report_draft_artifact",
        summary="Persisted technical report draft and markdown sidecar.",
        now=now,
    )
    if artifact_ref is not None:
        refs.append(artifact_ref)
    summary = TaskContextSummary(
        headline=(
            f"Drafted technical report {output.draft.title!r} with "
            f"{len(output.draft.claims)} claim(s)."
        ),
        goal="Render the report harness into a verification-ready technical report.",
        decision="Draft created and ready for technical report verification.",
        next_action="Create verify_technical_report to enforce evidence, graph, and context gates.",
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "section_count": len(output.draft.sections),
            "claim_count": len(output.draft.claims),
            "blocked_claim_count": len(output.draft.blocked_claims),
            "generator_mode": output.draft.generator_mode,
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_verify_technical_report_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = VerifyTechnicalReportTaskOutput.model_validate(payload)
    now = utcnow()
    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.verification.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_technical_report",
        expected_schema_name="draft_technical_report_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Technical report verification must declare the report draft "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Technical report draft must be rerun after the context migration before verification."
        ),
    )
    refs: list[ContextRef] = [
        task_output_context_ref(
            ref_key="technical_report_draft_task_output",
            summary="Typed technical report draft consumed by this verification task.",
            context=draft_context,
            now=now,
        )
    ]
    verification_row = session.get(AgentTaskVerification, output.verification.verification_id)
    if verification_row is not None:
        refs.append(
            ContextRef(
                ref_key="verification_record",
                ref_kind="verification_record",
                summary="Verifier record persisted for the technical report gate.",
                task_id=output.verification.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=payload_sha256(verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )
    artifact_ref = artifact_context_ref(
        session,
        task=task,
        artifact_id=output.artifact_id,
        action=action,
        ref_key="technical_report_verification_artifact",
        summary="Persisted technical report verification artifact.",
        now=now,
    )
    if artifact_ref is not None:
        refs.append(artifact_ref)
    summary = TaskContextSummary(
        headline=(
            f"Verified technical report {output.draft.title!r} with "
            f"{output.summary.get('claim_count', 0)} claim(s)."
        ),
        goal="Verify report claim traceability, graph approval, citations, and wake-up context.",
        decision=(
            "Verification passed; the technical report is ready for review."
            if output.verification.outcome == "passed"
            else "Verification failed; revise the technical report before review."
        ),
        next_action=(
            "Record an operator outcome or use the verified report downstream."
            if output.verification.outcome == "passed"
            else "Revise the draft or evidence harness and rerun verification."
        ),
        approval_state="not_required",
        verification_state=output.verification.outcome,
        metrics={
            "claim_count": output.summary.get("claim_count"),
            "unsupported_claim_count": output.summary.get("unsupported_claim_count"),
            "traceable_claim_ratio": output.summary.get("traceable_claim_ratio"),
            "context_blocker_count": output.summary.get("context_blocker_count"),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_evaluate_claim_support_judge_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = EvaluateClaimSupportJudgeTaskOutput.model_validate(payload)
    now = utcnow()
    gate_outcome = str(output.summary.get("gate_outcome") or "unknown")
    gate_passed = gate_outcome == "passed"
    refs: list[ContextRef] = []
    artifact_ref = artifact_context_ref(
        session,
        task=task,
        artifact_id=output.artifact_id,
        action=action,
        ref_key="claim_support_judge_evaluation_artifact",
        summary="Persisted claim support judge replay evaluation artifact.",
        now=now,
    )
    if artifact_ref is not None:
        refs.append(artifact_ref)
    summary = TaskContextSummary(
        headline=(
            f"Claim support judge evaluation {gate_outcome} with "
            f"{output.summary.get('case_count', 0)} replay case(s)."
        ),
        goal=(
            "Replay fixed hard-case fixtures to calibrate the technical report claim support judge."
        ),
        decision=(
            "Support judge calibration is ready for gated technical report verification."
            if gate_passed
            else "Support judge calibration failed; repair the judge or fixtures before promotion."
        ),
        next_action=(
            "Use verify_technical_report with support judgments enabled."
            if gate_passed
            else "Inspect failed case_results and rerun evaluate_claim_support_judge."
        ),
        approval_state="not_required",
        verification_state=gate_outcome,
        problem="; ".join(output.reasons) if output.reasons else None,
        evidence=f"Fixture set sha256: {output.fixture_set_sha256}",
        metrics={
            "gate_outcome": gate_outcome,
            "case_count": output.summary.get("case_count"),
            "passed_case_count": output.summary.get("passed_case_count"),
            "failed_case_count": output.summary.get("failed_case_count"),
            "overall_accuracy": output.summary.get("overall_accuracy"),
            "fixture_set_sha256": output.fixture_set_sha256,
            "judge_version": output.judge_version,
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
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
            observed_sha256=payload_sha256(target_context.output),
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
                observed_sha256=payload_sha256(verification_payload(verification_row)),
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
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def _build_triage_semantic_candidate_disagreements_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = TriageSemanticCandidateDisagreementsTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []

    target_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.evaluation_task_id,
        dependency_kind="target_task",
        expected_task_type="evaluate_semantic_candidate_extractor",
        expected_schema_name="evaluate_semantic_candidate_extractor_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Candidate disagreement triage must declare the requested evaluation "
            "task as a target_task dependency."
        ),
        rerun_message=(
            "Candidate evaluation task must be rerun after the context migration before triage."
        ),
    )
    refs.append(
        ContextRef(
            ref_key="target_task_output",
            ref_kind="task_output",
            summary=(
                "Typed shadow semantic candidate evaluation consumed by this disagreement triage."
            ),
            task_id=target_context.task_id,
            schema_name=target_context.output_schema_name,
            schema_version=target_context.output_schema_version,
            observed_sha256=payload_sha256(target_context.output),
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
                summary="Verifier record persisted for the shadow semantic disagreement gate.",
                task_id=task.id,
                verification_id=verification_row.id,
                observed_sha256=payload_sha256(verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            ContextRef(
                ref_key="disagreement_artifact",
                ref_kind="artifact",
                summary="Persisted shadow semantic disagreement report artifact.",
                task_id=task.id,
                artifact_id=artifact_row.id,
                artifact_kind=artifact_row.artifact_kind,
                schema_name=action.output_schema_name,
                schema_version=action.output_schema_version,
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    summary = TaskContextSummary(
        headline=(
            f"Shadow disagreement triage surfaced "
            f"{output.disagreement_report.issue_count} issue(s)."
        ),
        goal=(
            "Compress shadow semantic disagreements into reviewable issues "
            "without mutating live semantics."
        ),
        decision=output.recommendation.get("summary") or "Review the disagreement report.",
        next_action=output.recommendation.get("next_action") or "review_shadow_candidates",
        approval_state="not_required",
        verification_state=output.verification.outcome,
        metrics={
            "issue_count": output.disagreement_report.issue_count,
            "success_metric_pass_count": sum(
                1 for item in output.disagreement_report.success_metrics if item.passed
            ),
            "followup_count": len(output.disagreement_report.recommended_followups),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
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
            observed_sha256=payload_sha256(draft_context.output),
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
            observed_sha256=payload_sha256(verification_context.output),
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
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
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
                ContextRef(
                    ref_key=f"{source.source_type}_baseline_replay_run",
                    ref_kind="replay_run",
                    summary=(f"Baseline replay run for {source.source_type} used by triage."),
                    replay_run_id=baseline_run.id,
                    observed_sha256=payload_sha256(search_replay_run_payload(baseline_run)),
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
                    observed_sha256=payload_sha256(search_replay_run_payload(candidate_run)),
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
                observed_sha256=payload_sha256(verification_payload(verification_row)),
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
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    if output.repair_case_artifact_id is not None:
        repair_case_artifact_row = session.get(AgentTaskArtifact, output.repair_case_artifact_id)
        if repair_case_artifact_row is not None:
            refs.append(
                ContextRef(
                    ref_key="repair_case_artifact",
                    ref_kind="artifact",
                    summary=(
                        "Canonical repair case linking replay evidence to a bounded harness action."
                    ),
                    task_id=task.id,
                    artifact_id=repair_case_artifact_row.id,
                    artifact_kind=repair_case_artifact_row.artifact_kind,
                    schema_name="search_harness_repair_case",
                    schema_version="1.0",
                    observed_sha256=payload_sha256(repair_case_artifact_row.payload_json or {}),
                    source_updated_at=repair_case_artifact_row.created_at,
                    checked_at=now,
                    freshness_status=ContextFreshnessStatus.FRESH,
                )
            )

    repair_case = output.repair_case
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
        problem=repair_case.problem_statement if repair_case is not None else None,
        evidence=(
            f"{len(repair_case.evidence_refs)} evidence ref(s) captured in repair_case."
            if repair_case is not None
            else None
        ),
        proposed_change=(
            "No live change proposed; create a bounded draft harness if review proceeds."
        ),
        predicted_risk=(
            "Drafts are limited to retrieval-profile and reranker override surfaces."
            if repair_case is not None
            else None
        ),
        follow_up_status="not_started",
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
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
        expected_task_type=(
            "draft_harness_config_update",
            "draft_harness_config_update_from_optimization",
        ),
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
            observed_sha256=payload_sha256(draft_context.output),
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
            observed_sha256=payload_sha256(verification_context.output),
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
                observed_sha256=payload_sha256(artifact_row.payload_json or {}),
                source_updated_at=artifact_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )

    if output.follow_up_artifact_id is not None:
        follow_up_artifact_row = session.get(AgentTaskArtifact, output.follow_up_artifact_id)
        if follow_up_artifact_row is not None:
            refs.append(
                ContextRef(
                    ref_key="follow_up_evaluation_artifact",
                    ref_kind="artifact",
                    summary="Post-apply replay/evaluation evidence for the published harness.",
                    task_id=task.id,
                    artifact_id=follow_up_artifact_row.id,
                    artifact_kind=follow_up_artifact_row.artifact_kind,
                    schema_name="search_harness_follow_up_evidence",
                    schema_version="1.0",
                    observed_sha256=payload_sha256(follow_up_artifact_row.payload_json or {}),
                    source_updated_at=follow_up_artifact_row.created_at,
                    checked_at=now,
                    freshness_status=ContextFreshnessStatus.FRESH,
                )
            )

    verification_output = VerifyDraftHarnessConfigTaskOutput.model_validate(
        verification_context.output
    )
    follow_up_summary = output.follow_up_summary or {}
    summary = TaskContextSummary(
        headline=f"Applied verified harness {output.draft_harness_name} to live search.",
        goal="Publish a verified draft harness after approval without changing the workflow model.",
        decision=(
            follow_up_summary.get("summary")
            or "Live override written and ready for post-apply monitoring."
        ),
        next_action=(
            "Review follow-up evidence and keep the override."
            if follow_up_summary.get("recommendation") == "keep_override"
            else (
                "Monitor search traffic and run follow-up evaluation for "
                f"{output.draft_harness_name}."
            )
        ),
        approval_state="approved" if task.approved_at is not None else "pending",
        verification_state=verification_output.verification.outcome,
        problem=(
            verification_output.comprehension_gate.repair_case.problem_statement
            if verification_output.comprehension_gate is not None
            and verification_output.comprehension_gate.repair_case is not None
            else None
        ),
        evidence=(
            "Before/after evidence attached with recommendation: "
            f"{follow_up_summary.get('recommendation')}"
            if follow_up_summary
            else "Verification evidence attached; follow-up not run."
        ),
        proposed_change="Published "
        f"{output.draft_harness_name} derived from "
        f"{draft_context.output.get('draft', {}).get('base_harness_name')}.",
        predicted_risk=(
            verification_output.comprehension_gate.rollback_condition
            if verification_output.comprehension_gate is not None
            else None
        ),
        follow_up_status="completed" if follow_up_summary else "not_started",
        metrics={
            "total_shared_query_count": (verification_output.verification.metrics or {}).get(
                "total_shared_query_count"
            ),
            "regressed_count": verification_output.evaluation.get("total_regressed_count"),
            "improved_count": verification_output.evaluation.get("total_improved_count"),
            "follow_up_regressed_count": (
                (follow_up_summary.get("after") or {}).get("total_regressed_count")
            ),
            "follow_up_recommendation": follow_up_summary.get("recommendation"),
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
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
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


_CONTEXT_BUILDERS = {
    "generic": _build_generic_task_context,
    "latest_semantic_pass": _build_latest_semantic_pass_context,
    "initialize_workspace_ontology": _build_initialize_workspace_ontology_context,
    "get_active_ontology_snapshot": _build_get_active_ontology_snapshot_context,
    "discover_semantic_bootstrap_candidates": _build_discover_semantic_bootstrap_candidates_context,
    "export_semantic_supervision_corpus": _build_export_semantic_supervision_corpus_context,
    "evaluate_semantic_candidate_extractor": _build_evaluate_semantic_candidate_extractor_context,
    "build_shadow_semantic_graph": _build_build_shadow_semantic_graph_context,
    "evaluate_semantic_relation_extractor": _build_evaluate_semantic_relation_extractor_context,
    "plan_technical_report": _build_plan_technical_report_context,
    "build_report_evidence_cards": _build_build_report_evidence_cards_context,
    "prepare_report_agent_harness": _build_prepare_report_agent_harness_context,
    "draft_technical_report": _build_draft_technical_report_context,
    "verify_technical_report": _build_verify_technical_report_context,
    "evaluate_claim_support_judge": _build_evaluate_claim_support_judge_context,
    "prepare_semantic_generation_brief": _build_prepare_semantic_generation_brief_context,
    "draft_harness_config": _build_draft_harness_config_context,
    "evaluate_search_harness": _build_evaluate_search_harness_context,
    "verify_search_harness_evaluation": _build_verify_search_harness_evaluation_context,
    "draft_semantic_registry_update": _build_draft_semantic_registry_update_context,
    "draft_ontology_extension": _build_draft_ontology_extension_context,
    "draft_graph_promotions": _build_draft_graph_promotions_context,
    "verify_draft_harness_config": _build_verify_draft_harness_config_context,
    "verify_draft_semantic_registry_update": _build_verify_draft_semantic_registry_update_context,
    "verify_draft_ontology_extension": _build_verify_draft_ontology_extension_context,
    "verify_draft_graph_promotions": _build_verify_draft_graph_promotions_context,
    "draft_semantic_grounded_document": _build_draft_semantic_grounded_document_context,
    "verify_semantic_grounded_document": _build_verify_semantic_grounded_document_context,
    "triage_replay_regression": _build_triage_replay_regression_context,
    "triage_semantic_pass": _build_triage_semantic_pass_context,
    "triage_semantic_candidate_disagreements": (
        _build_triage_semantic_candidate_disagreements_context
    ),
    "triage_semantic_graph_disagreements": _build_triage_semantic_graph_disagreements_context,
    "apply_harness_config_update": _build_apply_harness_config_update_context,
    "apply_semantic_registry_update": _build_apply_semantic_registry_update_context,
    "apply_ontology_extension": _build_apply_ontology_extension_context,
    "apply_graph_promotions": _build_apply_graph_promotions_context,
    "build_document_fact_graph": _build_build_document_fact_graph_context,
}


def get_agent_task_context_builder(name: str | None):
    builder_name = name or "generic"
    try:
        return _CONTEXT_BUILDERS[builder_name]
    except KeyError as exc:
        available = ", ".join(sorted(_CONTEXT_BUILDERS))
        msg = f"Unknown agent task context builder '{builder_name}'. Available: {available}"
        raise ValueError(msg) from exc


def list_agent_task_context_builder_names() -> set[str]:
    return set(_CONTEXT_BUILDERS)


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
    builder = get_agent_task_context_builder(action.context_builder_name)
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
