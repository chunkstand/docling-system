from __future__ import annotations

from pathlib import Path

import pytest

from app.services.semantic_registry import (
    semantic_registry_from_payload,
    validate_semantic_relation_instance,
    write_semantic_registry_payload,
)


def test_write_semantic_registry_payload_rejects_invalid_contract(tmp_path: Path) -> None:
    invalid_payload = {
        "registry_name": "semantic_registry",
        "registry_version": "alpha.1",
        "categories": [],
        "concepts": [
            {
                "concept_key": "integration_threshold",
                "preferred_label": "Integration Threshold",
                "category_keys": ["missing_category"],
                "aliases": ["integration threshold"],
            }
        ],
    }

    with pytest.raises(ValueError, match="unknown category_key"):
        write_semantic_registry_payload(
            invalid_payload, registry_path=tmp_path / "semantic_registry.yaml"
        )

    assert not (tmp_path / "semantic_registry.yaml").exists()


def test_semantic_registry_from_payload_rejects_unknown_relation_entity_type() -> None:
    invalid_payload = {
        "registry_name": "portable_upper_ontology",
        "registry_version": "portable-upper-ontology-v1",
        "categories": [],
        "concepts": [],
        "entity_types": [
            {"entity_type": "document", "preferred_label": "Document"},
            {"entity_type": "concept", "preferred_label": "Concept"},
        ],
        "relations": [
            {
                "relation_key": "concept_depends_on_concept",
                "preferred_label": "Concept Depends On Concept",
                "domain_entity_types": ["concept"],
                "range_entity_types": ["literal"],
            }
        ],
    }

    with pytest.raises(ValueError, match="unknown entity_type"):
        semantic_registry_from_payload(invalid_payload)


def test_validate_semantic_relation_instance_enforces_domain_and_range() -> None:
    registry = semantic_registry_from_payload(
        {
            "registry_name": "portable_upper_ontology",
            "registry_version": "portable-upper-ontology-v1",
            "categories": [],
            "concepts": [],
            "entity_types": [
                {"entity_type": "document", "preferred_label": "Document"},
                {"entity_type": "concept", "preferred_label": "Concept"},
                {"entity_type": "literal", "preferred_label": "Literal"},
            ],
            "relations": [
                {
                    "relation_key": "document_mentions_concept",
                    "preferred_label": "Document Mentions Concept",
                    "domain_entity_types": ["document"],
                    "range_entity_types": ["concept"],
                    "allow_literal_object": False,
                }
            ],
        }
    )

    valid = validate_semantic_relation_instance(
        registry,
        relation_key="document_mentions_concept",
        subject_entity_key="document:abc",
        object_entity_key="concept:integration_threshold",
    )
    invalid = validate_semantic_relation_instance(
        registry,
        relation_key="document_mentions_concept",
        subject_entity_key="concept:integration_threshold",
        object_entity_key="document:abc",
    )

    assert valid == []
    assert any("subject entity type" in reason for reason in invalid)
    assert any("object entity type" in reason for reason in invalid)
