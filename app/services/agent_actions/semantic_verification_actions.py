from __future__ import annotations

from app.db.models import AgentTaskSideEffectLevel
from app.schemas.agent_tasks import (
    ApplyGraphPromotionsTaskInput,
    ApplyGraphPromotionsTaskOutput,
    ApplyOntologyExtensionTaskInput,
    ApplyOntologyExtensionTaskOutput,
    ApplySemanticRegistryUpdateTaskInput,
    ApplySemanticRegistryUpdateTaskOutput,
    TriageSemanticCandidateDisagreementsTaskInput,
    TriageSemanticCandidateDisagreementsTaskOutput,
    TriageSemanticGraphDisagreementsTaskInput,
    TriageSemanticGraphDisagreementsTaskOutput,
    TriageSemanticPassTaskInput,
    TriageSemanticPassTaskOutput,
    VerifyDraftGraphPromotionsTaskInput,
    VerifyDraftGraphPromotionsTaskOutput,
    VerifyDraftOntologyExtensionTaskInput,
    VerifyDraftOntologyExtensionTaskOutput,
    VerifyDraftSemanticRegistryUpdateTaskInput,
    VerifyDraftSemanticRegistryUpdateTaskOutput,
    VerifySemanticGroundedDocumentTaskInput,
    VerifySemanticGroundedDocumentTaskOutput,
)
from app.services.agent_actions.types import AgentTaskActionDefinition, AgentTaskExecutor


