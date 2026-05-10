from __future__ import annotations

import hmac
from collections.abc import Callable
from typing import Any
from uuid import UUID

from app.core.hashes import hmac_sha256_hex as _receipt_signature_value
from app.core.json_utils import json_object_payload as _json_payload
from app.services.evidence_common import clean_mapping, payload_sha256

TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND = "technical_report_prov_export"
TECHNICAL_REPORT_PROV_EXPORT_FILENAME = "technical_report_prov_export.json"
TECHNICAL_REPORT_PROV_EXPORT_RECEIPT_SCHEMA = "technical_report_prov_export_receipt"
PROV_EXPORT_RECEIPT_SIGNATURE_ALGORITHM = "hmac-sha256"
PROV_INTEGRITY_EXCLUDED_FIELDS = {"frozen_export", "prov_integrity"}


def prov_identifier(table: str | None, value: Any) -> str | None:
    if table is None or value is None or value == "":
        return None
    normalized_table = str(table).replace("_", "-")
    return f"docling:{normalized_table}/{value}"


def add_prov_entity(
    entities: dict[str, dict[str, Any]],
    entity_id: str | None,
    *,
    label: str,
    entity_type: str,
    **attrs: Any,
) -> None:
    if entity_id is None:
        return
    payload = {
        "prov:label": label,
        "prov:type": entity_type,
        **{key: value for key, value in attrs.items() if value is not None and value != []},
    }
    existing = entities.get(entity_id)
    if existing is None:
        entities[entity_id] = payload
        return
    existing.update({key: value for key, value in payload.items() if value is not None})


def add_prov_activity(
    activities: dict[str, dict[str, Any]],
    activity_id: str | None,
    *,
    label: str,
    activity_type: str,
    started_at: Any = None,
    ended_at: Any = None,
    **attrs: Any,
) -> None:
    if activity_id is None:
        return
    payload = {
        "prov:label": label,
        "prov:type": activity_type,
        "prov:startTime": started_at,
        "prov:endTime": ended_at,
        **{key: value for key, value in attrs.items() if value is not None and value != []},
    }
    activities[activity_id] = {key: value for key, value in payload.items() if value is not None}


def add_prov_relation(
    relations: dict[str, dict[str, Any]],
    relation_prefix: str,
    *,
    sequence: int,
    **attrs: Any,
) -> None:
    relations[f"docling:{relation_prefix}/{sequence:06d}"] = {
        key: value for key, value in attrs.items() if value is not None
    }


def missing_relation_references(
    relations: dict[str, dict[str, Any]],
    *,
    relation_type: str,
    reference_field: str,
    declared_ids: set[str],
) -> list[dict[str, Any]]:
    missing_references: list[dict[str, Any]] = []
    for relation_id, relation in sorted(relations.items()):
        reference_id = relation.get(reference_field)
        if not reference_id or reference_id not in declared_ids:
            missing_references.append(
                {
                    "relation_type": relation_type,
                    "relation_id": relation_id,
                    "reference_field": reference_field,
                    "reference_id": reference_id,
                }
            )
    return missing_references


