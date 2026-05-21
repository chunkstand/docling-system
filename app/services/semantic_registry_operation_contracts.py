from __future__ import annotations

from typing import Any

SUPPORTED_SEMANTIC_REGISTRY_OPERATION_TYPES = (
    "add_concept",
    "add_alias",
    "add_category_binding",
)
_BLOCKED_ONTOLOGY_LIFECYCLE_OPERATION_TYPES = (
    "split_concept",
    "merge_concept",
    "deprecate_concept",
    "replace_concept",
    "migrate_concept",
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
    if not unsupported_types:
        return
    blocked_lifecycle_types = [
        operation_type
        for operation_type in unsupported_types
        if operation_type in _BLOCKED_ONTOLOGY_LIFECYCLE_OPERATION_TYPES
    ]
    if blocked_lifecycle_types:
        blocked_text = ", ".join(blocked_lifecycle_types)
        raise ValueError(
            "Non-additive ontology lifecycle operations are not supported in the "
            f"current additive-only ontology workflow: {blocked_text}. Route this "
            "work through docs/ontology_evolution_lifecycle_milestone_plan.md "
            "instead of publishing it as an additive ontology draft."
        )
    raise ValueError(
        "Unsupported semantic registry operation(s): "
        f"{', '.join(unsupported_types)}. Supported operation types are "
        f"{', '.join(SUPPORTED_SEMANTIC_REGISTRY_OPERATION_TYPES)}."
    )


__all__ = [
    "SUPPORTED_SEMANTIC_REGISTRY_OPERATION_TYPES",
    "validate_semantic_registry_operations",
]
