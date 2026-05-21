from __future__ import annotations

from uuid import uuid4

import pytest

from app.schemas.agent_task_semantics import (
    ApplyOntologyExtensionTaskOutput,
    DraftOntologyExtensionTaskOutput,
    VerifyDraftOntologyExtensionTaskOutput,
)
from app.services.semantic_registry_operation_contracts import (
    SUPPORTED_SEMANTIC_REGISTRY_OPERATION_TYPES,
    validate_semantic_registry_operations,
)
from tests.unit.agent_task_context_semantic_governance_support import (
    apply_ontology_output_payload,
    draft_ontology_output_payload,
    verify_draft_ontology_output_payload,
)


def test_validate_semantic_registry_operations_rejects_non_additive_lifecycle_types() -> None:
    with pytest.raises(ValueError) as excinfo:
        validate_semantic_registry_operations(
            [
                {
                    "operation_id": "merge:incident_latency:incident_response_latency",
                    "operation_type": "merge_concept",
                    "concept_key": "incident_latency",
                }
            ]
        )

    message = str(excinfo.value)
    assert "Non-additive ontology lifecycle operations are not supported" in message
    assert "merge_concept" in message
    assert "docs/ontology_evolution_lifecycle_milestone_plan.md" in message


def test_validate_semantic_registry_operations_reports_supported_additive_surface() -> None:
    validate_semantic_registry_operations(
        [
            {
                "operation_id": "op-1",
                "operation_type": "add_concept",
                "concept_key": "incident_response_latency",
            },
            {
                "operation_id": "op-2",
                "operation_type": "add_alias",
                "concept_key": "incident_response_latency",
                "alias_text": "incident response latency",
            },
            {
                "operation_id": "op-3",
                "operation_type": "add_category_binding",
                "concept_key": "incident_response_latency",
                "category_key": "integration_governance",
            },
        ]
    )

    assert SUPPORTED_SEMANTIC_REGISTRY_OPERATION_TYPES == (
        "add_concept",
        "add_alias",
        "add_category_binding",
    )


def test_ontology_extension_task_outputs_preserve_current_additive_contract_fields() -> None:
    source_task_id = uuid4()
    draft_output = DraftOntologyExtensionTaskOutput.model_validate(
        draft_ontology_output_payload(
            source_task_id=source_task_id,
            source_task_type="discover_semantic_bootstrap_candidates",
        )
    )
    verify_output = VerifyDraftOntologyExtensionTaskOutput.model_validate(
        verify_draft_ontology_output_payload(draft_task_id=uuid4())
    )
    apply_output = ApplyOntologyExtensionTaskOutput.model_validate(
        apply_ontology_output_payload(
            draft_task_id=uuid4(),
            verification_task_id=uuid4(),
        )
    )

    assert draft_output.draft.source_task_id == source_task_id
    assert draft_output.draft.base_ontology_version == "portable-upper-ontology-v1"
    assert draft_output.draft.proposed_ontology_version == "portable-upper-ontology-v1.1"
    assert draft_output.draft.ontology_slice_count == 5
    assert draft_output.draft.competency_family_count == 4
    assert draft_output.draft.operations[0].operation_type == "add_concept"

    assert verify_output.verification.outcome == "passed"
    assert verify_output.draft.operations[0].operation_type == "add_concept"
    assert verify_output.draft.contract_version == "portable-upper-ontology-v1"

    assert apply_output.applied_ontology_version == "portable-upper-ontology-v1.1"
    assert apply_output.ontology_slice_count == 5
    assert apply_output.competency_family_count == 4
    assert apply_output.applied_operations[0].operation_type == "add_concept"