def prov_export_integrity_payload(prov_export: dict[str, Any]) -> dict[str, Any]:
    entities = set((prov_export.get("entity") or {}).keys())
    activities = set((prov_export.get("activity") or {}).keys())
    agents = set((prov_export.get("agent") or {}).keys())
    audit = prov_export.get("audit") or {}
    retrieval_evaluation = prov_export.get("retrieval_evaluation") or {}
    summary = prov_export.get("prov_summary") or {}

    was_generated_by = prov_export.get("wasGeneratedBy") or {}
    used = prov_export.get("used") or {}
    was_derived_from = prov_export.get("wasDerivedFrom") or {}
    was_associated_with = prov_export.get("wasAssociatedWith") or {}
    was_attributed_to = prov_export.get("wasAttributedTo") or {}

    missing_generated_entities = missing_relation_references(
        was_generated_by,
        relation_type="wasGeneratedBy",
        reference_field="prov:entity",
        declared_ids=entities,
    )
    missing_generation_activities = missing_relation_references(
        was_generated_by,
        relation_type="wasGeneratedBy",
        reference_field="prov:activity",
        declared_ids=activities,
    )
    missing_used_activities = missing_relation_references(
        used,
        relation_type="used",
        reference_field="prov:activity",
        declared_ids=activities,
    )
    missing_used_entities = missing_relation_references(
        used,
        relation_type="used",
        reference_field="prov:entity",
        declared_ids=entities,
    )
    missing_derived_generated_entities = missing_relation_references(
        was_derived_from,
        relation_type="wasDerivedFrom",
        reference_field="prov:generatedEntity",
        declared_ids=entities,
    )
    missing_derived_used_entities = missing_relation_references(
        was_derived_from,
        relation_type="wasDerivedFrom",
        reference_field="prov:usedEntity",
        declared_ids=entities,
    )
    missing_association_activities = missing_relation_references(
        was_associated_with,
        relation_type="wasAssociatedWith",
        reference_field="prov:activity",
        declared_ids=activities,
    )
    missing_association_agents = missing_relation_references(
        was_associated_with,
        relation_type="wasAssociatedWith",
        reference_field="prov:agent",
        declared_ids=agents,
    )
    missing_attribution_entities = missing_relation_references(
        was_attributed_to,
        relation_type="wasAttributedTo",
        reference_field="prov:entity",
        declared_ids=entities,
    )
    missing_attribution_agents = missing_relation_references(
        was_attributed_to,
        relation_type="wasAttributedTo",
        reference_field="prov:agent",
        declared_ids=agents,
    )
    missing_relation_reference_list = [
        *missing_generated_entities,
        *missing_generation_activities,
        *missing_used_activities,
        *missing_used_entities,
        *missing_derived_generated_entities,
        *missing_derived_used_entities,
        *missing_association_activities,
        *missing_association_agents,
        *missing_attribution_entities,
        *missing_attribution_agents,
    ]

    hash_basis = clean_mapping(prov_export, drop_fields=PROV_INTEGRITY_EXCLUDED_FIELDS)
    manifest_integrity_complete = bool((audit.get("manifest_integrity") or {}).get("complete"))
    trace_integrity_complete = bool((audit.get("trace_integrity") or {}).get("complete"))
    retrieval_evaluation_complete = bool(retrieval_evaluation.get("complete"))
    has_required_prov_surface = bool(entities and activities and was_derived_from)
    relation_references_complete = not missing_relation_reference_list

    return {
        "hash_policy": "sha256 over canonical JSON excluding frozen_export and prov_integrity",
        "hash_basis_schema": "technical_report_prov_export_without_integrity_v1",
        "hash_basis_fields": sorted(hash_basis.keys()),
        "hash_excluded_fields": sorted(PROV_INTEGRITY_EXCLUDED_FIELDS),
        "prov_sha256": payload_sha256(hash_basis),
        "manifest_integrity_complete": manifest_integrity_complete,
        "trace_integrity_complete": trace_integrity_complete,
        "retrieval_evaluation_complete": retrieval_evaluation_complete,
        "has_required_prov_surface": has_required_prov_surface,
        "all_generated_entities_declared": not missing_generated_entities,
        "all_generation_activities_declared": not missing_generation_activities,
        "all_used_activities_declared": not missing_used_activities,
        "all_used_entities_declared": not missing_used_entities,
        "all_derived_generated_entities_declared": not missing_derived_generated_entities,
        "all_derived_used_entities_declared": not missing_derived_used_entities,
        "all_association_activities_declared": not missing_association_activities,
        "all_association_agents_declared": not missing_association_agents,
        "all_attribution_entities_declared": not missing_attribution_entities,
        "all_attribution_agents_declared": not missing_attribution_agents,
        "all_relation_references_declared": relation_references_complete,
        "missing_relation_reference_count": len(missing_relation_reference_list),
        "missing_relation_references": missing_relation_reference_list,
        "relation_count": int(summary.get("relation_count") or 0),
        "complete": bool(
            manifest_integrity_complete
            and trace_integrity_complete
            and retrieval_evaluation_complete
            and has_required_prov_surface
            and relation_references_complete
        ),
    }


