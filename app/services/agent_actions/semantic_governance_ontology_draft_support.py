from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.public.agent_tasks import AgentTask
from app.schemas import agent_task_semantic_graph as graph_schemas
from app.schemas.agent_task_semantics import (
    DraftOntologyExtensionTaskInput,
    TriageSemanticPassTaskOutput,
)


def draft_ontology_extension_from_source_task(
    session: Session,
    task: AgentTask,
    payload: DraftOntologyExtensionTaskInput,
    *,
    resolve_required_dependency_task_output_context_func,
    draft_ontology_extension_func,
    draft_ontology_extension_from_bootstrap_report_func,
) -> dict:
    source_task = session.get(AgentTask, payload.source_task_id)
    if source_task is None:
        raise ValueError(f"Ontology extension source task not found: {payload.source_task_id}")
    if source_task.task_type == "triage_semantic_pass":
        source_context = resolve_required_dependency_task_output_context_func(
            session,
            task_id=task.id,
            depends_on_task_id=payload.source_task_id,
            dependency_kind="source_task",
            expected_task_type="triage_semantic_pass",
            expected_schema_name="triage_semantic_pass_output",
            expected_schema_version="1.0",
            dependency_error_message=(
                "Ontology extension draft must declare the semantic triage task as "
                "a source_task dependency."
            ),
            rerun_message=(
                "Semantic triage task must be rerun after the context migration "
                "before ontology drafting."
            ),
        )
        triage_output = TriageSemanticPassTaskOutput.model_validate(source_context.output)
        return draft_ontology_extension_func(
            session,
            triage_output.gap_report.model_dump(mode="json"),
            source_task_id=payload.source_task_id,
            source_task_type=source_task.task_type,
            proposed_ontology_version=payload.proposed_ontology_version,
            rationale=payload.rationale,
            candidate_ids=payload.candidate_ids,
        )
    if source_task.task_type == "discover_semantic_bootstrap_candidates":
        source_context = resolve_required_dependency_task_output_context_func(
            session,
            task_id=task.id,
            depends_on_task_id=payload.source_task_id,
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
        bootstrap_output = (
            graph_schemas.DiscoverSemanticBootstrapCandidatesTaskOutput.model_validate(
                source_context.output
            )
        )
        return draft_ontology_extension_from_bootstrap_report_func(
            session,
            bootstrap_output.report.model_dump(mode="json"),
            source_task_id=payload.source_task_id,
            source_task_type=source_task.task_type,
            proposed_ontology_version=payload.proposed_ontology_version,
            rationale=payload.rationale,
            candidate_ids=payload.candidate_ids,
        )
    raise ValueError(
        "Ontology extension drafting only supports triage_semantic_pass, "
        "discover_semantic_bootstrap_candidates, or explicit operations."
    )


__all__ = ["draft_ontology_extension_from_source_task"]
