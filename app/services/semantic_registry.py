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
    category_keys: tuple[str, ...]


@dataclass(frozen=True)
class SemanticRegistryCategoryDefinition:
    category_key: str
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

    return SemanticRegistry(
        registry_name=registry_name,
        registry_version=registry_version,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        categories=tuple(categories),
        concepts=tuple(concepts),
    )


def semantic_registry_from_payload(payload: dict[str, Any]) -> SemanticRegistry:
    normalized_payload = _validate_registry_payload(payload)
    raw_bytes = yaml.safe_dump(
        normalized_payload,
        sort_keys=False,
        allow_unicode=True,
    ).encode("utf-8")
    return _semantic_registry_from_payload(raw_bytes, normalized_payload)


def load_semantic_registry_payload(registry_path: str | Path | None = None) -> dict[str, Any]:
    current_path = (
        Path(registry_path).expanduser().resolve()
        if registry_path is not None
        else get_settings().semantic_registry_path.expanduser().resolve()
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
        else get_settings().semantic_registry_path.expanduser().resolve()
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


def get_semantic_registry() -> SemanticRegistry:
    settings = get_settings()
    registry_path = settings.semantic_registry_path.expanduser().resolve()
    return _load_semantic_registry_cached(str(registry_path))