def prov_export_receipt_signature(
    receipt_sha256: str,
    *,
    settings_provider: Callable[[], Any],
) -> dict[str, Any]:
    settings = settings_provider()
    signing_key = getattr(settings, "audit_bundle_signing_key", None)
    if not signing_key:
        return {
            "signature_status": "unsigned",
            "signature": None,
            "signature_algorithm": PROV_EXPORT_RECEIPT_SIGNATURE_ALGORITHM,
            "signing_key_id": None,
        }
    signing_key_id = getattr(settings, "audit_bundle_signing_key_id", None) or "local"
    return {
        "signature_status": "signed",
        "signature": _receipt_signature_value(receipt_sha256, str(signing_key)),
        "signature_algorithm": PROV_EXPORT_RECEIPT_SIGNATURE_ALGORITHM,
        "signing_key_id": str(signing_key_id),
    }


def prov_export_receipt(
    prov_export: dict[str, Any],
    *,
    artifact_id: UUID,
    task_id: UUID,
    created_at: Any,
    storage_path: str | None,
    export_payload_sha256: str | None,
    prov_hash_basis_sha256: str | None,
    settings_provider: Callable[[], Any],
) -> dict[str, Any]:
    audit = prov_export.get("audit") or {}
    frozen_at = created_at.isoformat() if hasattr(created_at, "isoformat") else created_at
    receipt_core = {
        "schema_name": TECHNICAL_REPORT_PROV_EXPORT_RECEIPT_SCHEMA,
        "schema_version": "1.0",
        "artifact_id": str(artifact_id),
        "artifact_kind": TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        "task_id": str(task_id),
        "storage_path": storage_path,
        "frozen_at": frozen_at,
        "receipt_policy": (
            "Hash-chain receipt for the immutable technical-report PROV export. "
            "The receipt links the evidence manifest, evidence trace, PROV hash basis, "
            "and frozen export payload."
        ),
        "hash_chain": [
            {
                "position": 1,
                "name": "evidence_manifest",
                "sha256": audit.get("manifest_sha256"),
            },
            {
                "position": 2,
                "name": "evidence_trace",
                "sha256": audit.get("trace_sha256"),
            },
            {
                "position": 3,
                "name": "prov_hash_basis",
                "sha256": prov_hash_basis_sha256,
                "derived_from": ["evidence_manifest", "evidence_trace"],
            },
            {
                "position": 4,
                "name": "technical_report_prov_export",
                "sha256": export_payload_sha256,
                "derived_from": ["prov_hash_basis"],
            },
        ],
    }
    receipt_core["hash_chain_complete"] = all(
        bool(item.get("sha256")) for item in receipt_core["hash_chain"]
    )
    receipt_sha256 = str(payload_sha256(receipt_core))
    return {
        **receipt_core,
        "receipt_sha256": receipt_sha256,
        **prov_export_receipt_signature(receipt_sha256, settings_provider=settings_provider),
    }


def frozen_prov_export_payload(
    prov_export: dict[str, Any],
    *,
    artifact_id: UUID,
    task_id: UUID,
    created_at: Any,
    storage_path: str | None,
    settings_provider: Callable[[], Any],
) -> dict[str, Any]:
    frozen_payload = _json_payload(prov_export)
    export_payload_sha256 = payload_sha256(prov_export)
    prov_hash_basis_sha256 = (prov_export.get("prov_integrity") or {}).get("prov_sha256")
    frozen_payload["frozen_export"] = {
        "schema_name": "technical_report_prov_export_freeze",
        "schema_version": "1.0",
        "artifact_id": str(artifact_id),
        "artifact_kind": TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        "task_id": str(task_id),
        "storage_path": storage_path,
        "frozen_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
        "freeze_policy": (
            "The first completed technical-report PROV export is persisted as an "
            "agent-task artifact and reused for subsequent reads."
        ),
        "export_payload_sha256": export_payload_sha256,
        "prov_hash_basis_sha256": prov_hash_basis_sha256,
        "export_receipt": prov_export_receipt(
            prov_export,
            artifact_id=artifact_id,
            task_id=task_id,
            created_at=created_at,
            storage_path=storage_path,
            export_payload_sha256=export_payload_sha256,
            prov_hash_basis_sha256=prov_hash_basis_sha256,
            settings_provider=settings_provider,
        ),
    }
    return _json_payload(frozen_payload)


def frozen_export_sha256(payload: dict[str, Any] | None) -> str | None:
    frozen_export = (payload or {}).get("frozen_export") or {}
    return frozen_export.get("export_payload_sha256")


