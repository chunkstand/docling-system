from __future__ import annotations

from typing import Any

from app.services.semantic_registry_operation_contracts import (
    LIFECYCLE_SEMANTIC_REGISTRY_OPERATION_TYPES,
)


def _normalized_keys(values: list[str] | None) -> list[str]:
    candidates = (str(value).strip() for value in (values or []))
    return [candidate for candidate in dict.fromkeys(candidates) if candidate]


def has_lifecycle_registry_operations(operations: list[dict[str, Any]]) -> bool:
    return any(
        str(operation.get("operation_type") or "") in LIFECYCLE_SEMANTIC_REGISTRY_OPERATION_TYPES
        for operation in operations
    )


def _source_concept_keys(operation: dict[str, Any]) -> list[str]:
    operation_type = str(operation.get("operation_type") or "")
    if operation_type == "merge_concept":
        return _normalized_keys(
            [str(concept_key) for concept_key in (operation.get("source_concept_keys") or [])]
        )
    concept_key = str(operation.get("concept_key") or "").strip()
    return [concept_key] if concept_key else []


def _lifecycle_successor_concept_keys(operation: dict[str, Any]) -> list[str]:
    operation_type = str(operation.get("operation_type") or "")
    if operation_type == "merge_concept":
        concept_key = str(operation.get("concept_key") or "").strip()
        return [concept_key] if concept_key else []
    return _normalized_keys(
        [
            str(successor.get("concept_key") or "")
            for successor in (operation.get("successor_concepts") or [])
            if isinstance(successor, dict)
        ]
    )


def build_lifecycle_verification_preview(
    *,
    operations: list[dict[str, Any]],
    document_deltas: list[dict[str, Any]],
) -> dict[str, Any] | None:
    lifecycle_operations = [
        operation
        for operation in operations
        if str(operation.get("operation_type") or "") in LIFECYCLE_SEMANTIC_REGISTRY_OPERATION_TYPES
    ]
    if not lifecycle_operations:
        return None

    operation_previews: list[dict[str, Any]] = []
    missing_operation_ids: list[str] = []
    for operation in lifecycle_operations:
        source_concept_keys = _source_concept_keys(operation)
        successor_concept_keys = _lifecycle_successor_concept_keys(operation)
        tracked_concept_keys = set(source_concept_keys) | set(successor_concept_keys)
        preview_signals: list[dict[str, Any]] = []
        for delta in document_deltas:
            added_successor_concept_keys = sorted(
                set(delta.get("added_concept_keys") or []) & set(successor_concept_keys)
            )
            removed_source_concept_keys = sorted(
                set(delta.get("removed_concept_keys") or []) & set(source_concept_keys)
            )
            introduced_expected_concepts = sorted(
                set(delta.get("introduced_expected_concepts") or []) & tracked_concept_keys
            )
            regressed_expected_concepts = sorted(
                set(delta.get("regressed_expected_concepts") or []) & tracked_concept_keys
            )
            if not (
                added_successor_concept_keys
                or removed_source_concept_keys
                or introduced_expected_concepts
                or regressed_expected_concepts
            ):
                continue
            preview_signals.append(
                {
                    "document_id": str(delta["document_id"]),
                    "run_id": str(delta["run_id"]),
                    "evaluation_fixture_name": delta.get("evaluation_fixture_name"),
                    "candidate_evaluation_status": delta.get("candidate_evaluation_status"),
                    "added_successor_concept_keys": added_successor_concept_keys,
                    "removed_source_concept_keys": removed_source_concept_keys,
                    "introduced_expected_concepts": introduced_expected_concepts,
                    "regressed_expected_concepts": regressed_expected_concepts,
                }
            )

        if not preview_signals:
            missing_operation_ids.append(str(operation.get("operation_id") or ""))
        operation_previews.append(
            {
                "operation_id": operation["operation_id"],
                "operation_type": operation["operation_type"],
                "source_concept_keys": source_concept_keys,
                "successor_concept_keys": successor_concept_keys,
                "previewed_document_count": len(preview_signals),
                "regressed_document_count": sum(
                    1
                    for signal in preview_signals
                    if signal.get("regressed_expected_concepts")
                ),
                "preview_signals": preview_signals,
            }
        )

    operations_with_preview_count = sum(
        1 for preview in operation_previews if preview["previewed_document_count"] > 0
    )
    return {
        "required": True,
        "evidence_complete": not missing_operation_ids,
        "operation_count": len(operation_previews),
        "operations_with_preview_count": operations_with_preview_count,
        "operations_without_preview_count": len(missing_operation_ids),
        "missing_operation_ids": missing_operation_ids,
        "operations": operation_previews,
    }


def assert_lifecycle_verification_preview_ready(
    *,
    operations: list[dict[str, Any]],
    lifecycle_preview: dict[str, Any] | None,
) -> None:
    if not has_lifecycle_registry_operations(operations):
        return
    if lifecycle_preview is None:
        raise ValueError(
            "Lifecycle ontology apply requires explicit document-level preview evidence from "
            "verify_draft_ontology_extension."
        )
    if not lifecycle_preview.get("evidence_complete", False):
        raise ValueError(
            "Lifecycle ontology apply requires preview evidence for every non-additive "
            "operation before publication."
        )


def lifecycle_verification_success_metrics(
    *,
    lifecycle_preview: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if lifecycle_preview is None:
        return []
    return [
        {
            "metric_key": "lifecycle_regression_preview",
            "stakeholder": "Milestone",
            "passed": bool(lifecycle_preview.get("evidence_complete")),
            "summary": (
                "Lifecycle verification captures explicit document-level preview signals for "
                "every non-additive ontology operation."
            ),
            "details": {
                "operation_count": lifecycle_preview.get("operation_count", 0),
                "operations_without_preview_count": lifecycle_preview.get(
                    "operations_without_preview_count", 0
                ),
                "missing_operation_ids": lifecycle_preview.get("missing_operation_ids") or [],
            },
        }
    ]


def lifecycle_apply_success_metrics(
    *,
    lifecycle_preview: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if lifecycle_preview is None:
        return []
    return [
        {
            "metric_key": "lifecycle_preview_preserved",
            "stakeholder": "Milestone",
            "passed": bool(lifecycle_preview.get("evidence_complete")),
            "summary": (
                "Publication carries forward the verified lifecycle preview evidence that "
                "justified the ontology change."
            ),
            "details": {
                "operation_count": lifecycle_preview.get("operation_count", 0),
                "operations_with_preview_count": lifecycle_preview.get(
                    "operations_with_preview_count", 0
                ),
            },
        }
    ]


__all__ = [
    "assert_lifecycle_verification_preview_ready",
    "build_lifecycle_verification_preview",
    "has_lifecycle_registry_operations",
    "lifecycle_apply_success_metrics",
    "lifecycle_verification_success_metrics",
]
