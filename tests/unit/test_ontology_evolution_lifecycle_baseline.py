from __future__ import annotations

from uuid import uuid4

import pytest

from app.schemas.agent_task_semantics import (
    ApplyOntologyExtensionTaskOutput,
    DraftOntologyExtensionTaskInput,
    DraftOntologyExtensionTaskOutput,
    SemanticRegistryUpdateOperation,
    VerifyDraftOntologyExtensionTaskOutput,
)
from app.services.semantic_registry_operation_contracts import (
    SEMANTIC_REGISTRY_OPERATION_CONTRACT_VERSION,
    SUPPORTED_SEMANTIC_REGISTRY_OPERATION_TYPES,
    validate_semantic_registry_operations,
)
from app.services.semantic_registry_operation_mutations import apply_semantic_registry_operations
from tests.unit.agent_task_context_semantic_governance_support import (
    apply_ontology_output_payload,
    draft_ontology_output_payload,
    manual_lifecycle_draft_ontology_output_payload,
    verify_draft_ontology_output_payload,
)


def _base_ontology_payload() -> dict:
    return {
        "registry_name": "portable_upper_ontology",
        "registry_version": "portable-upper-ontology-v1",
        "upper_ontology_version": "portable-upper-ontology-v1",
        "categories": [],
        "concepts": [
            {"concept_key": "incident_latency", "preferred_label": "Incident Latency"},
            {
                "concept_key": "vendor_escalation_owner",
                "preferred_label": "Vendor Escalation Owner",
            },
            {
                "concept_key": "legacy_escalation_owner",
                "preferred_label": "Legacy Escalation Owner",
                "aliases": ["legacy owner"],
            },
            {
                "concept_key": "secondary_escalation_owner",
                "preferred_label": "Secondary Escalation Owner",
            },
            {"concept_key": "legacy_control", "preferred_label": "Legacy Control"},
            {"concept_key": "governance_control", "preferred_label": "Governance Control"},
            {"concept_key": "manual_triage_gate", "preferred_label": "Manual Triage Gate"},
            {
                "concept_key": "incident_latency_legacy",
                "preferred_label": "Incident Latency Legacy",
            },
        ],
        "relations": [
            {
                "relation_key": "document_mentions_concept",
                "preferred_label": "Document Mentions Concept",
            }
        ],
    }


def _lifecycle_operations() -> list[dict]:
    return [
        {
            "operation_id": "split:incident_latency",
            "operation_type": "split_concept",
            "concept_key": "incident_latency",
            "source_concept_keys": [],
            "successor_concepts": [
                {
                    "concept_key": "incident_ack_latency",
                    "preferred_label": "Incident Ack Latency",
                    "aliases": ["ack latency"],
                    "category_keys": [],
                    "scope_note": None,
                },
                {
                    "concept_key": "incident_resolution_latency",
                    "preferred_label": "Incident Resolution Latency",
                    "aliases": ["resolution latency"],
                    "category_keys": [],
                    "scope_note": None,
                },
            ],
        },
        {
            "operation_id": "merge:vendor_escalation_owner",
            "operation_type": "merge_concept",
            "concept_key": "vendor_escalation_owner",
            "source_concept_keys": [
                "legacy_escalation_owner",
                "secondary_escalation_owner",
            ],
            "successor_concepts": [],
        },
        {
            "operation_id": "deprecate:legacy_control",
            "operation_type": "deprecate_concept",
            "concept_key": "legacy_control",
            "source_concept_keys": [],
            "successor_concepts": [
                {
                    "concept_key": "governance_control",
                    "preferred_label": None,
                    "aliases": [],
                    "category_keys": [],
                    "scope_note": None,
                }
            ],
        },
        {
            "operation_id": "replace:manual_triage_gate:triage_decision_gate",
            "operation_type": "replace_concept",
            "concept_key": "manual_triage_gate",
            "source_concept_keys": [],
            "successor_concepts": [
                {
                    "concept_key": "triage_decision_gate",
                    "preferred_label": "Triage Decision Gate",
                    "aliases": [],
                    "category_keys": [],
                    "scope_note": None,
                }
            ],
        },
        {
            "operation_id": "migrate:incident_latency_legacy",
            "operation_type": "migrate_concept",
            "concept_key": "incident_latency_legacy",
            "source_concept_keys": [],
            "successor_concepts": [
                {
                    "concept_key": "incident_ack_latency",
                    "preferred_label": None,
                    "aliases": [],
                    "category_keys": [],
                    "scope_note": None,
                },
                {
                    "concept_key": "incident_resolution_latency",
                    "preferred_label": None,
                    "aliases": [],
                    "category_keys": [],
                    "scope_note": None,
                },
            ],
        },
    ]


def test_validate_semantic_registry_operations_accepts_structured_lifecycle_surface() -> None:
    validate_semantic_registry_operations(_lifecycle_operations())

    assert SUPPORTED_SEMANTIC_REGISTRY_OPERATION_TYPES == (
        "add_concept",
        "add_alias",
        "add_category_binding",
        "split_concept",
        "merge_concept",
        "deprecate_concept",
        "replace_concept",
        "migrate_concept",
    )


