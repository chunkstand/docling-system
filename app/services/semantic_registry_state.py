from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.text import collapse_whitespace
from app.core.time import utcnow
from app.db.public.semantic_memory import (
    SemanticOntologySnapshot,
    SemanticOntologySourceKind,
    WorkspaceSemanticState,
)
from app.services.semantic_governance import record_ontology_snapshot_governance_events
from app.services.semantic_registry_contracts import (
    SemanticRegistry,
    SemanticRegistryEntityTypeDefinition,
    SemanticRegistryRelationDefinition,
    semantic_registry_from_payload,
    validate_semantic_registry_payload,
)
from app.services.semantic_registry_storage import (
    clear_semantic_registry_cache,
    load_semantic_registry_payload,
)

WORKSPACE_SEMANTIC_STATE_KEY = "default"


def _snapshot_payload_sha256(payload: dict[str, Any]) -> str:
    normalized_payload = validate_semantic_registry_payload(payload)
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
    normalized_payload = validate_semantic_registry_payload(payload)
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


def get_semantic_registry(session: Session | None = None) -> SemanticRegistry:
    if session is not None:
        return ensure_workspace_semantic_registry(session)
    from app.services.semantic_registry_storage import (
        load_semantic_registry as _load_semantic_registry,
    )

    return _load_semantic_registry()


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


__all__ = [
    "WORKSPACE_SEMANTIC_STATE_KEY",
    "canonicalize_semantic_relation_endpoints",
    "ensure_workspace_semantic_registry",
    "get_semantic_registry",
    "get_semantic_relation_definition",
    "get_active_semantic_ontology_snapshot",
    "infer_semantic_entity_type",
    "persist_semantic_ontology_snapshot",
    "semantic_entity_types_by_name",
    "semantic_relations_by_key",
    "validate_semantic_relation_instance",
]
