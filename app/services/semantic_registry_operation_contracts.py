from __future__ import annotations

from typing import Any

SEMANTIC_REGISTRY_OPERATION_CONTRACT_VERSION = "semantic-registry-operations-v2"
LIFECYCLE_PLAN_PATH = "docs/ontology_evolution_lifecycle_milestone_plan.md"
SUPPORTED_SEMANTIC_REGISTRY_OPERATION_TYPES = (
    "add_concept",
    "add_alias",
    "add_category_binding",
    "split_concept",
    "merge_concept",
    "deprecate_concept",
    "replace_concept",
    "migrate_concept",
)
LIFECYCLE_SEMANTIC_REGISTRY_OPERATION_TYPES = (
    "split_concept",
    "merge_concept",
    "deprecate_concept",
    "replace_concept",
    "migrate_concept",
)


def _normalized_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _successor_concept_keys(operation: dict[str, Any]) -> list[str]:
    successors = operation.get("successor_concepts")
    if not isinstance(successors, list):
        return []
    concept_keys: list[str] = []
    for successor in successors:
        if not isinstance(successor, dict):
            continue
        concept_key = str(successor.get("concept_key") or "").strip()
        if concept_key:
            concept_keys.append(concept_key)
    return concept_keys


def _validate_lifecycle_operation_shape(
    operation: dict[str, Any],
    *,
    operation_type: str,
) -> None:
    source_concept_keys = _normalized_string_list(operation.get("source_concept_keys"))
    successor_concept_keys = _successor_concept_keys(operation)
    if operation_type == "split_concept":
        if len(successor_concept_keys) < 2:
            raise ValueError(
                "split_concept operations require at least two structured successor_concepts. "
                f"Keep lifecycle lineage machine-readable in {LIFECYCLE_PLAN_PATH}."
            )
    elif operation_type == "merge_concept":
        if len(set(source_concept_keys)) < 2:
            raise ValueError(
                "merge_concept operations require at least two source_concept_keys. "
                f"Keep lifecycle lineage machine-readable in {LIFECYCLE_PLAN_PATH}."
            )
    elif operation_type == "deprecate_concept":
        if not successor_concept_keys:
            raise ValueError(
                "deprecate_concept operations require successor_concepts so replacement "
                f"lineage stays explicit in {LIFECYCLE_PLAN_PATH}."
            )
    elif operation_type == "replace_concept":
        if len(successor_concept_keys) != 1:
            raise ValueError(
                "replace_concept operations require exactly one successor_concept. "
                f"Keep lifecycle lineage machine-readable in {LIFECYCLE_PLAN_PATH}."
            )
    elif operation_type == "migrate_concept" and not successor_concept_keys:
        raise ValueError(
            "migrate_concept operations require successor_concepts so migration intent "
            f"stays explicit in {LIFECYCLE_PLAN_PATH}."
        )


def validate_semantic_registry_operations(operations: list[dict[str, Any]]) -> None:
    unsupported_types = sorted(
        {
            str(operation.get("operation_type") or "").strip() or "<missing>"
            for operation in operations
            if (str(operation.get("operation_type") or "").strip() or "<missing>")
            not in SUPPORTED_SEMANTIC_REGISTRY_OPERATION_TYPES
        }
    )
    if unsupported_types:
        raise ValueError(
            "Unsupported semantic registry operation(s): "
            f"{', '.join(unsupported_types)}. Supported operation types are "
            f"{', '.join(SUPPORTED_SEMANTIC_REGISTRY_OPERATION_TYPES)}."
        )
    for operation in operations:
        operation_type = str(operation.get("operation_type") or "").strip()
        if operation_type in LIFECYCLE_SEMANTIC_REGISTRY_OPERATION_TYPES:
            _validate_lifecycle_operation_shape(operation, operation_type=operation_type)


__all__ = [
    "LIFECYCLE_SEMANTIC_REGISTRY_OPERATION_TYPES",
    "SEMANTIC_REGISTRY_OPERATION_CONTRACT_VERSION",
    "SUPPORTED_SEMANTIC_REGISTRY_OPERATION_TYPES",
    "validate_semantic_registry_operations",
]
