from __future__ import annotations

from typing import Any

from app.services.semantic_registry_operation_contracts import (
    SEMANTIC_REGISTRY_OPERATION_CONTRACT_VERSION,
    validate_semantic_registry_operations,
)


def _preferred_label_from_concept_key(concept_key: str) -> str:
    return " ".join(part.capitalize() for part in concept_key.replace("-", "_").split("_") if part)


def _normalized_unique_strings(values: list[str] | None) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values or []:
        candidate = str(value).strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def _known_category_keys(payload: dict[str, Any]) -> set[str]:
    return {
        str(category.get("category_key") or "").strip()
        for category in (payload.get("categories") or [])
        if str(category.get("category_key") or "").strip()
    }


def _ensure_category_keys_exist(category_keys: list[str], known_category_keys: set[str]) -> None:
    missing = [
        category_key
        for category_key in category_keys
        if category_key not in known_category_keys
    ]
    if missing:
        raise ValueError(
            "Semantic registry operation references unknown category_key(s): "
            f"{', '.join(sorted(missing))}."
        )


def _merge_unique_strings(
    existing_values: list[str] | None,
    new_values: list[str] | None,
) -> list[str]:
    return _normalized_unique_strings([*(existing_values or []), *(new_values or [])])


def _concept_aliases(concept: dict[str, Any]) -> list[str]:
    return _normalized_unique_strings([str(alias) for alias in (concept.get("aliases") or [])])


def _concept_category_keys(concept: dict[str, Any]) -> list[str]:
    return sorted(
        _normalized_unique_strings(
            [str(category_key) for category_key in (concept.get("category_keys") or [])]
        )
    )


def _ensure_concept(
    updated_payload: dict[str, Any],
    concepts_by_key: dict[str, dict[str, Any]],
    known_category_keys: set[str],
    *,
    concept_key: str,
    preferred_label: str | None = None,
    aliases: list[str] | None = None,
    category_keys: list[str] | None = None,
    scope_note: str | None = None,
) -> dict[str, Any]:
    normalized_aliases = _normalized_unique_strings(aliases)
    normalized_category_keys = sorted(_normalized_unique_strings(category_keys))
    _ensure_category_keys_exist(normalized_category_keys, known_category_keys)
    concept = concepts_by_key.get(concept_key)
    if concept is None:
        concept = {
            "concept_key": concept_key,
            "preferred_label": preferred_label or _preferred_label_from_concept_key(concept_key),
        }
        if normalized_aliases:
            concept["aliases"] = normalized_aliases
        if normalized_category_keys:
            concept["category_keys"] = normalized_category_keys
        if scope_note:
            concept["scope_note"] = scope_note
        updated_payload["concepts"].append(concept)
        concepts_by_key[concept_key] = concept
        return concept
    if preferred_label and not str(concept.get("preferred_label") or "").strip():
        concept["preferred_label"] = preferred_label
    if normalized_aliases:
        concept["aliases"] = _merge_unique_strings(_concept_aliases(concept), normalized_aliases)
    if normalized_category_keys:
        concept["category_keys"] = sorted(
            _merge_unique_strings(_concept_category_keys(concept), normalized_category_keys)
        )
    if scope_note and not str(concept.get("scope_note") or "").strip():
        concept["scope_note"] = scope_note
    return concept


def _require_concept(
    concepts_by_key: dict[str, dict[str, Any]],
    *,
    concept_key: str,
) -> dict[str, Any]:
    concept = concepts_by_key.get(concept_key)
    if concept is None:
        raise ValueError(f"Unknown semantic concept key in draft: {concept_key}")
    return concept


def _record_lifecycle(
    concept: dict[str, Any],
    *,
    status: str | None,
    predecessor_concept_keys: list[str] | None = None,
    successor_concept_keys: list[str] | None = None,
    operation_id: str,
    operation_type: str,
) -> None:
    if status is not None:
        concept["lifecycle_status"] = status
    if predecessor_concept_keys:
        concept["predecessor_concept_keys"] = sorted(
            _merge_unique_strings(
                [str(value) for value in (concept.get("predecessor_concept_keys") or [])],
                predecessor_concept_keys,
            )
        )
    if successor_concept_keys:
        concept["successor_concept_keys"] = sorted(
            _merge_unique_strings(
                [str(value) for value in (concept.get("successor_concept_keys") or [])],
                successor_concept_keys,
            )
        )
    concept["lifecycle_operation_ids"] = _merge_unique_strings(
        [str(value) for value in (concept.get("lifecycle_operation_ids") or [])],
        [operation_id],
    )
    concept["lifecycle_operation_types"] = _merge_unique_strings(
        [str(value) for value in (concept.get("lifecycle_operation_types") or [])],
        [operation_type],
    )


def _merge_source_terms_into_target(source: dict[str, Any], target: dict[str, Any]) -> None:
    source_aliases = _merge_unique_strings(
        [str(source.get("preferred_label") or "").strip()],
        [str(alias) for alias in (source.get("aliases") or [])],
    )
    source_aliases = [
        alias
        for alias in source_aliases
        if alias and alias != target.get("preferred_label")
    ]
    if source_aliases:
        target["aliases"] = _merge_unique_strings(_concept_aliases(target), source_aliases)
    source_category_keys = _concept_category_keys(source)
    if source_category_keys:
        target["category_keys"] = sorted(
            _merge_unique_strings(_concept_category_keys(target), source_category_keys)
        )


