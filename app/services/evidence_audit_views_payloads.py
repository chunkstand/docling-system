from __future__ import annotations

from app.core.json_utils import json_object_payload as _json_payload
from app.db.models import AgentTaskArtifact
from app.services.evidence_provenance import (
    frozen_export_receipt as _frozen_export_receipt,
)
from app.services.evidence_release_readiness import (
    prov_export_receipt_integrity as _prov_export_receipt_integrity,
)


def provenance_export_receipt_payload(row: AgentTaskArtifact) -> dict:
    payload = _json_payload(row.payload_json or {})
    frozen_export = payload.get("frozen_export") or {}
    receipt = _frozen_export_receipt(payload)
    return {
        "artifact_id": row.id,
        "task_id": row.task_id,
        "artifact_kind": row.artifact_kind,
        "storage_path": row.storage_path,
        "export_payload_sha256": frozen_export.get("export_payload_sha256"),
        "prov_hash_basis_sha256": frozen_export.get("prov_hash_basis_sha256"),
        "export_receipt": receipt,
        "receipt_integrity": _prov_export_receipt_integrity(payload),
    }
