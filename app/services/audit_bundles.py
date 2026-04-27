from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.config import get_settings
from app.core.time import utcnow
from app.db.models import (
    AuditBundleExport,
    SearchHarnessEvaluation,
    SearchHarnessEvaluationSource,
    SearchHarnessRelease,
    SearchReplayRun,
)
from app.schemas.search import (
    AuditBundleExportResponse,
    AuditBundleExportSummaryResponse,
    SearchHarnessReleaseAuditBundleRequest,
)
from app.services.storage import StorageService

SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND = "search_harness_release_provenance"
SEARCH_HARNESS_RELEASE_SOURCE_TABLE = "search_harness_releases"
SIGNATURE_ALGORITHM = "hmac-sha256"


def _payload_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _file_sha256(path: Path | None) -> str | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _audit_bundle_not_found(bundle_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "audit_bundle_export_not_found",
        "Audit bundle export not found.",
        bundle_id=str(bundle_id),
    )


def _release_not_found(release_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "search_harness_release_not_found",
        "Search harness release gate not found.",
        release_id=str(release_id),
    )


def _signing_key() -> tuple[str, str]:
    settings = get_settings()
    signing_key = getattr(settings, "audit_bundle_signing_key", None)
    if not signing_key:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "audit_bundle_signing_key_missing",
            "DOCLING_SYSTEM_AUDIT_BUNDLE_SIGNING_KEY is required to export signed audit bundles.",
        )
    key_id = getattr(settings, "audit_bundle_signing_key_id", None) or "local"
    return str(signing_key), str(key_id)


