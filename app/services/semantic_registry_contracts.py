from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import yaml

from app.core.text import collapse_whitespace

_NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")
_DEFAULT_ENTITY_TYPE_DEFINITIONS = (
    ("document", "Document"),
    ("concept", "Concept"),
    ("literal", "Literal"),
)


def normalize_semantic_text(value: str | None) -> str:
    collapsed = collapse_whitespace((value or "").lower())
    return collapse_whitespace(_NORMALIZE_PATTERN.sub(" ", collapsed))


def metadata_without(payload: dict[str, Any], excluded: set[str]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key not in excluded}


@dataclass(frozen=True)
class SemanticRegistryTermDefinition:
    text: str
    normalized_text: str
    term_kind: str


@dataclass(frozen=True)
class SemanticRegistryConceptDefinition:
    concept_key: str
    preferred_label: str
    scope_note: str | None
    metadata: dict[str, Any]
    terms: tuple[SemanticRegistryTermDefinition, ...]
    category_keys: tuple[str, ...]


@dataclass(frozen=True)
class SemanticRegistryCategoryDefinition:
    category_key: str
    preferred_label: str
    scope_note: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SemanticRegistryEntityTypeDefinition:
    entity_type: str
    preferred_label: str
    scope_note: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SemanticRegistryRelationDefinition:
    relation_key: str
    preferred_label: str
    scope_note: str | None
    domain_entity_types: tuple[str, ...]
    range_entity_types: tuple[str, ...]
    symmetric: bool
    allow_literal_object: bool
    cardinality_hint: str | None
    inverse_relation_key: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SemanticRegistry:
    registry_name: str
    registry_version: str
    sha256: str
    categories: tuple[SemanticRegistryCategoryDefinition, ...]
    concepts: tuple[SemanticRegistryConceptDefinition, ...]
    entity_types: tuple[SemanticRegistryEntityTypeDefinition, ...] = ()
    relations: tuple[SemanticRegistryRelationDefinition, ...] = ()
    snapshot_id: UUID | None = None
    upper_ontology_version: str | None = None


def validate_semantic_registry_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Semantic registry must be a mapping.")
    return payload


def _concept_terms(concept_payload: dict[str, Any]) -> tuple[SemanticRegistryTermDefinition, ...]:
    preferred_label = collapse_whitespace(str(concept_payload.get("preferred_label") or ""))
    if not preferred_label:
        raise ValueError("Semantic concepts require a non-empty preferred_label.")

    raw_aliases = concept_payload.get("aliases") or []
    if raw_aliases and not isinstance(raw_aliases, list):
        raise ValueError("Semantic concept aliases must be a list.")

    terms: list[SemanticRegistryTermDefinition] = []
    seen: set[str] = set()
    for term_text, term_kind in [
        (preferred_label, "preferred_label"),
        *[(collapse_whitespace(str(item or "")), "alias") for item in raw_aliases],
    ]:
        if not term_text:
            continue
        normalized = normalize_semantic_text(term_text)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        terms.append(
            SemanticRegistryTermDefinition(
                text=term_text,
                normalized_text=normalized,
                term_kind=term_kind,
            )
        )
    if not terms:
        raise ValueError("Semantic concepts require at least one usable term.")
    return tuple(terms)


