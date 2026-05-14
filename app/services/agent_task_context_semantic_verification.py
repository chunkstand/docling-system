from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskArtifact, AgentTaskVerification
from app.schemas.agent_task_core import (
    ContextFreshnessStatus,
    ContextRef,
    TaskContextEnvelope,
    TaskContextSummary,
)
from app.schemas.agent_task_semantic_graph import TriageSemanticCandidateDisagreementsTaskOutput
from app.schemas.agent_task_semantics import TriageSemanticPassTaskOutput
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
    verification_payload,
)

SEMANTIC_VERIFICATION_CONTEXT_BUILDER_SYMBOLS = {
    "triage_semantic_pass": "_build_triage_semantic_pass_context",
    "triage_semantic_candidate_disagreements": (
        "_build_triage_semantic_candidate_disagreements_context"
    ),
}


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


def build_semantic_verification_context_builders(
    available_symbols: Mapping[str, object] | None = None,
) -> dict[str, AgentTaskContextBuilder]:
    symbols = {**(dict(available_symbols) if available_symbols else {}), **globals()}
    return resolve_context_builder_registry(
        symbols,
        builder_symbols=SEMANTIC_VERIFICATION_CONTEXT_BUILDER_SYMBOLS,
        registry_name="semantic_verification",
    )
