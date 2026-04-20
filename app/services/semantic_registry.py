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

NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")
WORKSPACE_SEMANTIC_STATE_KEY = "default"


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
class SemanticRegistryRelationDefinition:
    relation_key: str
    preferred_label: str
    scope_note: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SemanticRegistry:
    registry_name: str
    registry_version: str
    sha256: str
    categories: tuple[SemanticRegistryCategoryDefinition, ...]
    concepts: tuple[SemanticRegistryConceptDefinition, ...]
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
    for term_text, term_kind in [(preferred_label, "preferred_label"), *[
        (collapse_whitespace(str(item or "")), "alias") for item in raw_aliases
    ]]:
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
        relations.append(
            SemanticRegistryRelationDefinition(
                relation_key=relation_key,
                preferred_label=preferred_label,
                scope_note=collapse_whitespace(str(raw_relation.get("scope_note") or "")) or None,
                metadata={
                    key: value
                    for key, value in raw_relation.items()
                    if key not in {"relation_key", "preferred_label", "scope_note"}
                },
            )
        )

    return SemanticRegistry(
        registry_name=registry_name,
        registry_version=registry_version,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        categories=tuple(categories),
        concepts=tuple(concepts),
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
        relations=registry.relations,
        snapshot_id=snapshot.id,
        upper_ontology_version=snapshot.upper_ontology_version,
    )


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
