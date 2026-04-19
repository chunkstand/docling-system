from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.core.config import get_settings
from app.core.text import collapse_whitespace

NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")


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


@dataclass(frozen=True)
class SemanticRegistry:
    registry_name: str
    registry_version: str
    sha256: str
    concepts: tuple[SemanticRegistryConceptDefinition, ...]


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


def _load_semantic_registry(registry_path: str) -> SemanticRegistry:
    path = Path(registry_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Semantic registry path does not exist: {path}")

    raw_bytes = path.read_bytes()
    payload = _validate_registry_payload(yaml.safe_load(raw_bytes) or {})
    registry_name = collapse_whitespace(str(payload.get("registry_name") or "semantic_registry"))
    registry_version = collapse_whitespace(str(payload.get("registry_version") or ""))
    if not registry_version:
        raise ValueError("Semantic registry requires registry_version.")

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
        concepts.append(
            SemanticRegistryConceptDefinition(
                concept_key=concept_key,
                preferred_label=preferred_label,
                scope_note=collapse_whitespace(str(raw_concept.get("scope_note") or "")) or None,
                metadata={
                    key: value
                    for key, value in raw_concept.items()
                    if key not in {"concept_key", "preferred_label", "scope_note", "aliases"}
                },
                terms=_concept_terms(raw_concept),
            )
        )

    return SemanticRegistry(
        registry_name=registry_name,
        registry_version=registry_version,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        concepts=tuple(concepts),
    )


@lru_cache(maxsize=4)
def _load_semantic_registry_cached(registry_path: str) -> SemanticRegistry:
    return _load_semantic_registry(registry_path)


def get_semantic_registry() -> SemanticRegistry:
    settings = get_settings()
    registry_path = settings.semantic_registry_path.expanduser().resolve()
    return _load_semantic_registry_cached(str(registry_path))
