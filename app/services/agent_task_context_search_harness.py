from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskVerification,
    SearchReplayRun,
)
from app.schemas import agent_task_core as task_core
from app.schemas.agent_task_search_workflows import (
    ApplyHarnessConfigUpdateTaskOutput,
    DraftHarnessConfigUpdateTaskOutput,
    EvaluateSearchHarnessTaskOutput,
    TriageReplayRegressionTaskOutput,
    VerifyDraftHarnessConfigTaskOutput,
    VerifySearchHarnessEvaluationTaskOutput,
)
from app.services.agent_task_context_registry import (
    AgentTaskContextBuilder,
    resolve_context_builder_registry,
)
from app.services.agent_task_context_resolvers import (
    resolve_required_dependency_task_output_context,
    resolve_required_task_output_context,
)
from app.services.agent_task_context_store import (
    derive_freshness_status,
    get_context_artifact_row,
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


def _build_draft_harness_config_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = DraftHarnessConfigUpdateTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    if output.draft.source_task_id is not None:
        source_task = session.get(AgentTask, output.draft.source_task_id)
        if source_task is not None:
            from app.services.agent_task_action_lookup import get_agent_task_action

            source_action = get_agent_task_action(source_task.task_type)
            source_context_row = get_context_artifact_row(session, source_task.id)
            if source_context_row is not None:
                source_context = task_core.TaskContextEnvelope.model_validate(
                    source_context_row.payload_json or {}
                )
                observed_payload = source_context.output
            else:
                observed_payload = source_task.result_json or {}
            refs.append(
                task_core.ContextRef(
                    ref_key="source_task",
                    ref_kind="task_output",
                    summary="Source task that motivated this harness draft.",
                    task_id=source_task.id,
                    schema_name=source_action.output_schema_name,
                    schema_version=source_action.output_schema_version,
                    observed_sha256=payload_sha256(observed_payload),
                    source_updated_at=source_task.updated_at,
                    checked_at=now,
                    freshness_status=task_core.ContextFreshnessStatus.FRESH,
                )
            )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            task_core.ContextRef(
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
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    summary = task_core.TaskContextSummary(
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


def _build_verify_draft_harness_config_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = VerifyDraftHarnessConfigTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

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
        task_core.ContextRef(
            ref_key="draft_task_output",
            ref_kind="task_output",
            summary="Migrated draft-harness output consumed by this verification.",
            task_id=draft_context.task_id,
            schema_name=draft_context.output_schema_name,
            schema_version=draft_context.output_schema_version,
            observed_sha256=payload_sha256(draft_context.output),
            source_updated_at=draft_context.task_updated_at,
            checked_at=now,
            freshness_status=task_core.ContextFreshnessStatus.FRESH,
        )
    )

    for ref in draft_context.refs:
        if ref.ref_key != "draft_artifact":
            continue
        refs.append(
            task_core.ContextRef(
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
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
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
            task_core.ContextRef(
                ref_key="verification_record",
                ref_kind="verification_record",
                summary="Verifier record persisted for the draft review gate.",
                task_id=output.verification.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=payload_sha256(verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    verification_outcome = output.verification.outcome
    comprehension_gate = output.comprehension_gate
    changed_scopes = (
        comprehension_gate.predicted_blast_radius.get("changed_scopes") or []
        if comprehension_gate is not None
        else []
    )
    summary = task_core.TaskContextSummary(
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


def _build_triage_replay_regression_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = TriageReplayRegressionTaskOutput.model_validate(payload)
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
                    summary=(f"Baseline replay run for {source.source_type} used by triage."),
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
                    summary=(f"Candidate replay run for {source.source_type} used by triage."),
                    replay_run_id=candidate_run.id,
                    observed_sha256=payload_sha256(search_replay_run_payload(candidate_run)),
                    source_updated_at=candidate_run.completed_at or candidate_run.created_at,
                    checked_at=now,
                    freshness_status=task_core.ContextFreshnessStatus.FRESH,
                )
            )

    verification_row = session.get(AgentTaskVerification, output.verification.verification_id)
    if verification_row is not None:
        refs.append(
            task_core.ContextRef(
                ref_key="verification_record",
                ref_kind="verification_record",
                summary="Verifier record captured for the shadow-mode triage gate.",
                task_id=task.id,
                verification_id=verification_row.id,
                observed_sha256=payload_sha256(verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            task_core.ContextRef(
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
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    if output.repair_case_artifact_id is not None:
        repair_case_artifact_row = session.get(AgentTaskArtifact, output.repair_case_artifact_id)
        if repair_case_artifact_row is not None:
            refs.append(
                task_core.ContextRef(
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
                    freshness_status=task_core.ContextFreshnessStatus.FRESH,
                )
            )

    repair_case = output.repair_case
    summary = task_core.TaskContextSummary(
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


def _build_apply_harness_config_update_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = ApplyHarnessConfigUpdateTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

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
        task_core.ContextRef(
            ref_key="draft_task_output",
            ref_kind="task_output",
            summary="Migrated draft-harness output applied to the live override store.",
            task_id=draft_context.task_id,
            schema_name=draft_context.output_schema_name,
            schema_version=draft_context.output_schema_version,
            observed_sha256=payload_sha256(draft_context.output),
            source_updated_at=draft_context.task_updated_at,
            checked_at=now,
            freshness_status=task_core.ContextFreshnessStatus.FRESH,
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
        task_core.ContextRef(
            ref_key="verification_task_output",
            ref_kind="task_output",
            summary="Migrated verification output that approved this live apply step.",
            task_id=verification_context.task_id,
            schema_name=verification_context.output_schema_name,
            schema_version=verification_context.output_schema_version,
            observed_sha256=payload_sha256(verification_context.output),
            source_updated_at=verification_context.task_updated_at,
            checked_at=now,
            freshness_status=task_core.ContextFreshnessStatus.FRESH,
        )
    )

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            task_core.ContextRef(
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
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    if output.follow_up_artifact_id is not None:
        follow_up_artifact_row = session.get(AgentTaskArtifact, output.follow_up_artifact_id)
        if follow_up_artifact_row is not None:
            refs.append(
                task_core.ContextRef(
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
                    freshness_status=task_core.ContextFreshnessStatus.FRESH,
                )
            )

    verification_output = VerifyDraftHarnessConfigTaskOutput.model_validate(
        verification_context.output
    )
    follow_up_summary = output.follow_up_summary or {}
    summary = task_core.TaskContextSummary(
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
