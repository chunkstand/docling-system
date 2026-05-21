from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.files import repo_root
from app.services.ontology_contracts import (
    load_ontology_contract_payload,
    resolve_ontology_contract_path,
)


def load_ontology_contract_runtime_metadata(
    contract_path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    root = project_root or repo_root()
    resolved_contract_path = resolve_ontology_contract_path(contract_path, project_root=root)
    metadata = _load_ontology_contract_runtime_metadata_cached(
        str(resolved_contract_path),
        str(root),
    )
    return json.loads(json.dumps(metadata))


@lru_cache(maxsize=2)
def _load_ontology_contract_runtime_metadata_cached(
    resolved_contract_path: str,
    project_root_path: str,
) -> dict[str, Any]:
    root = Path(project_root_path)
    contract_path = Path(resolved_contract_path)
    payload = load_ontology_contract_payload(contract_path, project_root=root)
    layer_versions: dict[str, str] = {}
    layer_kind_versions: dict[str, str] = {}
    for layer in payload.get("layers") or []:
        layer_key = str(layer.get("layer_key") or "").strip()
        layer_kind = str(layer.get("layer_kind") or "").strip()
        layer_version = str(layer.get("layer_version") or "").strip()
        if layer_key:
            layer_versions[layer_key] = layer_version
        if layer_kind:
            layer_kind_versions[layer_kind] = layer_version

    ontology_slices = []
    for raw_slice in payload.get("slices") or []:
        entity_type_keys = _string_list(raw_slice.get("entity_type_keys"))
        relation_keys = _string_list(raw_slice.get("relation_keys"))
        slice_payload = {
            "slice_key": str(raw_slice.get("slice_key") or "").strip(),
            "status": str(raw_slice.get("status") or "unspecified").strip() or "unspecified",
            "layer_keys": _string_list(raw_slice.get("layer_keys")),
            "entity_type_keys": entity_type_keys,
            "relation_keys": relation_keys,
            "entity_type_count": len(entity_type_keys),
            "relation_count": len(relation_keys),
        }
        slice_payload["slice_sha256"] = hashlib.sha256(
            json.dumps(slice_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        ontology_slices.append(slice_payload)

    competency_families = [
        {
            "family_key": str(raw_family.get("family_key") or "").strip(),
            "status": str(raw_family.get("status") or "unspecified").strip() or "unspecified",
            "slice_keys": _string_list(raw_family.get("slice_keys")),
        }
        for raw_family in (payload.get("competency_families") or [])
    ]
    return {
        "contract_path": _runtime_path_relative_to_root(contract_path, root),
        "contract_schema_name": payload["schema_name"],
        "contract_schema_version": payload["schema_version"],
        "contract_version": payload["contract_version"],
        "contract_upper_ontology_version": payload["upper_ontology_version"],
        "contract_sha256": hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "contract_layer_count": len(payload.get("layers") or []),
        "layer_versions": layer_versions,
        "layer_kind_versions": layer_kind_versions,
        "ontology_slice_count": len(ontology_slices),
        "ontology_slices": ontology_slices,
        "competency_family_count": len(competency_families),
        "competency_families": competency_families,
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item or "").strip())]


def _runtime_path_relative_to_root(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


__all__ = ["load_ontology_contract_runtime_metadata"]
