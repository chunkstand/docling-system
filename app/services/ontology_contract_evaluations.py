from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from app.core.files import repo_root
from app.services.ontology_contracts import (
    DEFAULT_ONTOLOGY_CONTRACT_PATH,
    compile_contract_registry_payload,
    validate_ontology_contract_payload,
)

DEFAULT_SEMANTIC_EVALUATION_CORPUS_PATH = Path("docs") / "semantic_evaluation_corpus.yaml"


def resolve_semantic_evaluation_corpus_path(
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> Path:
    root = project_root or repo_root()
    raw_path = Path(path) if path is not None else DEFAULT_SEMANTIC_EVALUATION_CORPUS_PATH
    return raw_path if raw_path.is_absolute() else root / raw_path


def load_ontology_evaluation_corpus(
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    resolved_path = resolve_semantic_evaluation_corpus_path(path, project_root=project_root)
    if not resolved_path.is_file():
        raise ValueError(f"Ontology evaluation corpus path does not exist: {resolved_path}")
    payload = yaml.safe_load(resolved_path.read_text()) or {}
    if not isinstance(payload, dict):
        raise ValueError("Ontology evaluation corpus must be a mapping.")
    return payload


def evaluate_ontology_contract(
    payload: dict[str, Any],
    *,
    project_root: Path | None = None,
    contract_path: str | Path | None = None,
    semantic_evaluation_corpus_path: str | Path | None = None,
) -> dict[str, Any]:
    contract = validate_ontology_contract_payload(payload)
    root = project_root or repo_root()
    errors: list[str] = []
    warnings: list[str] = []

    try:
        corpus = load_ontology_evaluation_corpus(
            semantic_evaluation_corpus_path,
            project_root=root,
        )
    except ValueError as exc:
        corpus = {}
        errors.append(str(exc))

    try:
        compiled_registry = compile_contract_registry_payload(contract)
    except ValueError as exc:
        compiled_registry = {
            "entity_types": [],
            "relations": [],
        }
        errors.append(str(exc))

    layers_by_key = {
        str(layer.get("layer_key") or "").strip(): layer for layer in contract.get("layers") or []
    }
    slices_by_key = {
        str(slice_row.get("slice_key") or "").strip(): slice_row
        for slice_row in contract.get("slices") or []
    }
    families_by_key = {
        str(family.get("family_key") or "").strip(): family
        for family in contract.get("competency_families") or []
    }

    ontology_eval = corpus.get("ontology_evaluation") or {}
    if corpus and not isinstance(ontology_eval, dict):
        errors.append("Ontology evaluation corpus field ontology_evaluation must be a mapping.")
        ontology_eval = {}
    if corpus and not ontology_eval:
        errors.append(
            "Ontology evaluation corpus requires a non-empty "
            "ontology_evaluation section."
        )

    raw_slice_expectations = ontology_eval.get("slice_expectations") or []
    if raw_slice_expectations and not isinstance(raw_slice_expectations, list):
        errors.append("Ontology evaluation corpus field slice_expectations must be a list.")
        raw_slice_expectations = []
    raw_family_expectations = ontology_eval.get("competency_family_expectations") or []
    if raw_family_expectations and not isinstance(raw_family_expectations, list):
        errors.append(
            "Ontology evaluation corpus field competency_family_expectations must be a list."
        )
        raw_family_expectations = []
    if corpus and not raw_slice_expectations:
        errors.append("Ontology evaluation corpus requires at least one slice_expectation.")
    if corpus and not raw_family_expectations:
        errors.append(
            "Ontology evaluation corpus requires at least one "
            "competency_family_expectation."
        )

    slice_results = [
        _evaluate_slice_expectation(
            expectation,
            slices_by_key=slices_by_key,
            layers_by_key=layers_by_key,
        )
        for expectation in raw_slice_expectations
        if isinstance(expectation, dict)
    ]
    family_results = [
        _evaluate_family_expectation(
            expectation,
            families_by_key=families_by_key,
            slices_by_key=slices_by_key,
            layers_by_key=layers_by_key,
        )
        for expectation in raw_family_expectations
        if isinstance(expectation, dict)
    ]

    if len(slice_results) != len(raw_slice_expectations):
        errors.append("Ontology evaluation corpus contains a non-mapping slice expectation.")
    if len(family_results) != len(raw_family_expectations):
        errors.append(
            "Ontology evaluation corpus contains a non-mapping "
            "competency family expectation."
        )

    if not slice_results:
        warnings.append("No ontology slice expectations were evaluated.")
    if not family_results:
        warnings.append("No ontology competency family expectations were evaluated.")

    slice_fail_count = sum(1 for result in slice_results if not result["passed"])
    family_fail_count = sum(1 for result in family_results if not result["passed"])
    overall_passed = not errors and slice_fail_count == 0 and family_fail_count == 0

    return {
        "schema_name": contract["schema_name"],
        "schema_version": contract["schema_version"],
        "contract_name": contract["contract_name"],
        "contract_version": contract["contract_version"],
        "upper_ontology_version": contract["upper_ontology_version"],
        "contract_path": _display_path(contract_path or DEFAULT_ONTOLOGY_CONTRACT_PATH, root=root),
        "semantic_evaluation_corpus_path": _display_path(
            semantic_evaluation_corpus_path or DEFAULT_SEMANTIC_EVALUATION_CORPUS_PATH,
            root=root,
        ),
        "corpus_name": corpus.get("corpus_name"),
        "overall_passed": overall_passed,
        "errors": errors,
        "warnings": warnings,
        "global_entity_type_count": len(compiled_registry.get("entity_types") or []),
        "global_relation_count": len(compiled_registry.get("relations") or []),
        "slice_result_count": len(slice_results),
        "slice_pass_count": len(slice_results) - slice_fail_count,
        "slice_fail_count": slice_fail_count,
        "slice_results": slice_results,
        "competency_family_result_count": len(family_results),
        "competency_family_pass_count": len(family_results) - family_fail_count,
        "competency_family_fail_count": family_fail_count,
        "competency_family_results": family_results,
    }


def write_ontology_evaluation_report(
    path: str | Path,
    *,
    report: dict[str, Any],
    project_root: Path | None = None,
) -> Path:
    root = project_root or repo_root()
    raw_path = Path(path)
    resolved_path = raw_path if raw_path.is_absolute() else root / raw_path
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return resolved_path


def _evaluate_slice_expectation(
    expectation: dict[str, Any],
    *,
    slices_by_key: dict[str, dict[str, Any]],
    layers_by_key: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    slice_key = str(expectation.get("slice_key") or "").strip()
    expected_status = str(expectation.get("expected_status") or "").strip() or None
    expected_layer_keys = _corpus_string_list(expectation, "required_layer_keys")
    required_entity_type_keys = _corpus_string_list(expectation, "required_entity_type_keys")
    required_relation_keys = _corpus_string_list(expectation, "required_relation_keys")
    raw_slice = slices_by_key.get(slice_key, {})

    actual_status = str(raw_slice.get("status") or "").strip() or None
    actual_layer_keys = _corpus_string_list(raw_slice, "layer_keys")
    declared_entity_type_keys = _corpus_string_list(raw_slice, "entity_type_keys")
    declared_relation_keys = _corpus_string_list(raw_slice, "relation_keys")
    layer_entity_type_keys = _layer_entity_type_keys(actual_layer_keys, layers_by_key=layers_by_key)
    layer_relation_keys = _layer_relation_keys(actual_layer_keys, layers_by_key=layers_by_key)

    missing_layer_keys = sorted(set(expected_layer_keys) - set(actual_layer_keys))
    missing_declared_entity_type_keys = sorted(
        set(required_entity_type_keys) - set(declared_entity_type_keys)
    )
    missing_layer_entity_type_keys = sorted(
        set(required_entity_type_keys) - set(layer_entity_type_keys)
    )
    missing_declared_relation_keys = sorted(
        set(required_relation_keys) - set(declared_relation_keys)
    )
    missing_layer_relation_keys = sorted(set(required_relation_keys) - set(layer_relation_keys))
    status_matches = expected_status is None or expected_status == actual_status

    return {
        "slice_key": slice_key,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "passed": bool(slice_key)
        and bool(raw_slice)
        and status_matches
        and not missing_layer_keys
        and not missing_declared_entity_type_keys
        and not missing_layer_entity_type_keys
        and not missing_declared_relation_keys
        and not missing_layer_relation_keys,
        "missing_layer_keys": missing_layer_keys,
        "missing_declared_entity_type_keys": missing_declared_entity_type_keys,
        "missing_layer_entity_type_keys": missing_layer_entity_type_keys,
        "missing_declared_relation_keys": missing_declared_relation_keys,
        "missing_layer_relation_keys": missing_layer_relation_keys,
    }


def _evaluate_family_expectation(
    expectation: dict[str, Any],
    *,
    families_by_key: dict[str, dict[str, Any]],
    slices_by_key: dict[str, dict[str, Any]],
    layers_by_key: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    family_key = str(expectation.get("family_key") or "").strip()
    expected_status = str(expectation.get("expected_status") or "").strip() or None
    expected_slice_keys = _corpus_string_list(expectation, "required_slice_keys")
    required_entity_type_keys = _corpus_string_list(expectation, "required_entity_type_keys")
    required_relation_keys = _corpus_string_list(expectation, "required_relation_keys")
    competency_questions = _corpus_string_list(expectation, "competency_questions")
    raw_family = families_by_key.get(family_key, {})

    actual_status = str(raw_family.get("status") or "").strip() or None
    actual_slice_keys = _corpus_string_list(raw_family, "slice_keys")
    declared_entity_type_keys = _family_entity_type_keys(
        actual_slice_keys,
        slices_by_key=slices_by_key,
        layers_by_key=layers_by_key,
        include_declared=True,
        include_layers=False,
    )
    layer_entity_type_keys = _family_entity_type_keys(
        actual_slice_keys,
        slices_by_key=slices_by_key,
        layers_by_key=layers_by_key,
        include_declared=False,
        include_layers=True,
    )
    declared_relation_keys = _family_relation_keys(
        actual_slice_keys,
        slices_by_key=slices_by_key,
        layers_by_key=layers_by_key,
        include_declared=True,
        include_layers=False,
    )
    layer_relation_keys = _family_relation_keys(
        actual_slice_keys,
        slices_by_key=slices_by_key,
        layers_by_key=layers_by_key,
        include_declared=False,
        include_layers=True,
    )

    missing_slice_keys = sorted(set(expected_slice_keys) - set(actual_slice_keys))
    missing_declared_entity_type_keys = sorted(
        set(required_entity_type_keys) - set(declared_entity_type_keys)
    )
    missing_layer_entity_type_keys = sorted(
        set(required_entity_type_keys) - set(layer_entity_type_keys)
    )
    missing_declared_relation_keys = sorted(
        set(required_relation_keys) - set(declared_relation_keys)
    )
    missing_layer_relation_keys = sorted(set(required_relation_keys) - set(layer_relation_keys))
    status_matches = expected_status is None or expected_status == actual_status

    return {
        "family_key": family_key,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "passed": bool(family_key)
        and bool(raw_family)
        and status_matches
        and not missing_slice_keys
        and not missing_declared_entity_type_keys
        and not missing_layer_entity_type_keys
        and not missing_declared_relation_keys
        and not missing_layer_relation_keys
        and bool(competency_questions),
        "missing_slice_keys": missing_slice_keys,
        "missing_declared_entity_type_keys": missing_declared_entity_type_keys,
        "missing_layer_entity_type_keys": missing_layer_entity_type_keys,
        "missing_declared_relation_keys": missing_declared_relation_keys,
        "missing_layer_relation_keys": missing_layer_relation_keys,
        "competency_question_count": len(competency_questions),
    }


def _family_entity_type_keys(
    slice_keys: list[str],
    *,
    slices_by_key: dict[str, dict[str, Any]],
    layers_by_key: dict[str, dict[str, Any]],
    include_declared: bool,
    include_layers: bool,
) -> list[str]:
    entity_type_keys: set[str] = set()
    for slice_key in slice_keys:
        raw_slice = slices_by_key.get(slice_key, {})
        actual_layer_keys = _corpus_string_list(raw_slice, "layer_keys")
        if include_declared:
            entity_type_keys.update(_corpus_string_list(raw_slice, "entity_type_keys"))
        if include_layers:
            entity_type_keys.update(
                _layer_entity_type_keys(actual_layer_keys, layers_by_key=layers_by_key)
            )
    return sorted(entity_type_keys)


def _family_relation_keys(
    slice_keys: list[str],
    *,
    slices_by_key: dict[str, dict[str, Any]],
    layers_by_key: dict[str, dict[str, Any]],
    include_declared: bool,
    include_layers: bool,
) -> list[str]:
    relation_keys: set[str] = set()
    for slice_key in slice_keys:
        raw_slice = slices_by_key.get(slice_key, {})
        actual_layer_keys = _corpus_string_list(raw_slice, "layer_keys")
        if include_declared:
            relation_keys.update(_corpus_string_list(raw_slice, "relation_keys"))
        if include_layers:
            relation_keys.update(
                _layer_relation_keys(actual_layer_keys, layers_by_key=layers_by_key)
            )
    return sorted(relation_keys)


def _layer_entity_type_keys(
    layer_keys: list[str],
    *,
    layers_by_key: dict[str, dict[str, Any]],
) -> list[str]:
    entity_type_keys: set[str] = set()
    for layer_key in layer_keys:
        layer = layers_by_key.get(layer_key, {})
        registry_payload = layer.get("registry_payload") or {}
        for entity_type in registry_payload.get("entity_types") or []:
            if isinstance(entity_type, dict):
                entity_type_key = str(entity_type.get("entity_type") or "").strip()
                if entity_type_key:
                    entity_type_keys.add(entity_type_key)
    return sorted(entity_type_keys)


def _layer_relation_keys(
    layer_keys: list[str],
    *,
    layers_by_key: dict[str, dict[str, Any]],
) -> list[str]:
    relation_keys: set[str] = set()
    for layer_key in layer_keys:
        layer = layers_by_key.get(layer_key, {})
        registry_payload = layer.get("registry_payload") or {}
        for relation in registry_payload.get("relations") or []:
            if isinstance(relation, dict):
                relation_key = str(relation.get("relation_key") or "").strip()
                if relation_key:
                    relation_keys.add(relation_key)
    return sorted(relation_keys)


def _corpus_string_list(payload: dict[str, Any], field: str) -> list[str]:
    raw_values = payload.get(field) or []
    if not isinstance(raw_values, list):
        return []
    values = [str(value or "").strip() for value in raw_values]
    return [value for value in values if value]


def _display_path(path: str | Path, *, root: Path) -> str:
    resolved_path = Path(path)
    candidate = resolved_path if resolved_path.is_absolute() else root / resolved_path
    try:
        return str(candidate.relative_to(root))
    except ValueError:
        return str(candidate)


__all__ = [
    "DEFAULT_SEMANTIC_EVALUATION_CORPUS_PATH",
    "evaluate_ontology_contract",
    "load_ontology_evaluation_corpus",
    "resolve_semantic_evaluation_corpus_path",
    "write_ontology_evaluation_report",
]