def test_validate_semantic_registry_operations_rejects_prose_only_lifecycle_payloads() -> None:
    with pytest.raises(ValueError) as excinfo:
        validate_semantic_registry_operations(
            [
                {
                    "operation_id": "deprecate:legacy_control",
                    "operation_type": "deprecate_concept",
                    "concept_key": "legacy_control",
                }
            ]
        )

    message = str(excinfo.value)
    assert "deprecate_concept operations require successor_concepts" in message
    assert "docs/ontology_evolution_lifecycle_milestone_plan.md" in message


def test_apply_semantic_registry_operations_tracks_lifecycle_lineage() -> None:
    effective_ontology = apply_semantic_registry_operations(
        _base_ontology_payload(),
        _lifecycle_operations(),
        proposed_registry_version="portable-upper-ontology-v1.1",
    )
    concepts_by_key = {
        concept["concept_key"]: concept for concept in effective_ontology["concepts"]
    }

    assert effective_ontology["registry_version"] == "portable-upper-ontology-v1.1"
    assert (
        effective_ontology["operation_contract_version"]
        == SEMANTIC_REGISTRY_OPERATION_CONTRACT_VERSION
    )
    assert concepts_by_key["incident_latency"]["lifecycle_status"] == "split"
    assert concepts_by_key["incident_latency"]["successor_concept_keys"] == [
        "incident_ack_latency",
        "incident_resolution_latency",
    ]
    assert sorted(concepts_by_key["incident_ack_latency"]["predecessor_concept_keys"]) == [
        "incident_latency",
        "incident_latency_legacy",
    ]
    assert concepts_by_key["legacy_escalation_owner"]["lifecycle_status"] == "merged"
    assert concepts_by_key["legacy_escalation_owner"]["successor_concept_keys"] == [
        "vendor_escalation_owner"
    ]
    assert "Legacy Escalation Owner" in concepts_by_key["vendor_escalation_owner"]["aliases"]
    assert concepts_by_key["legacy_control"]["lifecycle_status"] == "deprecated"
    assert concepts_by_key["governance_control"]["predecessor_concept_keys"] == [
        "legacy_control"
    ]
    assert concepts_by_key["manual_triage_gate"]["lifecycle_status"] == "replaced"
    assert concepts_by_key["triage_decision_gate"]["predecessor_concept_keys"] == [
        "manual_triage_gate"
    ]
    assert "Manual Triage Gate" in concepts_by_key["triage_decision_gate"]["aliases"]
    assert concepts_by_key["incident_latency_legacy"]["lifecycle_status"] == "migrated"


def test_draft_ontology_extension_input_requires_source_task_or_operations() -> None:
    with pytest.raises(ValueError, match="require source_task_id or explicit operations"):
        DraftOntologyExtensionTaskInput.model_validate({})

    replace_operation = SemanticRegistryUpdateOperation.model_validate(
        {
            "operation_id": "replace:legacy_control:governance_control",
            "operation_type": "replace_concept",
            "concept_key": "legacy_control",
            "successor_concepts": [{"concept_key": "governance_control"}],
        }
    )
    payload = DraftOntologyExtensionTaskInput.model_validate(
        {
            "rationale": "replace the legacy concept with a governed successor",
            "operations": [replace_operation.model_dump(mode="json")],
        }
    )

    assert payload.source_task_id is None
    assert payload.operations[0].operation_type == "replace_concept"


def test_ontology_extension_task_outputs_preserve_contract_fields_with_lifecycle_version() -> None:
    source_task_id = uuid4()
    additive_draft_output = DraftOntologyExtensionTaskOutput.model_validate(
        draft_ontology_output_payload(
            source_task_id=source_task_id,
            source_task_type="discover_semantic_bootstrap_candidates",
        )
    )
    lifecycle_draft_output = DraftOntologyExtensionTaskOutput.model_validate(
        manual_lifecycle_draft_ontology_output_payload()
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

    assert additive_draft_output.draft.source_task_id == source_task_id
    assert (
        additive_draft_output.draft.operation_contract_version
        == SEMANTIC_REGISTRY_OPERATION_CONTRACT_VERSION
    )
    assert additive_draft_output.draft.operations[0].operation_type == "add_concept"

    assert lifecycle_draft_output.draft.source_task_id is None
    assert lifecycle_draft_output.draft.document_ids == []
    assert (
        lifecycle_draft_output.draft.operation_contract_version
        == SEMANTIC_REGISTRY_OPERATION_CONTRACT_VERSION
    )
    assert lifecycle_draft_output.draft.operations[0].operation_type == "replace_concept"

    assert verify_output.verification.outcome == "passed"
    assert (
        verify_output.draft.operation_contract_version
        == SEMANTIC_REGISTRY_OPERATION_CONTRACT_VERSION
    )
    assert apply_output.applied_ontology_version == "portable-upper-ontology-v1.1"
    assert apply_output.applied_operations[0].operation_type == "add_concept"
