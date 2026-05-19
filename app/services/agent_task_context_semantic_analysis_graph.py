from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskArtifact, AgentTaskVerification
from app.schemas import agent_task_core as task_core
from app.schemas.agent_task_semantic_graph import (
    BuildDocumentFactGraphTaskOutput,
    BuildShadowSemanticGraphTaskOutput,
    EvaluateSemanticRelationExtractorTaskOutput,
    TriageSemanticGraphDisagreementsTaskOutput,
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

SEMANTIC_ANALYSIS_GRAPH_CONTEXT_BUILDER_SYMBOLS = {
    "build_document_fact_graph": "_build_build_document_fact_graph_context",
    "build_shadow_semantic_graph": "_build_build_shadow_semantic_graph_context",
    "evaluate_semantic_relation_extractor": (
        "_build_evaluate_semantic_relation_extractor_context"
    ),
    "triage_semantic_graph_disagreements": (
        "_build_triage_semantic_graph_disagreements_context"
    ),
}


def _build_build_document_fact_graph_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = BuildDocumentFactGraphTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            task_core.ContextRef(
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
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    summary = task_core.TaskContextSummary(
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


def _build_build_shadow_semantic_graph_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = BuildShadowSemanticGraphTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            task_core.ContextRef(
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
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    graph = output.shadow_graph
    summary = task_core.TaskContextSummary(
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


def _build_evaluate_semantic_relation_extractor_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = EvaluateSemanticRelationExtractorTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

    artifact_row = session.get(AgentTaskArtifact, output.artifact_id)
    if artifact_row is not None:
        refs.append(
            task_core.ContextRef(
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
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    summary_payload = output.summary
    summary = task_core.TaskContextSummary(
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


def _build_triage_semantic_graph_disagreements_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> task_core.TaskContextEnvelope:
    output = TriageSemanticGraphDisagreementsTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[task_core.ContextRef] = []

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
        task_core.ContextRef(
            ref_key="target_task_output",
            ref_kind="task_output",
            summary="Typed graph evaluation output consumed by this disagreement triage.",
            task_id=evaluation_context.task_id,
            schema_name=evaluation_context.output_schema_name,
            schema_version=evaluation_context.output_schema_version,
            observed_sha256=payload_sha256(evaluation_context.output),
            source_updated_at=evaluation_context.task_updated_at,
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
                summary="Verifier record for the bounded shadow-graph disagreement gate.",
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
                freshness_status=task_core.ContextFreshnessStatus.FRESH,
            )
        )

    report = output.disagreement_report
    summary = task_core.TaskContextSummary(
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


def build_semantic_analysis_graph_context_builders(
    available_symbols: Mapping[str, object] | None = None,
) -> dict[str, AgentTaskContextBuilder]:
    symbols = {**(dict(available_symbols) if available_symbols else {}), **globals()}
    return resolve_context_builder_registry(
        symbols,
        builder_symbols=SEMANTIC_ANALYSIS_GRAPH_CONTEXT_BUILDER_SYMBOLS,
        registry_name="semantic_analysis_graph",
    )
