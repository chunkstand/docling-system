from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskArtifact, AgentTaskVerification, SearchReplayRun
from app.schemas import agent_task_core as task_core
from app.schemas.agent_task_search_workflows import TriageReplayRegressionTaskOutput
from app.services.agent_task_context_store import (
    derive_freshness_status,
    payload_sha256,
    search_harness_evaluation_context_ref,
    search_replay_run_payload,
    verification_payload,
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
