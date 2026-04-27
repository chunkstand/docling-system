from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.text import collapse_whitespace
from app.core.time import utcnow
from app.db.models import (
    SemanticOntologySnapshot,
    SemanticOntologySourceKind,
    WorkspaceSemanticState,
)
from app.services.semantic_governance import record_ontology_snapshot_governance_events

NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")
WORKSPACE_SEMANTIC_STATE_KEY = "default"
DEFAULT_ENTITY_TYPE_DEFINITIONS = (
    ("document", "Document"),
    ("concept", "Concept"),
    ("literal", "Literal"),
)


def normalize_semantic_text(value: str | None) -> str:
    collapsed = collapse_whitespace((value or "").lower())
    return collapse_whitespace(NORMALIZE_PATTERN.sub(" ", collapsed))


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


def _validate_registry_payload(payload: Any) -> dict[str, Any]:
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
                metadata={
                    key: value
                    for key, value in raw_category.items()
                    if key not in {"category_key", "preferred_label", "scope_note"}
                },
            )
        )

    raw_entity_types = payload.get("entity_types")
    if raw_entity_types is None:
        raw_entity_types = [
            {
                "entity_type": entity_type,
                "preferred_label": preferred_label,
            }
            for entity_type, preferred_label in DEFAULT_ENTITY_TYPE_DEFINITIONS
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
                metadata={
                    key: value
                    for key, value in raw_entity_type.items()
                    if key not in {"entity_type", "preferred_label", "scope_note"}
                },
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
                metadata={
                    key: value
                    for key, value in raw_concept.items()
                    if key
                    not in {
                        "concept_key",
                        "preferred_label",
                        "scope_note",
                        "aliases",
                        "category_keys",
                    }
                },
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
                metadata={
                    key: value
                    for key, value in raw_relation.items()
                    if key
                    not in {
                        "relation_key",
                        "preferred_label",
                        "scope_note",
                        "domain_entity_types",
                        "range_entity_types",
                        "symmetric",
                        "allow_literal_object",
                        "cardinality_hint",
                        "inverse_relation_key",
                    }
                },
            )
        )
    relations_by_key = {relation.relation_key: relation for relation in relations}
    for relation in relations:
        if relation.inverse_relation_key is None:
            continue
        inverse = relations_by_key.get(relation.inverse_relation_key)
        if inverse is None:
            raise ValueError(
                f"Semantic relation {relation.relation_key} references "
                "unknown inverse_relation_key "
                f"{relation.inverse_relation_key}."
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
    normalized_payload = _validate_registry_payload(payload)
    raw_bytes = yaml.safe_dump(
        normalized_payload,
        sort_keys=False,
        allow_unicode=True,
    ).encode("utf-8")
    return _semantic_registry_from_payload(raw_bytes, normalized_payload)


def _resolve_seed_registry_path() -> Path:
    settings = get_settings()
    if settings.semantic_registry_path is not None:
        return settings.semantic_registry_path.expanduser().resolve()
    return settings.upper_ontology_path.expanduser().resolve()


def load_semantic_registry_payload(registry_path: str | Path | None = None) -> dict[str, Any]:
    current_path = (
        Path(registry_path).expanduser().resolve()
        if registry_path is not None
        else _resolve_seed_registry_path()
    )
    if not current_path.is_file():
        raise ValueError(f"Semantic registry path does not exist: {current_path}")
    return _validate_registry_payload(yaml.safe_load(current_path.read_bytes()) or {})


def clear_semantic_registry_cache() -> None:
    _load_semantic_registry_cached.cache_clear()


def write_semantic_registry_payload(
    payload: dict[str, Any],
    registry_path: str | Path | None = None,
) -> Path:
    # Validate the full semantic registry contract before mutating the live file.
    semantic_registry_from_payload(payload)
    current_path = (
        Path(registry_path).expanduser().resolve()
        if registry_path is not None
        else _resolve_seed_registry_path()
    )
    current_path.parent.mkdir(parents=True, exist_ok=True)
    current_path.write_text(
        yaml.safe_dump(
            _validate_registry_payload(payload),
            sort_keys=False,
            allow_unicode=True,
        )
    )
    clear_semantic_registry_cache()
    return current_path


def _load_semantic_registry(registry_path: str) -> SemanticRegistry:
    path = Path(registry_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Semantic registry path does not exist: {path}")

    raw_bytes = path.read_bytes()
    payload = _validate_registry_payload(yaml.safe_load(raw_bytes) or {})
    return _semantic_registry_from_payload(raw_bytes, payload)


@lru_cache(maxsize=4)
def _load_semantic_registry_cached(registry_path: str) -> SemanticRegistry:
    return _load_semantic_registry(registry_path)


def _snapshot_payload_sha256(payload: dict[str, Any]) -> str:
    normalized_payload = _validate_registry_payload(payload)
    return hashlib.sha256(
        json.dumps(
            normalized_payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _workspace_state(session: Session) -> WorkspaceSemanticState | None:
    return session.get(WorkspaceSemanticState, WORKSPACE_SEMANTIC_STATE_KEY)


def _snapshot_to_registry(snapshot: SemanticOntologySnapshot) -> SemanticRegistry:
    registry = semantic_registry_from_payload(snapshot.payload_json or {})
    return SemanticRegistry(
        registry_name=registry.registry_name,
        registry_version=registry.registry_version,
        sha256=snapshot.sha256,
        categories=registry.categories,
        concepts=registry.concepts,
        entity_types=registry.entity_types,
        relations=registry.relations,
        snapshot_id=snapshot.id,
        upper_ontology_version=snapshot.upper_ontology_version,
    )


def semantic_entity_types_by_name(
    registry: SemanticRegistry,
) -> dict[str, SemanticRegistryEntityTypeDefinition]:
    return {entity_type.entity_type: entity_type for entity_type in registry.entity_types}


def semantic_relations_by_key(
    registry: SemanticRegistry,
) -> dict[str, SemanticRegistryRelationDefinition]:
    return {relation.relation_key: relation for relation in registry.relations}


def get_semantic_relation_definition(
    registry: SemanticRegistry,
    relation_key: str,
) -> SemanticRegistryRelationDefinition | None:
    normalized_key = collapse_whitespace(relation_key)
    if not normalized_key:
        return None
    return semantic_relations_by_key(registry).get(normalized_key)


def infer_semantic_entity_type(
    registry: SemanticRegistry,
    entity_key: str | None,
    *,
    object_value_text: str | None = None,
) -> str | None:
    known_entity_types = set(semantic_entity_types_by_name(registry))
    normalized_key = collapse_whitespace(entity_key or "")
    if normalized_key and ":" in normalized_key:
        entity_type = normalized_key.split(":", 1)[0]
        if entity_type in known_entity_types:
            return entity_type
    if object_value_text is not None and "literal" in known_entity_types:
        return "literal"
    return None


def canonicalize_semantic_relation_endpoints(
    registry: SemanticRegistry,
    *,
    relation_key: str,
    subject_entity_key: str,
    subject_label: str,
    object_entity_key: str | None,
    object_label: str | None,
) -> tuple[str, str, str | None, str | None]:
    relation = get_semantic_relation_definition(registry, relation_key)
    if relation is None or not relation.symmetric or object_entity_key is None:
        return subject_entity_key, subject_label, object_entity_key, object_label
    if subject_entity_key <= object_entity_key:
        return subject_entity_key, subject_label, object_entity_key, object_label
    return object_entity_key, object_label or object_entity_key, subject_entity_key, subject_label


def validate_semantic_relation_instance(
    registry: SemanticRegistry,
    *,
    relation_key: str,
    subject_entity_key: str,
    object_entity_key: str | None,
    object_value_text: str | None = None,
) -> list[str]:
    reasons: list[str] = []
    relation = get_semantic_relation_definition(registry, relation_key)
    if relation is None:
        return [f"Unknown semantic relation: {relation_key}"]

    subject_entity_type = infer_semantic_entity_type(registry, subject_entity_key)
    if subject_entity_type is None:
        reasons.append(f"Unable to infer subject entity type for {subject_entity_key}.")
    elif subject_entity_type not in relation.domain_entity_types:
        reasons.append(
            f"Relation {relation_key} does not allow subject entity type {subject_entity_type}."
        )

    object_entity_type = infer_semantic_entity_type(
        registry,
        object_entity_key,
        object_value_text=object_value_text,
    )
    if object_value_text is not None:
        if not relation.allow_literal_object:
            reasons.append(f"Relation {relation_key} does not allow literal object values.")
        elif object_entity_type != "literal":
            reasons.append(
                f"Relation {relation_key} expected a literal object type, "
                f"received {object_entity_type!r}."
            )
    else:
        if object_entity_key is None:
            reasons.append(f"Relation {relation_key} requires an object entity key.")
        elif object_entity_type is None:
            reasons.append(f"Unable to infer object entity type for {object_entity_key}.")
        elif object_entity_type not in relation.range_entity_types:
            reasons.append(
                f"Relation {relation_key} does not allow object entity type {object_entity_type}."
            )

    return reasons


def persist_semantic_ontology_snapshot(
    session: Session,
    payload: dict[str, Any],
    *,
    source_kind: str,
    source_task_id: UUID | None = None,
    source_task_type: str | None = None,
    parent_snapshot_id: UUID | None = None,
    activate: bool = False,
) -> SemanticOntologySnapshot:
    registry = semantic_registry_from_payload(payload)
    normalized_payload = _validate_registry_payload(payload)
    incoming_sha256 = _snapshot_payload_sha256(normalized_payload)
    now = utcnow()
    requested_parent_snapshot_id = parent_snapshot_id
    snapshot = session.execute(
        select(SemanticOntologySnapshot).where(
            SemanticOntologySnapshot.ontology_version == registry.registry_version
        )
    ).scalar_one_or_none()
    if snapshot is None:
        snapshot = SemanticOntologySnapshot(
            ontology_name=registry.registry_name,
            ontology_version=registry.registry_version,
            upper_ontology_version=registry.upper_ontology_version or registry.registry_version,
            source_kind=source_kind,
            source_task_id=source_task_id,
            source_task_type=source_task_type,
            parent_snapshot_id=requested_parent_snapshot_id,
            payload_json=normalized_payload,
            sha256=incoming_sha256,
            created_at=now,
            activated_at=now if activate else None,
        )
        session.add(snapshot)
        session.flush()
    else:
        if (
            snapshot.source_kind == SemanticOntologySourceKind.UPPER_SEED.value
            and source_kind == SemanticOntologySourceKind.UPPER_SEED.value
        ):
            resolved_parent_snapshot_id = requested_parent_snapshot_id
            if resolved_parent_snapshot_id == snapshot.id:
                resolved_parent_snapshot_id = snapshot.parent_snapshot_id
            snapshot.ontology_name = registry.registry_name
            snapshot.upper_ontology_version = (
                registry.upper_ontology_version or registry.registry_version
            )
            snapshot.source_kind = source_kind
            snapshot.source_task_id = source_task_id
            snapshot.source_task_type = source_task_type
            snapshot.parent_snapshot_id = resolved_parent_snapshot_id
            snapshot.payload_json = normalized_payload
            snapshot.sha256 = incoming_sha256
        elif snapshot.sha256 != incoming_sha256:
            raise ValueError(
                "Semantic ontology snapshot versions are immutable once published; "
                "choose a new ontology_version for changed payloads."
            )
        if activate:
            snapshot.activated_at = now
    if activate:
        state = _workspace_state(session)
        if state is None:
            state = WorkspaceSemanticState(
                workspace_key=WORKSPACE_SEMANTIC_STATE_KEY,
                active_ontology_snapshot_id=snapshot.id,
                created_at=now,
                updated_at=now,
            )
            session.add(state)
        else:
            state.active_ontology_snapshot_id = snapshot.id
            state.updated_at = now
        snapshot.activated_at = now
        clear_semantic_registry_cache()
    record_ontology_snapshot_governance_events(
        session,
        snapshot,
        activated=activate,
    )
    session.flush()
    return snapshot


def ensure_workspace_semantic_registry(session: Session) -> SemanticRegistry:
    state = _workspace_state(session)
    if state is not None and state.active_ontology_snapshot_id is not None:
        snapshot = session.get(SemanticOntologySnapshot, state.active_ontology_snapshot_id)
        if snapshot is not None:
            if snapshot.source_kind != SemanticOntologySourceKind.UPPER_SEED.value:
                return _snapshot_to_registry(snapshot)

            seed_payload = load_semantic_registry_payload()
            seed_sha256 = _snapshot_payload_sha256(seed_payload)
            if snapshot.sha256 == seed_sha256:
                return _snapshot_to_registry(snapshot)

            synced_snapshot = persist_semantic_ontology_snapshot(
                session,
                seed_payload,
                source_kind=SemanticOntologySourceKind.UPPER_SEED.value,
                parent_snapshot_id=snapshot.id,
                activate=True,
            )
            session.commit()
            return _snapshot_to_registry(synced_snapshot)

    seed_payload = load_semantic_registry_payload()
    snapshot = persist_semantic_ontology_snapshot(
        session,
        seed_payload,
        source_kind=SemanticOntologySourceKind.UPPER_SEED.value,
        activate=True,
    )
    session.commit()
    return _snapshot_to_registry(snapshot)


def get_active_semantic_ontology_snapshot(session: Session) -> SemanticOntologySnapshot:
    state = _workspace_state(session)
    if state is None or state.active_ontology_snapshot_id is None:
        ensure_workspace_semantic_registry(session)
        state = _workspace_state(session)
    if state is None or state.active_ontology_snapshot_id is None:
        raise ValueError("Workspace semantic state is missing an active ontology snapshot.")
    snapshot = session.get(SemanticOntologySnapshot, state.active_ontology_snapshot_id)
    if snapshot is None:
        raise ValueError("Active ontology snapshot disappeared.")
    return snapshot


def get_semantic_registry(session: Session | None = None) -> SemanticRegistry:
    if session is not None:
        return ensure_workspace_semantic_registry(session)
    registry_path = _resolve_seed_registry_path()
    return _load_semantic_registry_cached(str(registry_path))
