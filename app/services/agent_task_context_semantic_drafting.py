from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskArtifact, AgentTaskVerification
from app.schemas.agent_tasks import (
    ContextFreshnessStatus,
    ContextRef,
    DraftSemanticGroundedDocumentTaskOutput,
    PrepareSemanticGenerationBriefTaskOutput,
    TaskContextEnvelope,
    TaskContextSummary,
    VerifySemanticGroundedDocumentTaskOutput,
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
    verification_payload,
)

SEMANTIC_DRAFTING_CONTEXT_BUILDER_SYMBOLS = {
    "prepare_semantic_generation_brief": "_build_prepare_semantic_generation_brief_context",
    "draft_semantic_grounded_document": "_build_draft_semantic_grounded_document_context",
    "verify_semantic_grounded_document": "_build_verify_semantic_grounded_document_context",
}


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


def build_semantic_drafting_context_builders(
    available_symbols: Mapping[str, object] | None = None,
) -> dict[str, AgentTaskContextBuilder]:
    symbols = {**(dict(available_symbols) if available_symbols else {}), **globals()}
    return resolve_context_builder_registry(
        symbols,
        builder_symbols=SEMANTIC_DRAFTING_CONTEXT_BUILDER_SYMBOLS,
        registry_name="semantic_drafting",
    )
