from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from app.db.public.ingest import Document, DocumentRun
from app.db.public.semantic_memory import DocumentRunSemanticPass
from app.services.semantic_registry import SemanticRegistry
from app.services.storage import StorageService

SEMANTIC_ARTIFACT_SCHEMA_NAME = "docling.semantic_pass"
SEMANTIC_ARTIFACT_SCHEMA_VERSION = "2.1"
SEMANTIC_EXTRACTOR_VERSION = "semantics_sidecar_v2_1"
SEMANTIC_MATCH_STRATEGY = "normalized_phrase_contains"
SEMANTIC_EVAL_VERSION = 2


def semantic_artifact_payload(
    *,
    document: Document,
    run: DocumentRun,
    semantic_pass: DocumentRunSemanticPass,
    registry: SemanticRegistry,
    assertions: list[dict[str, Any]],
    concept_category_bindings: list[dict[str, Any]],
    summary: dict[str, Any],
    evaluation_status: str,
    evaluation_fixture_name: str | None,
    evaluation_summary: dict[str, Any],
    continuity_summary: dict[str, Any],
    artifact_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_name": SEMANTIC_ARTIFACT_SCHEMA_NAME,
        "schema_version": SEMANTIC_ARTIFACT_SCHEMA_VERSION,
        "artifact_sha256": artifact_sha256,
        "document_id": str(document.id),
        "run_id": str(run.id),
        "semantic_pass_id": str(semantic_pass.id),
        "ontology_snapshot_id": (
            str(semantic_pass.ontology_snapshot_id) if semantic_pass.ontology_snapshot_id else None
        ),
        "baseline_run_id": str(semantic_pass.baseline_run_id)
        if semantic_pass.baseline_run_id
        else None,
        "baseline_semantic_pass_id": (
            str(semantic_pass.baseline_semantic_pass_id)
            if semantic_pass.baseline_semantic_pass_id
            else None
        ),
        "status": semantic_pass.status,
        "created_at": semantic_pass.created_at.isoformat(),
        "completed_at": semantic_pass.completed_at.isoformat()
        if semantic_pass.completed_at
        else None,
        "registry": {
            "name": registry.registry_name,
            "version": registry.registry_version,
            "sha256": registry.sha256,
            "upper_ontology_version": registry.upper_ontology_version,
        },
        "extractor": {
            "version": SEMANTIC_EXTRACTOR_VERSION,
            "match_strategy": SEMANTIC_MATCH_STRATEGY,
        },
        "summary": summary,
        "evaluation": {
            "status": evaluation_status,
            "fixture_name": evaluation_fixture_name,
            "version": SEMANTIC_EVAL_VERSION,
            "summary": evaluation_summary,
        },
        "continuity": continuity_summary,
        "concept_category_bindings": concept_category_bindings,
        "assertions": assertions,
    }


def persist_semantic_artifacts(
    storage_service: StorageService,
    document: Document,
    run: DocumentRun,
    semantic_pass: DocumentRunSemanticPass,
    registry: SemanticRegistry,
    assertions: list[dict[str, Any]],
    concept_category_bindings: list[dict[str, Any]],
    summary: dict[str, Any],
    evaluation_status: str,
    evaluation_fixture_name: str | None,
    evaluation_summary: dict[str, Any],
    continuity_summary: dict[str, Any],
) -> tuple[Path, Path, str, str]:
    base_payload = semantic_artifact_payload(
        document=document,
        run=run,
        semantic_pass=semantic_pass,
        registry=registry,
        assertions=assertions,
        concept_category_bindings=concept_category_bindings,
        summary=summary,
        evaluation_status=evaluation_status,
        evaluation_fixture_name=evaluation_fixture_name,
        evaluation_summary=evaluation_summary,
        continuity_summary=continuity_summary,
        artifact_sha256="",
    )
    normalized_base_payload = json.loads(json.dumps(base_payload, default=str))
    artifact_seed = hashlib.sha256(
        json.dumps(normalized_base_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    payload = semantic_artifact_payload(
        document=document,
        run=run,
        semantic_pass=semantic_pass,
        registry=registry,
        assertions=assertions,
        concept_category_bindings=concept_category_bindings,
        summary=summary,
        evaluation_status=evaluation_status,
        evaluation_fixture_name=evaluation_fixture_name,
        evaluation_summary=evaluation_summary,
        continuity_summary=continuity_summary,
        artifact_sha256=artifact_seed,
    )
    normalized_payload = json.loads(json.dumps(payload, default=str))
    json_path = storage_service.get_semantic_json_path(
        document.id,
        run.id,
        SEMANTIC_ARTIFACT_SCHEMA_VERSION,
    )
    yaml_path = storage_service.get_semantic_yaml_path(
        document.id,
        run.id,
        SEMANTIC_ARTIFACT_SCHEMA_VERSION,
    )
    json_bytes = json.dumps(normalized_payload, indent=2).encode("utf-8")
    yaml_bytes = yaml.safe_dump(normalized_payload, sort_keys=False, allow_unicode=True).encode(
        "utf-8"
    )
    json_path.write_bytes(json_bytes)
    yaml_path.write_bytes(yaml_bytes)
    return (
        json_path,
        yaml_path,
        hashlib.sha256(json_bytes).hexdigest(),
        hashlib.sha256(yaml_bytes).hexdigest(),
    )