def _signature(payload_sha256: str, signing_key: str) -> str:
    return hmac.new(
        signing_key.encode("utf-8"),
        payload_sha256.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def _release_payload(row: SearchHarnessRelease) -> dict[str, Any]:
    return {
        "release_id": str(row.id),
        "evaluation_id": str(row.search_harness_evaluation_id),
        "outcome": row.outcome,
        "baseline_harness_name": row.baseline_harness_name,
        "candidate_harness_name": row.candidate_harness_name,
        "limit": row.limit,
        "source_types": row.source_types_json or [],
        "thresholds": row.thresholds_json or {},
        "metrics": row.metrics_json or {},
        "reasons": row.reasons_json or [],
        "details": row.details_json or {},
        "evaluation_snapshot": row.evaluation_snapshot_json or {},
        "release_package_sha256": row.release_package_sha256,
        "requested_by": row.requested_by,
        "review_note": row.review_note,
        "created_at": row.created_at.isoformat(),
    }


def _evaluation_payload(row: SearchHarnessEvaluation | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "evaluation_id": str(row.id),
        "status": row.status,
        "baseline_harness_name": row.baseline_harness_name,
        "candidate_harness_name": row.candidate_harness_name,
        "limit": row.limit,
        "source_types": row.source_types_json or [],
        "harness_overrides": row.harness_overrides_json or {},
        "total_shared_query_count": row.total_shared_query_count,
        "total_improved_count": row.total_improved_count,
        "total_regressed_count": row.total_regressed_count,
        "total_unchanged_count": row.total_unchanged_count,
        "summary": row.summary_json or {},
        "error_message": row.error_message,
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _source_payload(row: SearchHarnessEvaluationSource) -> dict[str, Any]:
    return {
        "source_id": str(row.id),
        "source_index": row.source_index,
        "source_type": row.source_type,
        "baseline_replay_run_id": str(row.baseline_replay_run_id),
        "candidate_replay_run_id": str(row.candidate_replay_run_id),
        "baseline_status": row.baseline_status,
        "candidate_status": row.candidate_status,
        "shared_query_count": row.shared_query_count,
        "improved_count": row.improved_count,
        "regressed_count": row.regressed_count,
        "unchanged_count": row.unchanged_count,
        "acceptance_checks": row.acceptance_checks_json or {},
        "baseline_mrr": row.baseline_mrr,
        "candidate_mrr": row.candidate_mrr,
        "baseline_zero_result_count": row.baseline_zero_result_count,
        "candidate_zero_result_count": row.candidate_zero_result_count,
        "baseline_foreign_top_result_count": row.baseline_foreign_top_result_count,
        "candidate_foreign_top_result_count": row.candidate_foreign_top_result_count,
        "created_at": row.created_at.isoformat(),
    }


def _replay_payload(row: SearchReplayRun) -> dict[str, Any]:
    return {
        "replay_run_id": str(row.id),
        "source_type": row.source_type,
        "status": row.status,
        "harness_name": row.harness_name,
        "reranker_name": row.reranker_name,
        "reranker_version": row.reranker_version,
        "retrieval_profile_name": row.retrieval_profile_name,
        "harness_config": row.harness_config_json or {},
        "query_count": row.query_count,
        "passed_count": row.passed_count,
        "failed_count": row.failed_count,
        "zero_result_count": row.zero_result_count,
        "table_hit_count": row.table_hit_count,
        "top_result_changes": row.top_result_changes,
        "max_rank_shift": row.max_rank_shift,
        "summary": row.summary_json or {},
        "error_message": row.error_message,
        "created_at": row.created_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _release_package_sha256(row: SearchHarnessRelease) -> str:
    package = {
        "schema_name": "search_harness_release_package",
        "schema_version": "1.0",
        "evaluation": row.evaluation_snapshot_json or {},
        "gate": {
            "outcome": row.outcome,
            "metrics": row.metrics_json or {},
            "reasons": row.reasons_json or [],
            "details": row.details_json or {},
        },
        "thresholds": row.thresholds_json or {},
    }
    return _payload_sha256(package)


def _prov_graph(
    *,
    release: SearchHarnessRelease,
    evaluation: SearchHarnessEvaluation | None,
    sources: list[SearchHarnessEvaluationSource],
    replay_runs: list[SearchReplayRun],
    bundle_id: UUID,
    created_by: str | None,
) -> dict[str, Any]:
    release_entity = f"docling:search_harness_release:{release.id}"
    evaluation_entity = f"docling:search_harness_evaluation:{release.search_harness_evaluation_id}"
    activity = f"docling:activity:search_harness_release_gate:{release.id}"
    exporter_activity = f"docling:activity:audit_bundle_export:{bundle_id}"
    agent = f"docling:agent:{created_by or release.requested_by or 'system'}"

    entities: dict[str, dict[str, Any]] = {
        release_entity: {
            "prov:type": "docling:SearchHarnessRelease",
            "docling:outcome": release.outcome,
            "docling:releasePackageSha256": release.release_package_sha256,
        },
        evaluation_entity: {
            "prov:type": "docling:SearchHarnessEvaluation",
            "docling:status": evaluation.status if evaluation else None,
        },
        f"docling:thresholds:{release.id}": {
            "prov:type": "docling:ReleaseThresholds",
            "docling:sha256": _payload_sha256(release.thresholds_json or {}),
        },
    }
    for source in sources:
        entities[f"docling:search_harness_evaluation_source:{source.id}"] = {
            "prov:type": "docling:SearchHarnessEvaluationSource",
            "docling:sourceType": source.source_type,
        }
    for replay_run in replay_runs:
        entities[f"docling:search_replay_run:{replay_run.id}"] = {
            "prov:type": "docling:SearchReplayRun",
            "docling:status": replay_run.status,
            "docling:harnessName": replay_run.harness_name,
        }

    used = [
        {"activity": activity, "entity": evaluation_entity},
        {"activity": activity, "entity": f"docling:thresholds:{release.id}"},
    ]
    was_derived_from = [
        {"generatedEntity": release_entity, "usedEntity": evaluation_entity},
    ]
    for source in sources:
        source_entity = f"docling:search_harness_evaluation_source:{source.id}"
        used.append({"activity": activity, "entity": source_entity})
        was_derived_from.append({"generatedEntity": release_entity, "usedEntity": source_entity})
        was_derived_from.append(
            {
                "generatedEntity": source_entity,
                "usedEntity": f"docling:search_replay_run:{source.baseline_replay_run_id}",
            }
        )
        was_derived_from.append(
            {
                "generatedEntity": source_entity,
                "usedEntity": f"docling:search_replay_run:{source.candidate_replay_run_id}",
            }
        )

    return {
        "prefix": {
            "prov": "http://www.w3.org/ns/prov#",
            "docling": "https://local.docling-system/prov#",
        },
        "entity": entities,
        "activity": {
            activity: {
                "prov:type": "docling:SearchHarnessReleaseGate",
                "prov:endedAtTime": release.created_at.isoformat(),
            },
            exporter_activity: {
                "prov:type": "docling:AuditBundleExport",
            },
        },
        "agent": {
            agent: {
                "prov:type": "prov:Person" if created_by else "prov:SoftwareAgent",
                "docling:identifier": created_by or release.requested_by or "system",
            }
        },
        "wasGeneratedBy": [
            {"entity": release_entity, "activity": activity},
            {
                "entity": f"docling:audit_bundle_export:{bundle_id}",
                "activity": exporter_activity,
            },
        ],
        "used": used,
        "wasDerivedFrom": was_derived_from,
        "wasAssociatedWith": [
            {"activity": activity, "agent": agent},
            {"activity": exporter_activity, "agent": agent},
        ],
    }


def _build_search_harness_release_payload(
    session: Session,
    *,
    release: SearchHarnessRelease,
    bundle_id: UUID,
    created_by: str | None,
    created_at,
) -> dict[str, Any]:
    evaluation = session.get(SearchHarnessEvaluation, release.search_harness_evaluation_id)
    sources = (
        session.execute(
            select(SearchHarnessEvaluationSource)
            .where(
                SearchHarnessEvaluationSource.search_harness_evaluation_id
                == release.search_harness_evaluation_id
            )
            .order_by(SearchHarnessEvaluationSource.source_index.asc())
        )
        .scalars()
        .all()
    )
    replay_run_ids: list[UUID] = []
    for source in sources:
        replay_run_ids.extend([source.baseline_replay_run_id, source.candidate_replay_run_id])
    replay_runs = (
        session.execute(select(SearchReplayRun).where(SearchReplayRun.id.in_(replay_run_ids)))
        .scalars()
        .all()
        if replay_run_ids
        else []
    )
    replay_runs_by_id = {row.id: row for row in replay_runs}
    ordered_replay_runs = [
        replay_runs_by_id[replay_run_id]
        for replay_run_id in replay_run_ids
        if replay_run_id in replay_runs_by_id
    ]
    release_package_hash_matches = (
        _release_package_sha256(release) == release.release_package_sha256
    )
    all_replay_runs_present = len(ordered_replay_runs) == len(set(replay_run_ids))
    all_replay_runs_completed = bool(ordered_replay_runs) and all(
        row.status == "completed" for row in ordered_replay_runs
    )
    audit_checklist = {
        "has_release_record": True,
        "has_evaluation_record": evaluation is not None,
        "has_evaluation_snapshot": bool(release.evaluation_snapshot_json),
        "release_package_hash_matches": release_package_hash_matches,
        "has_replay_sources": bool(sources),
        "all_replay_runs_present": all_replay_runs_present,
        "all_replay_runs_completed": all_replay_runs_completed,
        "has_prov_graph": True,
    }
    audit_checklist["complete"] = all(audit_checklist.values())
    return {
        "schema_name": "search_harness_release_audit_payload",
        "schema_version": "1.0",
        "bundle_id": str(bundle_id),
        "bundle_kind": SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
        "created_at": created_at.isoformat(),
        "created_by": created_by,
        "source": {
            "source_table": SEARCH_HARNESS_RELEASE_SOURCE_TABLE,
            "source_id": str(release.id),
        },
        "release": _release_payload(release),
        "evaluation": _evaluation_payload(evaluation),
        "evaluation_sources": [_source_payload(row) for row in sources],
        "replay_runs": [_replay_payload(row) for row in ordered_replay_runs],
        "audit_checklist": audit_checklist,
        "integrity": {
            "release_package_hash_matches": release_package_hash_matches,
            "expected_release_package_sha256": _release_package_sha256(release),
            "stored_release_package_sha256": release.release_package_sha256,
            "replay_run_count": len(ordered_replay_runs),
            "expected_replay_run_count": len(set(replay_run_ids)),
        },
        "prov": _prov_graph(
            release=release,
            evaluation=evaluation,
            sources=sources,
            replay_runs=ordered_replay_runs,
            bundle_id=bundle_id,
            created_by=created_by,
        ),
    }


def _bundle_without_bundle_sha256(bundle: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(bundle, default=str, sort_keys=True))
    export = normalized.get("bundle_export") or {}
    export.pop("bundle_sha256", None)
    normalized["bundle_export"] = export
    return normalized


def _bundle_sha256(bundle: dict[str, Any]) -> str:
    return _payload_sha256(_bundle_without_bundle_sha256(bundle))


def _signed_bundle(
    *,
    bundle_id: UUID,
    payload: dict[str, Any],
    signing_key: str,
    signing_key_id: str,
) -> dict[str, Any]:
    payload_sha256 = _payload_sha256(payload)
    signature = _signature(payload_sha256, signing_key)
    bundle = {
        "schema_name": "audit_bundle_export",
        "schema_version": "1.0",
        "bundle_export": {
            "bundle_id": str(bundle_id),
            "bundle_kind": SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
            "source_table": SEARCH_HARNESS_RELEASE_SOURCE_TABLE,
            "source_id": payload["source"]["source_id"],
            "payload_sha256": payload_sha256,
            "signature": signature,
            "signature_algorithm": SIGNATURE_ALGORITHM,
            "signing_key_id": signing_key_id,
        },
        "payload": payload,
    }
    bundle["bundle_export"]["bundle_sha256"] = _bundle_sha256(bundle)
    return bundle


def _to_summary(row: AuditBundleExport) -> AuditBundleExportSummaryResponse:
    return AuditBundleExportSummaryResponse(
        bundle_id=row.id,
        bundle_kind=row.bundle_kind,
        source_table=row.source_table,
        source_id=row.source_id,
        payload_sha256=row.payload_sha256,
        bundle_sha256=row.bundle_sha256,
        signature=row.signature,
        signature_algorithm=row.signature_algorithm,
        signing_key_id=row.signing_key_id,
        created_by=row.created_by,
        export_status=row.export_status,
        created_at=row.created_at,
    )


def _verify_bundle(
    row: AuditBundleExport,
    bundle: dict[str, Any],
    storage_service: StorageService,
) -> dict:
    payload = bundle.get("payload") or {}
    export = bundle.get("bundle_export") or {}
    payload_sha256 = _payload_sha256(payload)
    bundle_sha256 = _bundle_sha256(bundle)
    path = storage_service.resolve_existing_path(row.storage_path)
    file_sha256 = _file_sha256(path)
    try:
        signing_key, _key_id = _signing_key()
        signature_valid = hmac.compare_digest(
            row.signature,
            _signature(row.payload_sha256, signing_key),
        )
        signature_verification_status = "verified" if signature_valid else "mismatch"
    except HTTPException:
        signature_valid = False
        signature_verification_status = "signing_key_missing"
    checks = {
        "payload_hash_matches_row": payload_sha256 == row.payload_sha256,
        "payload_hash_matches_bundle": payload_sha256 == export.get("payload_sha256"),
        "bundle_hash_matches_row": bundle_sha256 == row.bundle_sha256,
        "bundle_hash_matches_bundle": bundle_sha256 == export.get("bundle_sha256"),
        "signature_matches_row": row.signature == export.get("signature"),
        "signature_valid": signature_valid,
        "file_exists": path is not None,
        "file_sha256": file_sha256,
        "stored_payload_matches_file": bool(row.bundle_payload_json == bundle),
    }
    checks["complete"] = all(
        bool(checks[key])
        for key in (
            "payload_hash_matches_row",
            "payload_hash_matches_bundle",
            "bundle_hash_matches_row",
            "bundle_hash_matches_bundle",
            "signature_matches_row",
            "signature_valid",
            "file_exists",
            "stored_payload_matches_file",
        )
    )
    checks["signature_verification_status"] = signature_verification_status
    return checks


def _to_response(
    row: AuditBundleExport,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    path = storage_service.resolve_existing_path(row.storage_path)
    if path is not None:
        bundle = json.loads(path.read_text())
    else:
        bundle = row.bundle_payload_json or {}
    integrity = _verify_bundle(row, bundle, storage_service)
    return AuditBundleExportResponse(
        **_to_summary(row).model_dump(),
        bundle=bundle,
        integrity=integrity,
    )


def create_search_harness_release_audit_bundle(
    session: Session,
    release_id: UUID,
    payload: SearchHarnessReleaseAuditBundleRequest,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    release = session.get(SearchHarnessRelease, release_id)
    if release is None:
        raise _release_not_found(release_id)
    signing_key, signing_key_id = _signing_key()
    bundle_id = uuid.uuid4()
    created_at = utcnow()
    audit_payload = _build_search_harness_release_payload(
        session,
        release=release,
        bundle_id=bundle_id,
        created_by=payload.created_by,
        created_at=created_at,
    )
    bundle = _signed_bundle(
        bundle_id=bundle_id,
        payload=audit_payload,
        signing_key=signing_key,
        signing_key_id=signing_key_id,
    )
    bundle_path = storage_service.get_audit_bundle_json_path(
        SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
        bundle_id,
    )
    bundle_path.write_bytes(_canonical_json_bytes(bundle))
    integrity = {
        "payload_hash_matches_bundle": True,
        "bundle_hash_matches_bundle": True,
        "signature_valid": True,
        "file_exists": True,
        "stored_payload_matches_file": True,
        "complete": True,
    }
    row = AuditBundleExport(
        id=bundle_id,
        bundle_kind=SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
        source_table=SEARCH_HARNESS_RELEASE_SOURCE_TABLE,
        source_id=release.id,
        search_harness_release_id=release.id,
        storage_path=str(bundle_path),
        payload_sha256=bundle["bundle_export"]["payload_sha256"],
        bundle_sha256=bundle["bundle_export"]["bundle_sha256"],
        signature=bundle["bundle_export"]["signature"],
        signature_algorithm=bundle["bundle_export"]["signature_algorithm"],
        signing_key_id=bundle["bundle_export"]["signing_key_id"],
        bundle_payload_json=bundle,
        integrity_json=integrity,
        created_by=payload.created_by,
        export_status="completed",
        created_at=created_at,
    )
    session.add(row)
    session.flush()
    return _to_response(row, storage_service=storage_service)


def get_audit_bundle_export(
    session: Session,
    bundle_id: UUID,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    row = session.get(AuditBundleExport, bundle_id)
    if row is None:
        raise _audit_bundle_not_found(bundle_id)
    return _to_response(row, storage_service=storage_service)


def get_latest_search_harness_release_audit_bundle(
    session: Session,
    release_id: UUID,
    *,
    storage_service: StorageService,
) -> AuditBundleExportResponse:
    row = session.scalar(
        select(AuditBundleExport)
        .where(
            AuditBundleExport.search_harness_release_id == release_id,
            AuditBundleExport.bundle_kind == SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
        )
        .order_by(AuditBundleExport.created_at.desc())
    )
    if row is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "search_harness_release_audit_bundle_not_found",
            "Search harness release audit bundle not found.",
            release_id=str(release_id),
        )
    return _to_response(row, storage_service=storage_service)
