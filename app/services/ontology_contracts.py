from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.files import repo_root
from app.services.ontology_contract_reporting import (
    render_ontology_contract_report,
    semantic_evaluation_corpus_summary,
    write_ontology_contract_report,
)
from app.services.semantic_registry import (
    load_semantic_registry_payload,
    semantic_registry_from_payload,
)

DEFAULT_ONTOLOGY_CONTRACT_PATH = Path("config") / "ontology" / "docling_ontology_contract.json"
REQUIRED_LAYER_KINDS = (
    "upper_ontology",
    "application_ontology",
    "domain_overlay",
    "report_semantics",
    "evaluation_coverage",
)
REQUIRED_SLICE_KEYS = (
    "core",
    "application_semantics",
    "domain_overlays",
    "report_semantics",
    "evaluation_coverage",
)
REQUIRED_COMPETENCY_FAMILIES = (
    "claim_support",
    "measurement_or_unit",
    "actor_or_obligation",
    "document_or_source_linkage",
)


def resolve_ontology_contract_path(
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> Path:
    root = project_root or repo_root()
    raw_path = Path(path) if path is not None else DEFAULT_ONTOLOGY_CONTRACT_PATH
    return raw_path if raw_path.is_absolute() else root / raw_path


def load_ontology_contract_payload(
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    resolved_path = resolve_ontology_contract_path(path, project_root=project_root)
    if not resolved_path.is_file():
        raise ValueError(f"Ontology contract path does not exist: {resolved_path}")
    payload = json.loads(resolved_path.read_text())
    return validate_ontology_contract_payload(payload)


def validate_ontology_contract_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Ontology contract must be a mapping.")
    if str(payload.get("schema_name") or "").strip() != "docling_ontology_contract":
        raise ValueError("Ontology contract requires schema_name=docling_ontology_contract.")
    for field in ("schema_version", "contract_name", "contract_version", "upper_ontology_version"):
        if not str(payload.get(field) or "").strip():
            raise ValueError(f"Ontology contract requires a non-empty {field}.")
    layers = payload.get("layers")
    if not isinstance(layers, list) or not layers:
        raise ValueError("Ontology contract requires a non-empty layers list.")
    slices = payload.get("slices")
    if not isinstance(slices, list) or not slices:
        raise ValueError("Ontology contract requires a non-empty slices list.")
    competency_families = payload.get("competency_families")
    if not isinstance(competency_families, list) or not competency_families:
        raise ValueError("Ontology contract requires a non-empty competency_families list.")
    legacy_views = payload.get("legacy_views")
    if not isinstance(legacy_views, list) or not legacy_views:
        raise ValueError("Ontology contract requires a non-empty legacy_views list.")
    return payload


def compile_legacy_view_payload(
    payload: dict[str, Any],
    view_key: str,
) -> dict[str, Any]:
    contract = validate_ontology_contract_payload(payload)
    legacy_view = next(
        (
            view
            for view in contract.get("legacy_views") or []
            if _required_text(view, "view_key", context="legacy view") == view_key
        ),
        None,
    )
    if legacy_view is None:
        raise ValueError(f"Unknown ontology legacy view: {view_key}")
    source_layer_keys = _required_string_list(
        legacy_view,
        "source_layer_keys",
        context=f"legacy view {view_key}",
    )
    return compile_contract_registry_payload(
        contract,
        layer_keys=source_layer_keys,
        missing_layer_context=f"Legacy view {view_key}",
    )


def compile_contract_registry_payload(
    payload: dict[str, Any],
    *,
    layer_keys: list[str] | tuple[str, ...] | None = None,
    missing_layer_context: str = "Ontology contract",
) -> dict[str, Any]:
    contract = validate_ontology_contract_payload(payload)
    layers_by_key = {
        _required_text(layer, "layer_key", context="layer"): layer
        for layer in contract.get("layers") or []
    }
    selected_layer_keys = list(layer_keys or layers_by_key.keys())
    compiled: dict[str, Any] = {
        "registry_name": contract["contract_name"],
        "registry_version": contract["contract_version"],
        "upper_ontology_version": contract["upper_ontology_version"],
        "categories": [],
        "concepts": [],
        "entity_types": [],
        "relations": [],
    }
    for layer_key in selected_layer_keys:
        layer = layers_by_key.get(layer_key)
        if layer is None:
            raise ValueError(
                f"{missing_layer_context} references unknown source layer {layer_key}."
            )
        registry_payload = _layer_registry_payload(layer)
        for field in ("categories", "concepts", "entity_types", "relations"):
            compiled[field].extend(registry_payload.get(field) or [])
    semantic_registry_from_payload(compiled)
    return compiled


def inspect_ontology_contract(
    payload: dict[str, Any],
    *,
    strict: bool = False,
    project_root: Path | None = None,
    semantic_evaluation_corpus_path: str | Path | None = None,
) -> dict[str, Any]:
    contract = validate_ontology_contract_payload(payload)
    root = project_root or repo_root()
    errors: list[str] = []
    warnings: list[str] = []

    layers: list[dict[str, Any]] = []
    seen_layer_keys: set[str] = set()
    seen_layer_kinds: set[str] = set()
    for raw_layer in contract.get("layers") or []:
        layer_key = _required_text(raw_layer, "layer_key", context="layer")
        layer_kind = _required_text(raw_layer, "layer_kind", context=f"layer {layer_key}")
        layer_version = _required_text(raw_layer, "layer_version", context=f"layer {layer_key}")
        if layer_key in seen_layer_keys:
            errors.append(f"Duplicate ontology layer_key: {layer_key}")
        seen_layer_keys.add(layer_key)
        if layer_kind in seen_layer_kinds:
            errors.append(f"Duplicate ontology layer_kind: {layer_kind}")
        seen_layer_kinds.add(layer_kind)
        registry_payload = _layer_registry_payload(raw_layer)
        layers.append(
            {
                "layer_key": layer_key,
                "layer_kind": layer_kind,
                "layer_version": layer_version,
                "include_in_legacy_registry": bool(raw_layer.get("include_in_legacy_registry")),
                "entity_type_count": len(registry_payload.get("entity_types") or []),
                "category_count": len(registry_payload.get("categories") or []),
                "concept_count": len(registry_payload.get("concepts") or []),
                "relation_count": len(registry_payload.get("relations") or []),
            }
        )
    if strict:
        for layer_kind in REQUIRED_LAYER_KINDS:
            if layer_kind not in seen_layer_kinds:
                errors.append(f"Missing required ontology layer_kind: {layer_kind}")
        try:
            compile_contract_registry_payload(contract)
        except ValueError as exc:
            errors.append(str(exc))

    layer_keys = {row["layer_key"] for row in layers}
    slices: list[dict[str, Any]] = []
    seen_slice_keys: set[str] = set()
    for raw_slice in contract.get("slices") or []:
        slice_key = _required_text(raw_slice, "slice_key", context="slice")
        if slice_key in seen_slice_keys:
            errors.append(f"Duplicate ontology slice_key: {slice_key}")
        seen_slice_keys.add(slice_key)
        slice_layer_keys = _required_string_list(
            raw_slice,
            "layer_keys",
            context=f"slice {slice_key}",
        )
        for layer_key in slice_layer_keys:
            if layer_key not in layer_keys:
                errors.append(
                    f"Ontology slice {slice_key} references unknown layer_key {layer_key}"
                )
        entity_type_keys = _optional_string_list(raw_slice, "entity_type_keys")
        relation_keys = _optional_string_list(raw_slice, "relation_keys")
        slices.append(
            {
                "slice_key": slice_key,
                "status": str(raw_slice.get("status") or "unspecified").strip() or "unspecified",
                "layer_keys": slice_layer_keys,
                "entity_type_count": len(entity_type_keys),
                "relation_count": len(relation_keys),
            }
        )
    if strict:
        for slice_key in REQUIRED_SLICE_KEYS:
            if slice_key not in seen_slice_keys:
                errors.append(f"Missing required ontology slice_key: {slice_key}")

    competency_families: list[dict[str, Any]] = []
    seen_family_keys: set[str] = set()
    for raw_family in contract.get("competency_families") or []:
        family_key = _required_text(raw_family, "family_key", context="competency family")
        if family_key in seen_family_keys:
            errors.append(f"Duplicate ontology competency family: {family_key}")
        seen_family_keys.add(family_key)
        slice_keys = _required_string_list(
            raw_family,
            "slice_keys",
            context=f"competency family {family_key}",
        )
        for slice_key in slice_keys:
            if slice_key not in seen_slice_keys:
                errors.append(
                    f"Ontology competency family {family_key} references unknown slice_key "
                    f"{slice_key}"
                )
        competency_families.append(
            {
                "family_key": family_key,
                "status": str(raw_family.get("status") or "unspecified").strip() or "unspecified",
                "slice_keys": slice_keys,
            }
        )
    if strict:
        for family_key in REQUIRED_COMPETENCY_FAMILIES:
            if family_key not in seen_family_keys:
                errors.append(f"Missing required ontology competency family: {family_key}")

    legacy_views: list[dict[str, Any]] = []
    seen_view_keys: set[str] = set()
    for raw_view in contract.get("legacy_views") or []:
        view_key = _required_text(raw_view, "view_key", context="legacy view")
        if view_key in seen_view_keys:
            errors.append(f"Duplicate ontology legacy view: {view_key}")
        seen_view_keys.add(view_key)
        relative_path = _required_text(raw_view, "path", context=f"legacy view {view_key}")
        view_path = _resolved_project_path(root, relative_path)
        try:
            compiled_payload = compile_legacy_view_payload(contract, view_key)
            compiled_registry = semantic_registry_from_payload(compiled_payload)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        view_row = {
            "view_key": view_key,
            "path": relative_path,
            "exists": view_path.is_file(),
            "in_sync": False,
            "entity_type_count": len(compiled_payload.get("entity_types") or []),
            "category_count": len(compiled_payload.get("categories") or []),
            "concept_count": len(compiled_payload.get("concepts") or []),
            "relation_count": len(compiled_payload.get("relations") or []),
            "compiled_sha256": compiled_registry.sha256,
        }
        if view_path.is_file():
            existing_payload = load_semantic_registry_payload(view_path)
            view_row["in_sync"] = existing_payload == compiled_payload
            if strict and not view_row["in_sync"]:
                errors.append(f"Legacy ontology view is out of sync: {relative_path}")
        else:
            errors.append(f"Legacy ontology view path does not exist: {relative_path}")
        legacy_views.append(view_row)

    semantic_corpus = semantic_evaluation_corpus_summary(
        project_root=root,
        path=semantic_evaluation_corpus_path,
    )
    if not semantic_corpus["exists"]:
        warnings.append("Semantic evaluation corpus path does not exist.")
    elif (
        semantic_corpus["document_count"] == 0
        and semantic_corpus["ontology_slice_expectation_count"] == 0
        and semantic_corpus["ontology_competency_family_expectation_count"] == 0
    ):
        warnings.append("Semantic evaluation corpus is present but currently empty.")

    return {
        "schema_name": contract["schema_name"],
        "schema_version": contract["schema_version"],
        "contract_name": contract["contract_name"],
        "contract_version": contract["contract_version"],
        "upper_ontology_version": contract["upper_ontology_version"],
        "valid": not errors,
        "strict": strict,
        "errors": errors,
        "warnings": warnings,
        "layer_count": len(layers),
        "layers": layers,
        "slice_count": len(slices),
        "slices": slices,
        "competency_family_count": len(competency_families),
        "competency_families": competency_families,
        "legacy_view_count": len(legacy_views),
        "legacy_views": legacy_views,
        "semantic_evaluation_corpus": semantic_corpus,
    }


def _layer_registry_payload(layer: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    registry_payload = layer.get("registry_payload")
    if not isinstance(registry_payload, dict):
        raise ValueError(
            f"Ontology layer {_required_text(layer, 'layer_key', context='layer')} requires a "
            "registry_payload mapping."
        )
    normalized: dict[str, list[dict[str, Any]]] = {}
    for field in ("categories", "concepts", "entity_types", "relations"):
        value = registry_payload.get(field) or []
        if not isinstance(value, list):
            raise ValueError(f"Ontology layer field registry_payload.{field} must be a list.")
        normalized[field] = value
    return normalized


def _required_text(payload: dict[str, Any], field: str, *, context: str) -> str:
    value = str(payload.get(field) or "").strip()
    if not value:
        raise ValueError(f"{context} requires a non-empty {field}.")
    return value


def _required_string_list(payload: dict[str, Any], field: str, *, context: str) -> list[str]:
    values = _optional_string_list(payload, field)
    if not values:
        raise ValueError(f"{context} requires a non-empty {field} list.")
    return values


def _optional_string_list(payload: dict[str, Any], field: str) -> list[str]:
    raw_values = payload.get(field) or []
    if not isinstance(raw_values, list):
        raise ValueError(f"Ontology contract field {field} must be a list when provided.")
    values = [str(value or "").strip() for value in raw_values]
    return [value for value in values if value]


def _resolved_project_path(project_root: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else project_root / path


__all__ = [
    "compile_contract_registry_payload",
    "DEFAULT_ONTOLOGY_CONTRACT_PATH",
    "compile_legacy_view_payload",
    "inspect_ontology_contract",
    "load_ontology_contract_payload",
    "render_ontology_contract_report",
    "resolve_ontology_contract_path",
    "validate_ontology_contract_payload",
    "write_ontology_contract_report",
]