def _successor_concepts_for_operation(
    updated_payload: dict[str, Any],
    concepts_by_key: dict[str, dict[str, Any]],
    known_category_keys: set[str],
    *,
    operation: dict[str, Any],
) -> list[dict[str, Any]]:
    successors: list[dict[str, Any]] = []
    for successor_payload in operation.get("successor_concepts") or []:
        if not isinstance(successor_payload, dict):
            continue
        successor = _ensure_concept(
            updated_payload,
            concepts_by_key,
            known_category_keys,
            concept_key=str(successor_payload.get("concept_key") or "").strip(),
            preferred_label=str(successor_payload.get("preferred_label") or "").strip() or None,
            aliases=[str(alias) for alias in (successor_payload.get("aliases") or [])],
            category_keys=[
                str(category_key) for category_key in (successor_payload.get("category_keys") or [])
            ],
            scope_note=str(successor_payload.get("scope_note") or "").strip() or None,
        )
        successors.append(successor)
    return successors


def apply_semantic_registry_operations(
    base_registry_payload: dict[str, Any],
    operations: list[dict[str, Any]],
    *,
    proposed_registry_version: str,
) -> dict[str, Any]:
    validate_semantic_registry_operations(operations)
    updated_payload = {
        **base_registry_payload,
        "registry_version": proposed_registry_version,
        "operation_contract_version": SEMANTIC_REGISTRY_OPERATION_CONTRACT_VERSION,
        "categories": [dict(item) for item in (base_registry_payload.get("categories") or [])],
        "concepts": [dict(item) for item in (base_registry_payload.get("concepts") or [])],
    }
    known_category_keys = _known_category_keys(updated_payload)
    concepts_by_key = {
        str(concept.get("concept_key") or ""): concept
        for concept in updated_payload["concepts"]
        if str(concept.get("concept_key") or "")
    }
    for operation in operations:
        operation_type = operation["operation_type"]
        concept_key = operation["concept_key"]
        operation_id = operation["operation_id"]
        if operation_type == "add_concept":
            concept = concepts_by_key.get(concept_key)
            if concept is not None:
                raise ValueError(f"Semantic concept key already exists in draft: {concept_key}")
            _ensure_concept(
                updated_payload,
                concepts_by_key,
                known_category_keys,
                concept_key=concept_key,
                preferred_label=str(operation.get("preferred_label") or "").strip() or None,
            )
            continue
        if operation_type == "add_alias":
            concept = _require_concept(concepts_by_key, concept_key=concept_key)
            alias_text = str(operation.get("alias_text") or "").strip()
            if alias_text:
                concept["aliases"] = _merge_unique_strings(_concept_aliases(concept), [alias_text])
            continue
        if operation_type == "add_category_binding":
            concept = _require_concept(concepts_by_key, concept_key=concept_key)
            category_key = str(operation.get("category_key") or "").strip()
            _ensure_category_keys_exist([category_key], known_category_keys)
            concept["category_keys"] = sorted(
                _merge_unique_strings(_concept_category_keys(concept), [category_key])
            )
            continue

        successors = _successor_concepts_for_operation(
            updated_payload,
            concepts_by_key,
            known_category_keys,
            operation=operation,
        )
        successor_keys = [successor["concept_key"] for successor in successors]
        if operation_type == "split_concept":
            source = _require_concept(concepts_by_key, concept_key=concept_key)
            _record_lifecycle(
                source,
                status="split",
                successor_concept_keys=successor_keys,
                operation_id=operation_id,
                operation_type=operation_type,
            )
            for successor in successors:
                _record_lifecycle(
                    successor,
                    status="active",
                    predecessor_concept_keys=[concept_key],
                    operation_id=operation_id,
                    operation_type=operation_type,
                )
            continue
        if operation_type == "merge_concept":
            target = _ensure_concept(
                updated_payload,
                concepts_by_key,
                known_category_keys,
                concept_key=concept_key,
                preferred_label=str(operation.get("preferred_label") or "").strip() or None,
            )
            source_concept_keys = _normalized_unique_strings(
                [str(source_key) for source_key in (operation.get("source_concept_keys") or [])]
            )
            for source_key in source_concept_keys:
                source = _require_concept(concepts_by_key, concept_key=source_key)
                _record_lifecycle(
                    source,
                    status="merged",
                    successor_concept_keys=[concept_key],
                    operation_id=operation_id,
                    operation_type=operation_type,
                )
                _merge_source_terms_into_target(source, target)
            _record_lifecycle(
                target,
                status="active",
                predecessor_concept_keys=source_concept_keys,
                operation_id=operation_id,
                operation_type=operation_type,
            )
            continue

        source = _require_concept(concepts_by_key, concept_key=concept_key)
        if operation_type == "deprecate_concept":
            status = "deprecated"
        elif operation_type == "replace_concept":
            status = "replaced"
        elif operation_type == "migrate_concept":
            status = "migrated"
        else:
            raise ValueError(f"Unsupported semantic registry operation: {operation_type}")
        _record_lifecycle(
            source,
            status=status,
            successor_concept_keys=successor_keys,
            operation_id=operation_id,
            operation_type=operation_type,
        )
        if len(successors) == 1:
            _merge_source_terms_into_target(source, successors[0])
        for successor in successors:
            _record_lifecycle(
                successor,
                status="active",
                predecessor_concept_keys=[concept_key],
                operation_id=operation_id,
                operation_type=operation_type,
            )
    return updated_payload


__all__ = ["apply_semantic_registry_operations"]