def build_semantic_verification_action_definitions(
    *,
    verify_draft_semantic_registry_update_executor: AgentTaskExecutor,
    verify_draft_ontology_extension_executor: AgentTaskExecutor,
    verify_draft_graph_promotions_executor: AgentTaskExecutor,
    verify_semantic_grounded_document_executor: AgentTaskExecutor,
    triage_semantic_pass_executor: AgentTaskExecutor,
    triage_semantic_candidate_disagreements_executor: AgentTaskExecutor,
    triage_semantic_graph_disagreements_executor: AgentTaskExecutor,
    apply_semantic_registry_update_executor: AgentTaskExecutor,
    apply_ontology_extension_executor: AgentTaskExecutor,
    apply_graph_promotions_executor: AgentTaskExecutor,
) -> dict[str, AgentTaskActionDefinition]:
    return {
        "verify_draft_semantic_registry_update": AgentTaskActionDefinition(
            task_type="verify_draft_semantic_registry_update",
            capability="semantic_memory",
            definition_kind="verifier",
            description=(
                "Verify an additive semantic registry draft against active "
                "documents without mutating live state."
            ),
            payload_model=VerifyDraftSemanticRegistryUpdateTaskInput,
            executor=verify_draft_semantic_registry_update_executor,
            output_model=VerifyDraftSemanticRegistryUpdateTaskOutput,
            output_schema_name="verify_draft_semantic_registry_update_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "max_regressed_document_count": 0,
                "max_failed_expectation_increase": 0,
                "min_improved_document_count": 1,
            },
            context_builder_name="verify_draft_semantic_registry_update",
        ),
        "verify_draft_ontology_extension": AgentTaskActionDefinition(
            task_type="verify_draft_ontology_extension",
            capability="semantic_memory",
            definition_kind="verifier",
            description="Verify an additive ontology extension draft against active documents.",
            payload_model=VerifyDraftOntologyExtensionTaskInput,
            executor=verify_draft_ontology_extension_executor,
            output_model=VerifyDraftOntologyExtensionTaskOutput,
            output_schema_name="verify_draft_ontology_extension_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "max_regressed_document_count": 0,
                "max_failed_expectation_increase": 0,
                "min_improved_document_count": 1,
            },
            context_builder_name="verify_draft_ontology_extension",
        ),
        "verify_draft_graph_promotions": AgentTaskActionDefinition(
            task_type="verify_draft_graph_promotions",
            capability="semantic_memory",
            definition_kind="verifier",
            description=(
                "Verify a graph promotion draft against current ontology and "
                "traceability constraints."
            ),
            payload_model=VerifyDraftGraphPromotionsTaskInput,
            executor=verify_draft_graph_promotions_executor,
            output_model=VerifyDraftGraphPromotionsTaskOutput,
            output_schema_name="verify_draft_graph_promotions_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "min_supporting_document_count": 2,
                "max_conflict_count": 0,
                "require_current_ontology_snapshot": True,
            },
            context_builder_name="verify_draft_graph_promotions",
        ),
        "verify_semantic_grounded_document": AgentTaskActionDefinition(
            task_type="verify_semantic_grounded_document",
            capability="semantic_memory",
            definition_kind="verifier",
            description=(
                "Verify that a semantic-grounded knowledge brief is fully "
                "traceable to typed semantic support."
            ),
            payload_model=VerifySemanticGroundedDocumentTaskInput,
            executor=verify_semantic_grounded_document_executor,
            output_model=VerifySemanticGroundedDocumentTaskOutput,
            output_schema_name="verify_semantic_grounded_document_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "max_unsupported_claim_count": 0,
                "require_full_claim_traceability": True,
                "require_full_concept_coverage": True,
            },
            context_builder_name="verify_semantic_grounded_document",
        ),
        "triage_semantic_pass": AgentTaskActionDefinition(
            task_type="triage_semantic_pass",
            capability="semantic_memory",
            definition_kind="workflow",
            description=(
                "Summarize active semantic-pass gaps, continuity changes, and bounded next actions."
            ),
            payload_model=TriageSemanticPassTaskInput,
            executor=triage_semantic_pass_executor,
            output_model=TriageSemanticPassTaskOutput,
            output_schema_name="triage_semantic_pass_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "low_evidence_threshold": 2,
            },
            context_builder_name="triage_semantic_pass",
        ),
        "triage_semantic_candidate_disagreements": AgentTaskActionDefinition(
            task_type="triage_semantic_candidate_disagreements",
            capability="semantic_memory",
            definition_kind="workflow",
            description=(
                "Compact shadow semantic disagreements into typed issues and "
                "bounded follow-up recommendations."
            ),
            payload_model=TriageSemanticCandidateDisagreementsTaskInput,
            executor=triage_semantic_candidate_disagreements_executor,
            output_model=TriageSemanticCandidateDisagreementsTaskOutput,
            output_schema_name="triage_semantic_candidate_disagreements_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "min_score": 0.34,
                "include_expected_only": False,
            },
            context_builder_name="triage_semantic_candidate_disagreements",
        ),
        "triage_semantic_graph_disagreements": AgentTaskActionDefinition(
            task_type="triage_semantic_graph_disagreements",
            capability="semantic_memory",
            definition_kind="workflow",
            description=(
                "Compact shadow semantic graph disagreements into typed issues and "
                "promotion follow-ups."
            ),
            payload_model=TriageSemanticGraphDisagreementsTaskInput,
            executor=triage_semantic_graph_disagreements_executor,
            output_model=TriageSemanticGraphDisagreementsTaskOutput,
            output_schema_name="triage_semantic_graph_disagreements_output",
            output_schema_version="1.0",
            input_example={
                "target_task_id": "00000000-0000-0000-0000-000000000000",
                "min_score": 0.45,
                "expected_only": True,
            },
            context_builder_name="triage_semantic_graph_disagreements",
        ),
        "apply_semantic_registry_update": AgentTaskActionDefinition(
            task_type="apply_semantic_registry_update",
            capability="semantic_memory",
            definition_kind="promotion",
            description="Apply a verified semantic registry update after approval.",
            payload_model=ApplySemanticRegistryUpdateTaskInput,
            executor=apply_semantic_registry_update_executor,
            side_effect_level=AgentTaskSideEffectLevel.PROMOTABLE.value,
            requires_approval=True,
            output_model=ApplySemanticRegistryUpdateTaskOutput,
            output_schema_name="apply_semantic_registry_update_output",
            output_schema_version="1.0",
            input_example={
                "draft_task_id": "00000000-0000-0000-0000-000000000000",
                "verification_task_id": "00000000-0000-0000-0000-000000000000",
                "reason": "Publish the verified registry update.",
            },
            context_builder_name="apply_semantic_registry_update",
        ),
        "apply_ontology_extension": AgentTaskActionDefinition(
            task_type="apply_ontology_extension",
            capability="semantic_memory",
            definition_kind="promotion",
            description="Apply a verified ontology extension as the new active workspace snapshot.",
            payload_model=ApplyOntologyExtensionTaskInput,
            executor=apply_ontology_extension_executor,
            side_effect_level=AgentTaskSideEffectLevel.PROMOTABLE.value,
            requires_approval=True,
            output_model=ApplyOntologyExtensionTaskOutput,
            output_schema_name="apply_ontology_extension_output",
            output_schema_version="1.0",
            input_example={
                "draft_task_id": "00000000-0000-0000-0000-000000000000",
                "verification_task_id": "00000000-0000-0000-0000-000000000000",
                "reason": "Publish the verified ontology extension.",
            },
            context_builder_name="apply_ontology_extension",
        ),
        "apply_graph_promotions": AgentTaskActionDefinition(
            task_type="apply_graph_promotions",
            capability="semantic_memory",
            definition_kind="promotion",
            description=(
                "Apply a verified semantic graph promotion draft as the new active graph snapshot."
            ),
            payload_model=ApplyGraphPromotionsTaskInput,
            executor=apply_graph_promotions_executor,
            side_effect_level=AgentTaskSideEffectLevel.PROMOTABLE.value,
            requires_approval=True,
            output_model=ApplyGraphPromotionsTaskOutput,
            output_schema_name="apply_graph_promotions_output",
            output_schema_version="1.0",
            input_example={
                "draft_task_id": "00000000-0000-0000-0000-000000000000",
                "verification_task_id": "00000000-0000-0000-0000-000000000000",
                "reason": "Publish the verified semantic graph memory snapshot.",
            },
            context_builder_name="apply_graph_promotions",
        ),
    }
