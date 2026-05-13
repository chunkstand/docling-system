from __future__ import annotations

from app.schemas.agent_tasks import (
    TriageSemanticCandidateDisagreementsTaskInput,
    TriageSemanticCandidateDisagreementsTaskOutput,
    TriageSemanticGraphDisagreementsTaskInput,
    TriageSemanticGraphDisagreementsTaskOutput,
    TriageSemanticPassTaskInput,
    TriageSemanticPassTaskOutput,
    VerifySemanticGroundedDocumentTaskInput,
    VerifySemanticGroundedDocumentTaskOutput,
)
from app.services.agent_actions.types import AgentTaskActionDefinition, AgentTaskExecutor


def build_semantic_verification_action_definitions(
    *,
    verify_semantic_grounded_document_executor: AgentTaskExecutor,
    triage_semantic_pass_executor: AgentTaskExecutor,
    triage_semantic_candidate_disagreements_executor: AgentTaskExecutor,
    triage_semantic_graph_disagreements_executor: AgentTaskExecutor,
) -> dict[str, AgentTaskActionDefinition]:
    return {
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
    }