def frozen_export_receipt(payload: dict[str, Any] | None) -> dict[str, Any]:
    frozen_export = (payload or {}).get("frozen_export") or {}
    receipt = frozen_export.get("export_receipt")
    return receipt if isinstance(receipt, dict) else {}


def receipt_hash_basis(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in receipt.items()
        if key
        not in {
            "receipt_sha256",
            "signature",
            "signature_algorithm",
            "signature_status",
            "signing_key_id",
        }
    }


def receipt_hash_chain_sha256(receipt: dict[str, Any], name: str) -> str | None:
    for item in receipt.get("hash_chain") or []:
        if item.get("name") == name:
            return item.get("sha256")
    return None


def prov_export_receipt_integrity(
    payload: dict[str, Any] | None,
    *,
    settings_provider: Callable[[], Any],
) -> dict[str, Any]:
    frozen_payload = _json_payload(payload or {})
    frozen_export = frozen_payload.get("frozen_export") or {}
    receipt = frozen_export_receipt(frozen_payload)
    hash_basis = receipt_hash_basis(receipt)
    expected_receipt_sha256 = str(payload_sha256(hash_basis)) if hash_basis else None
    stored_receipt_sha256 = receipt.get("receipt_sha256")
    receipt_hash_matches = bool(
        expected_receipt_sha256 and expected_receipt_sha256 == stored_receipt_sha256
    )

    signature_status = receipt.get("signature_status") or "missing"
    signature_algorithm_matches = (
        receipt.get("signature_algorithm") == PROV_EXPORT_RECEIPT_SIGNATURE_ALGORITHM
    )
    signature_present = bool(receipt.get("signature")) and signature_status == "signed"
    signature_valid = False
    signature_verification_status = signature_status
    if signature_status == "signed" and stored_receipt_sha256 and signature_present:
        settings = settings_provider()
        signing_key = getattr(settings, "audit_bundle_signing_key", None)
        if signing_key:
            signature_valid = hmac.compare_digest(
                str(receipt.get("signature")),
                _receipt_signature_value(stored_receipt_sha256, str(signing_key)),
            )
            signature_verification_status = "verified" if signature_valid else "mismatch"
        else:
            signature_verification_status = "signing_key_missing"

    hash_chain_values = [item.get("sha256") for item in receipt.get("hash_chain") or []]
    hash_chain_complete = bool(receipt.get("hash_chain_complete")) and all(hash_chain_values)
    export_payload_hash_matches = receipt_hash_chain_sha256(
        receipt, "technical_report_prov_export"
    ) == frozen_export.get("export_payload_sha256")
    prov_hash_basis_matches = receipt_hash_chain_sha256(
        receipt, "prov_hash_basis"
    ) == frozen_export.get("prov_hash_basis_sha256")
    checks = {
        "has_receipt": bool(receipt),
        "receipt_hash_matches": receipt_hash_matches,
        "expected_receipt_sha256": expected_receipt_sha256,
        "stored_receipt_sha256": stored_receipt_sha256,
        "hash_chain_complete": hash_chain_complete,
        "artifact_id_matches": receipt.get("artifact_id") == frozen_export.get("artifact_id"),
        "artifact_kind_matches": receipt.get("artifact_kind") == frozen_export.get("artifact_kind"),
        "task_id_matches": receipt.get("task_id") == frozen_export.get("task_id"),
        "storage_path_matches": receipt.get("storage_path") == frozen_export.get("storage_path"),
        "export_payload_hash_matches": export_payload_hash_matches,
        "prov_hash_basis_matches": prov_hash_basis_matches,
        "signature_status": signature_status,
        "signature_algorithm_matches": signature_algorithm_matches,
        "signature_present": signature_present,
        "signature_valid": signature_valid,
        "signature_verification_status": signature_verification_status,
    }
    checks["complete"] = all(
        bool(checks[key])
        for key in (
            "has_receipt",
            "receipt_hash_matches",
            "hash_chain_complete",
            "artifact_id_matches",
            "artifact_kind_matches",
            "task_id_matches",
            "storage_path_matches",
            "export_payload_hash_matches",
            "prov_hash_basis_matches",
            "signature_algorithm_matches",
            "signature_present",
            "signature_valid",
        )
    )
    return checks
