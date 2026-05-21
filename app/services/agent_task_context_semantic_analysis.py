from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.orm import Session

import app.services.agent_task_context_semantic_analysis_graph as graph_owner
from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTask, AgentTaskArtifact
from app.schemas import agent_task_core as task_core
from app.schemas.agent_task_semantic_graph import (
    DiscoverSemanticBootstrapCandidatesTaskOutput,
    EvaluateSemanticCandidateExtractorTaskOutput,
    ExportSemanticSupervisionCorpusTaskOutput,
)
from app.schemas.agent_task_semantics import (
    GetActiveOntologySnapshotTaskOutput,
    InitializeWorkspaceOntologyTaskOutput,
    LatestSemanticPassTaskOutput,
)
from app.services.agent_task_context_registry import (
    AgentTaskContextBuilder,
    compose_context_builder_registries,
    resolve_context_builder_registry,
)
from app.services.agent_task_context_store import (
    derive_freshness_status,
    payload_sha256,
)

SEMANTIC_ANALYSIS_CONTEXT_BUILDER_SYMBOLS = {
    "latest_semantic_pass": "_build_latest_semantic_pass_context",
    "initialize_workspace_ontology": "_build_initialize_workspace_ontology_context",
    "get_active_ontology_snapshot": "_build_get_active_ontology_snapshot_context",
    "discover_semantic_bootstrap_candidates": (
        "_build_discover_semantic_bootstrap_candidates_context"
    ),
    "export_semantic_supervision_corpus": (
        "_build_export_semantic_supervision_corpus_context"
    ),
    "evaluate_semantic_candidate_extractor": (
        "_build_evaluate_semantic_candidate_extractor_context"
    ),
}


def _build_latest_semantic_pass_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    del session
    output = LatestSemanticPassTaskOutput.model_validate(payload)
    semantic_pass = output.semantic_pass
    now = utcnow()
    summary = task_core.TaskContextSummary(
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
    return task_core.TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=task_core.ContextFreshnessStatus.FRESH,
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
) -> task_core.TaskContextEnvelope:
    output = InitializeWorkspaceOntologyTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            task_core.ContextRef(
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
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    snapshot = output.snapshot
    summary = task_core.TaskContextSummary(
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


def _build_get_active_ontology_snapshot_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
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
    summary = task_core.TaskContextSummary(
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
    return task_core.TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=task_core.ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=[],
        output=output.model_dump(mode="json"),
    )


def _build_discover_semantic_bootstrap_candidates_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = DiscoverSemanticBootstrapCandidatesTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            task_core.ContextRef(
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
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    summary = task_core.TaskContextSummary(
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


def _build_export_semantic_supervision_corpus_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = ExportSemanticSupervisionCorpusTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            task_core.ContextRef(
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
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    summary = task_core.TaskContextSummary(
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


def _build_evaluate_semantic_candidate_extractor_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = EvaluateSemanticCandidateExtractorTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            task_core.ContextRef(
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
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    summary = task_core.TaskContextSummary(
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


def build_semantic_analysis_context_builders(
    available_symbols: Mapping[str, object] | None = None,
) -> dict[str, AgentTaskContextBuilder]:
    symbols = {**(dict(available_symbols) if available_symbols else {}), **globals()}
    return compose_context_builder_registries(
        resolve_context_builder_registry(
            symbols,
            builder_symbols=SEMANTIC_ANALYSIS_CONTEXT_BUILDER_SYMBOLS,
            registry_name="semantic_analysis",
        ),
        graph_owner.build_semantic_analysis_graph_context_builders(available_symbols),
    )