def _semantic_registry_from_payload(raw_bytes: bytes, payload: dict[str, Any]) -> SemanticRegistry:
    registry_name = collapse_whitespace(str(payload.get("registry_name") or "semantic_registry"))
    registry_version = collapse_whitespace(str(payload.get("registry_version") or ""))
    if not registry_version:
        raise ValueError("Semantic registry requires registry_version.")
    upper_ontology_version = collapse_whitespace(
        str(payload.get("upper_ontology_version") or registry_version)
    )

    raw_categories = payload.get("categories") or []
    if not isinstance(raw_categories, list):
        raise ValueError("Semantic registry categories must be a list.")
    categories: list[SemanticRegistryCategoryDefinition] = []
    seen_category_keys: set[str] = set()
    for raw_category in raw_categories:
        if not isinstance(raw_category, dict):
            raise ValueError("Each semantic category must be a mapping.")
        category_key = collapse_whitespace(str(raw_category.get("category_key") or ""))
        if not category_key:
            raise ValueError("Semantic categories require category_key.")
        if category_key in seen_category_keys:
            raise ValueError(f"Duplicate semantic category key: {category_key}")
        seen_category_keys.add(category_key)
        preferred_label = collapse_whitespace(str(raw_category.get("preferred_label") or ""))
        if not preferred_label:
            raise ValueError("Semantic categories require a non-empty preferred_label.")
        categories.append(
            SemanticRegistryCategoryDefinition(
                category_key=category_key,
                preferred_label=preferred_label,
                scope_note=collapse_whitespace(str(raw_category.get("scope_note") or "")) or None,
                metadata=metadata_without(
                    raw_category, {"category_key", "preferred_label", "scope_note"}
                ),
            )
        )

    raw_entity_types = payload.get("entity_types")
    if raw_entity_types is None:
        raw_entity_types = [
            {
                "entity_type": entity_type,
                "preferred_label": preferred_label,
            }
            for entity_type, preferred_label in _DEFAULT_ENTITY_TYPE_DEFINITIONS
        ]
    if not isinstance(raw_entity_types, list):
        raise ValueError("Semantic registry entity_types must be a list when provided.")
    entity_types: list[SemanticRegistryEntityTypeDefinition] = []
    seen_entity_types: set[str] = set()
    for raw_entity_type in raw_entity_types:
        if not isinstance(raw_entity_type, dict):
            raise ValueError("Each semantic entity type must be a mapping.")
        entity_type = collapse_whitespace(str(raw_entity_type.get("entity_type") or ""))
        if not entity_type:
            raise ValueError("Semantic entity types require entity_type.")
        if entity_type in seen_entity_types:
            raise ValueError(f"Duplicate semantic entity type: {entity_type}")
        seen_entity_types.add(entity_type)
        preferred_label = collapse_whitespace(str(raw_entity_type.get("preferred_label") or ""))
        if not preferred_label:
            raise ValueError("Semantic entity types require a non-empty preferred_label.")
        entity_types.append(
            SemanticRegistryEntityTypeDefinition(
                entity_type=entity_type,
                preferred_label=preferred_label,
                scope_note=collapse_whitespace(str(raw_entity_type.get("scope_note") or ""))
                or None,
                metadata=metadata_without(
                    raw_entity_type, {"entity_type", "preferred_label", "scope_note"}
                ),
            )
        )

    raw_concepts = payload.get("concepts") or []
    if not isinstance(raw_concepts, list):
        raise ValueError("Semantic registry concepts must be a list.")

    concepts: list[SemanticRegistryConceptDefinition] = []
    seen_concept_keys: set[str] = set()
    for raw_concept in raw_concepts:
        if not isinstance(raw_concept, dict):
            raise ValueError("Each semantic concept must be a mapping.")
        concept_key = collapse_whitespace(str(raw_concept.get("concept_key") or ""))
        if not concept_key:
            raise ValueError("Semantic concepts require concept_key.")
        if concept_key in seen_concept_keys:
            raise ValueError(f"Duplicate semantic concept key: {concept_key}")
        seen_concept_keys.add(concept_key)
        preferred_label = collapse_whitespace(str(raw_concept.get("preferred_label") or ""))
        raw_category_keys = raw_concept.get("category_keys") or []
        if raw_category_keys and not isinstance(raw_category_keys, list):
            raise ValueError("Semantic concept category_keys must be a list when provided.")
        category_keys = tuple(
            sorted(
                collapse_whitespace(str(item or ""))
                for item in raw_category_keys
                if collapse_whitespace(str(item or ""))
            )
        )
        for category_key in category_keys:
            if category_key not in seen_category_keys:
                raise ValueError(
                    f"Semantic concept references unknown category_key: {category_key}"
                )
        concepts.append(
            SemanticRegistryConceptDefinition(
                concept_key=concept_key,
                preferred_label=preferred_label,
                scope_note=collapse_whitespace(str(raw_concept.get("scope_note") or "")) or None,
                metadata=metadata_without(
                    raw_concept,
                    {"concept_key", "preferred_label", "scope_note", "aliases", "category_keys"},
                ),
                terms=_concept_terms(raw_concept),
                category_keys=category_keys,
            )
        )

    raw_relations = payload.get("relations") or []
    if raw_relations and not isinstance(raw_relations, list):
        raise ValueError("Semantic registry relations must be a list.")
    relations: list[SemanticRegistryRelationDefinition] = []
    seen_relation_keys: set[str] = set()
    for raw_relation in raw_relations:
        if not isinstance(raw_relation, dict):
            raise ValueError("Each semantic relation must be a mapping.")
        relation_key = collapse_whitespace(str(raw_relation.get("relation_key") or ""))
        if not relation_key:
            raise ValueError("Semantic relations require relation_key.")
        if relation_key in seen_relation_keys:
            raise ValueError(f"Duplicate semantic relation key: {relation_key}")
        seen_relation_keys.add(relation_key)
        preferred_label = collapse_whitespace(str(raw_relation.get("preferred_label") or ""))
        if not preferred_label:
            raise ValueError("Semantic relations require a non-empty preferred_label.")
        raw_domain_entity_types = raw_relation.get("domain_entity_types")
        if raw_domain_entity_types is None:
            raw_domain_entity_types = (
                ["document"] if relation_key == "document_mentions_concept" else ["concept"]
            )
        if not isinstance(raw_domain_entity_types, list):
            raise ValueError("Semantic relation domain_entity_types must be a list.")
        domain_entity_types = tuple(
            sorted(
                collapse_whitespace(str(value or ""))
                for value in raw_domain_entity_types
                if collapse_whitespace(str(value or ""))
            )
        )
        if not domain_entity_types:
            raise ValueError("Semantic relations require at least one domain_entity_type.")
        raw_range_entity_types = raw_relation.get("range_entity_types")
        if raw_range_entity_types is None:
            raw_range_entity_types = ["concept"]
        if not isinstance(raw_range_entity_types, list):
            raise ValueError("Semantic relation range_entity_types must be a list.")
        range_entity_types = tuple(
            sorted(
                collapse_whitespace(str(value or ""))
                for value in raw_range_entity_types
                if collapse_whitespace(str(value or ""))
            )
        )
        if not range_entity_types:
            raise ValueError("Semantic relations require at least one range_entity_type.")
        for entity_type in (*domain_entity_types, *range_entity_types):
            if entity_type not in seen_entity_types:
                raise ValueError(f"Semantic relation references unknown entity_type: {entity_type}")
        symmetric = bool(raw_relation.get("symmetric", False))
        allow_literal_object = bool(raw_relation.get("allow_literal_object", False))
        if allow_literal_object and "literal" not in seen_entity_types:
            raise ValueError(
                "Semantic relations that allow literal objects require the literal entity type."
            )
        cardinality_hint = (
            collapse_whitespace(str(raw_relation.get("cardinality_hint") or "")) or None
        )
        inverse_relation_key = (
            collapse_whitespace(str(raw_relation.get("inverse_relation_key") or "")) or None
        )
        relations.append(
            SemanticRegistryRelationDefinition(
                relation_key=relation_key,
                preferred_label=preferred_label,
                scope_note=collapse_whitespace(str(raw_relation.get("scope_note") or "")) or None,
                domain_entity_types=domain_entity_types,
                range_entity_types=range_entity_types,
                symmetric=symmetric,
                allow_literal_object=allow_literal_object,
                cardinality_hint=cardinality_hint,
                inverse_relation_key=inverse_relation_key,
                metadata=metadata_without(
                    raw_relation,
                    {
                        "relation_key",
                        "preferred_label",
                        "scope_note",
                        "domain_entity_types",
                        "range_entity_types",
                        "symmetric",
                        "allow_literal_object",
                        "cardinality_hint",
                        "inverse_relation_key",
                    },
                ),
            )
        )
    relations_by_key = {relation.relation_key: relation for relation in relations}
    for relation in relations:
        if relation.inverse_relation_key is None:
            continue
        inverse = relations_by_key.get(relation.inverse_relation_key)
        if inverse is None:
            raise ValueError(
                f"Semantic relation {relation.relation_key} references unknown "
                f"inverse_relation_key {relation.inverse_relation_key}."
            )
        if inverse.inverse_relation_key not in {None, relation.relation_key}:
            raise ValueError(
                f"Semantic relation inverse mismatch: {relation.relation_key} -> "
                f"{relation.inverse_relation_key}, but inverse points to "
                f"{inverse.inverse_relation_key}."
            )
        if relation.symmetric and relation.inverse_relation_key != relation.relation_key:
            raise ValueError(
                f"Symmetric semantic relation {relation.relation_key} must point its inverse "
                "to itself when inverse_relation_key is set."
            )

    return SemanticRegistry(
        registry_name=registry_name,
        registry_version=registry_version,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        categories=tuple(categories),
        concepts=tuple(concepts),
        entity_types=tuple(entity_types),
        relations=tuple(relations),
        upper_ontology_version=upper_ontology_version,
    )


def semantic_registry_from_payload(payload: dict[str, Any]) -> SemanticRegistry:
    normalized_payload = validate_semantic_registry_payload(payload)
    raw_bytes = yaml.safe_dump(
        normalized_payload,
        sort_keys=False,
        allow_unicode=True,
    ).encode("utf-8")
    return semantic_registry_from_marshaled_payload(raw_bytes, normalized_payload)


def semantic_registry_from_marshaled_payload(
    raw_bytes: bytes,
    payload: dict[str, Any],
) -> SemanticRegistry:
    return _semantic_registry_from_payload(raw_bytes, validate_semantic_registry_payload(payload))


__all__ = [
    "SemanticRegistry",
    "SemanticRegistryCategoryDefinition",
    "SemanticRegistryConceptDefinition",
    "SemanticRegistryEntityTypeDefinition",
    "SemanticRegistryRelationDefinition",
    "SemanticRegistryTermDefinition",
    "metadata_without",
    "normalize_semantic_text",
    "semantic_registry_from_marshaled_payload",
    "semantic_registry_from_payload",
    "validate_semantic_registry_payload",
]
