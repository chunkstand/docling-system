from __future__ import annotations

from typing import Any

from app.db.models import AuditBundleExport
from app.services.audit_bundle_release_payload_serialization import (
    SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
)
from app.services.audit_bundle_replay_alert_corpus import (
    payload_requires_claim_support_replay_alert_corpus_lineage as _requires_claim_support_lineage,
)
from app.services.audit_bundle_training_runs import (
    RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND,
)


def validation_error(code: str, message: str, path: str) -> dict[str, str]:
    return {"code": code, "message": message, "path": path}


def append_missing_key_errors(
    errors: list[dict[str, str]],
    payload: dict[str, Any],
    required_keys: tuple[str, ...],
    *,
    path: str,
) -> None:
    for key in required_keys:
        if key not in payload:
            errors.append(
                validation_error(
                    "required_key_missing",
                    f"Required key `{key}` is missing.",
                    f"{path}.{key}",
                )
            )


def append_required_list_error(
    errors: list[dict[str, str]],
    payload: dict[str, Any],
    key: str,
    *,
    path: str,
) -> None:
    if not isinstance(payload.get(key), list):
        errors.append(
            validation_error(
                "required_list_missing",
                f"Required list `{key}` is missing.",
                f"{path}.{key}",
            )
        )


def validate_bundle_payload_schema(
    *,
    row: AuditBundleExport,
    bundle: dict[str, Any],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if bundle.get("schema_name") != "audit_bundle_export":
        errors.append(
            validation_error(
                "invalid_bundle_schema",
                "Bundle schema_name must be audit_bundle_export.",
                "bundle.schema_name",
            )
        )
    export = bundle.get("bundle_export")
    payload = bundle.get("payload")
    if not isinstance(export, dict):
        errors.append(
            validation_error(
                "bundle_export_missing",
                "Bundle export metadata must be present.",
                "bundle.bundle_export",
            )
        )
        export = {}
    if not isinstance(payload, dict):
        errors.append(
            validation_error(
                "payload_missing",
                "Bundle payload must be present.",
                "bundle.payload",
            )
        )
        payload = {}
    for key in ("bundle_id", "bundle_kind", "source_table", "source_id", "payload_sha256"):
        if export.get(key) is None:
            errors.append(
                validation_error(
                    "bundle_export_field_missing",
                    f"Bundle export field `{key}` is missing.",
                    f"bundle.bundle_export.{key}",
                )
            )
    if export.get("bundle_id") != str(row.id):
        errors.append(
            validation_error(
                "bundle_id_mismatch",
                "Bundle export id does not match the database row.",
                "bundle.bundle_export.bundle_id",
            )
        )
    if export.get("bundle_kind") != row.bundle_kind:
        errors.append(
            validation_error(
                "bundle_kind_mismatch",
                "Bundle export kind does not match the database row.",
                "bundle.bundle_export.bundle_kind",
            )
        )
    if row.bundle_kind == SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND:
        if payload.get("schema_name") != "search_harness_release_audit_payload":
            errors.append(
                validation_error(
                    "invalid_release_payload_schema",
                    "Release audit payload schema_name is invalid.",
                    "bundle.payload.schema_name",
                )
            )
        release_payload_schema_version = payload.get("schema_version")
        requires_reranker_artifacts = (
            release_payload_schema_version != "1.0" or "retrieval_reranker_artifacts" in payload
        )
        requires_training_corpus_lineage = (
            release_payload_schema_version != "1.0"
            or "training_audit_bundle_corpus_lineage_complete" in (payload.get("integrity") or {})
        )
        required_keys = [
            "release",
            "evaluation",
            "evaluation_sources",
            "replay_runs",
            "retrieval_learning_candidates",
            "retrieval_training_runs",
            "retrieval_training_audit_bundles",
            "retrieval_training_audit_bundle_validation_receipts",
            "semantic_governance_events",
            "semantic_governance_policy",
            "audit_checklist",
            "integrity",
            "prov",
        ]
        required_list_keys = [
            "evaluation_sources",
            "replay_runs",
            "retrieval_learning_candidates",
            "retrieval_training_runs",
            "retrieval_training_audit_bundles",
            "retrieval_training_audit_bundle_validation_receipts",
            "semantic_governance_events",
        ]
        if requires_reranker_artifacts:
            required_keys.append("retrieval_reranker_artifacts")
            required_list_keys.append("retrieval_reranker_artifacts")
        append_missing_key_errors(
            errors,
            payload,
            tuple(required_keys),
            path="bundle.payload",
        )
        for key in required_list_keys:
            append_required_list_error(errors, payload, key, path="bundle.payload")
        audit_checklist = payload.get("audit_checklist") or {}
        integrity = payload.get("integrity") or {}
        if audit_checklist.get("complete") is not True:
            errors.append(
                validation_error(
                    "audit_checklist_incomplete",
                    "Release audit checklist is not complete.",
                    "bundle.payload.audit_checklist.complete",
                )
            )
        if integrity.get("training_audit_bundle_hashes_match_training_runs") is not True:
            errors.append(
                validation_error(
                    "training_bundle_hash_mismatch",
                    "Training audit bundle hashes must match linked training runs.",
                    "bundle.payload.integrity.training_audit_bundle_hashes_match_training_runs",
                )
            )
        if (
            requires_training_corpus_lineage
            and integrity.get("training_audit_bundle_corpus_lineage_complete") is not True
        ):
            errors.append(
                validation_error(
                    "training_bundle_corpus_lineage_incomplete",
                    (
                        "Training audit bundles sourced from the replay-alert corpus "
                        "must still match current governed corpus lineage."
                    ),
                    "bundle.payload.integrity.training_audit_bundle_corpus_lineage_complete",
                )
            )
        if (
            requires_reranker_artifacts
            and integrity.get("reranker_artifact_hashes_match") is not True
        ):
            errors.append(
                validation_error(
                    "reranker_artifact_hash_mismatch",
                    "Reranker artifact hashes must match their frozen payloads.",
                    "bundle.payload.integrity.reranker_artifact_hashes_match",
                )
            )
        if (
            requires_reranker_artifacts
            and integrity.get("reranker_artifact_change_impacts_complete") is not True
        ):
            errors.append(
                validation_error(
                    "reranker_artifact_change_impact_incomplete",
                    "Reranker artifact change-impact reports must be complete.",
                    "bundle.payload.integrity.reranker_artifact_change_impacts_complete",
                )
            )
    elif row.bundle_kind == RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND:
        if payload.get("schema_name") != "retrieval_training_run_audit_payload":
            errors.append(
                validation_error(
                    "invalid_training_payload_schema",
                    "Retrieval training audit payload schema_name is invalid.",
                    "bundle.payload.schema_name",
                )
            )
        training_payload_schema_version = payload.get("schema_version")
        requires_corpus_lineage = (
            training_payload_schema_version not in {None, "1.0"}
            or "claim_support_replay_alert_corpus_integrity" in payload
            or _requires_claim_support_lineage(payload)
        )
        required_keys = [
            "retrieval_training_run",
            "retrieval_judgment_set",
            "retrieval_judgments",
            "retrieval_hard_negatives",
            "source_payload_hashes",
            "semantic_governance_events",
            "audit_checklist",
            "integrity",
            "prov",
        ]
        required_list_keys = [
            "retrieval_judgments",
            "retrieval_hard_negatives",
            "source_payload_hashes",
            "semantic_governance_events",
        ]
        if requires_corpus_lineage:
            required_keys.extend(
                [
                    "claim_support_replay_alert_corpus_source_references",
                    "claim_support_replay_alert_corpus_snapshots",
                    "claim_support_replay_alert_corpus_rows",
                    "claim_support_replay_alert_promotion_artifacts",
                    "claim_support_replay_alert_promotion_events",
                    "claim_support_replay_alert_escalation_events",
                    "claim_support_replay_alert_snapshot_governance_artifacts",
                    "claim_support_replay_alert_snapshot_governance_events",
                    "claim_support_replay_alert_corpus_integrity",
                ]
            )
            required_list_keys.extend(
                [
                    "claim_support_replay_alert_corpus_source_references",
                    "claim_support_replay_alert_corpus_snapshots",
                    "claim_support_replay_alert_corpus_rows",
                    "claim_support_replay_alert_promotion_artifacts",
                    "claim_support_replay_alert_promotion_events",
                    "claim_support_replay_alert_escalation_events",
                    "claim_support_replay_alert_snapshot_governance_artifacts",
                    "claim_support_replay_alert_snapshot_governance_events",
                ]
            )
        append_missing_key_errors(
            errors,
            payload,
            tuple(required_keys),
            path="bundle.payload",
        )
        for key in required_list_keys:
            append_required_list_error(errors, payload, key, path="bundle.payload")
        audit_checklist = payload.get("audit_checklist") or {}
        integrity = payload.get("integrity") or {}
        corpus_integrity = payload.get("claim_support_replay_alert_corpus_integrity") or {}
        if audit_checklist.get("complete") is not True:
            errors.append(
                validation_error(
                    "audit_checklist_incomplete",
                    "Training audit checklist is not complete.",
                    "bundle.payload.audit_checklist.complete",
                )
            )
        if integrity.get("training_dataset_hash_matches") is not True:
            errors.append(
                validation_error(
                    "training_dataset_hash_mismatch",
                    "Training dataset hash must match the canonical payload.",
                    "bundle.payload.integrity.training_dataset_hash_matches",
                )
            )
        if (
            requires_corpus_lineage
            and corpus_integrity.get("source_reference_count", 0)
            and corpus_integrity.get("complete") is not True
        ):
            errors.append(
                validation_error(
                    "claim_support_replay_alert_corpus_lineage_incomplete",
                    "Claim-support replay-alert corpus lineage must be complete.",
                    "bundle.payload.claim_support_replay_alert_corpus_integrity.complete",
                )
            )
    else:
        errors.append(
            validation_error(
                "unsupported_bundle_kind",
                "Audit bundle kind is not supported by the validation profile.",
                "bundle.bundle_export.bundle_kind",
            )
        )
    return errors


def validate_bundle_source_integrity(
    *,
    row: AuditBundleExport,
    bundle: dict[str, Any],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    export = bundle.get("bundle_export") or {}
    payload = bundle.get("payload") or {}
    source = payload.get("source") or {}
    expected = {
        "bundle_kind": row.bundle_kind,
        "source_table": row.source_table,
        "source_id": str(row.source_id),
    }
    for key, expected_value in expected.items():
        if export.get(key) != expected_value:
            errors.append(
                validation_error(
                    "bundle_export_source_mismatch",
                    f"Bundle export `{key}` does not match the database row.",
                    f"bundle.bundle_export.{key}",
                )
            )
    if source.get("source_table") != row.source_table:
        errors.append(
            validation_error(
                "payload_source_table_mismatch",
                "Payload source_table does not match the database row.",
                "bundle.payload.source.source_table",
            )
        )
    if source.get("source_id") != str(row.source_id):
        errors.append(
            validation_error(
                "payload_source_id_mismatch",
                "Payload source_id does not match the database row.",
                "bundle.payload.source.source_id",
            )
        )
    if row.bundle_kind == SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND:
        if row.search_harness_release_id != row.source_id or row.retrieval_training_run_id:
            errors.append(
                validation_error(
                    "release_source_fk_mismatch",
                    "Release bundle source fields do not match release foreign keys.",
                    "audit_bundle_exports.search_harness_release_id",
                )
            )
    if row.bundle_kind == RETRIEVAL_TRAINING_RUN_AUDIT_BUNDLE_KIND:
        if row.retrieval_training_run_id != row.source_id:
            errors.append(
                validation_error(
                    "training_source_fk_mismatch",
                    "Training bundle source fields do not match training run foreign keys.",
                    "audit_bundle_exports.retrieval_training_run_id",
                )
            )
        training_run = payload.get("retrieval_training_run") or {}
        if training_run.get("retrieval_training_run_id") != str(row.source_id):
            errors.append(
                validation_error(
                    "training_payload_id_mismatch",
                    "Training payload id does not match the bundle source id.",
                    "bundle.payload.retrieval_training_run.retrieval_training_run_id",
                )
            )
    return errors


def semantic_governance_chain_checks(events: list[dict[str, Any]]) -> dict[str, Any]:
    event_ids = {str(row.get("event_id")) for row in events if row.get("event_id")}
    event_hashes_by_id = {
        str(row.get("event_id")): row.get("event_hash") for row in events if row.get("event_id")
    }
    external_previous_event_count = 0
    hash_link_mismatch_count = 0
    for row in events:
        previous_event_id = row.get("previous_event_id")
        if not previous_event_id:
            continue
        if previous_event_id not in event_ids:
            external_previous_event_count += 1
            continue
        if row.get("previous_event_hash") != event_hashes_by_id.get(previous_event_id):
            hash_link_mismatch_count += 1
    return {
        "event_count": len(events),
        "external_previous_event_count": external_previous_event_count,
        "hash_link_mismatch_count": hash_link_mismatch_count,
        "hash_links_verified": (
            external_previous_event_count == 0 and hash_link_mismatch_count == 0
        ),
    }


def validate_release_semantic_governance_policy(
    payload: dict[str, Any],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    policy = payload.get("semantic_governance_policy")
    if not isinstance(policy, dict):
        return [
            validation_error(
                "semantic_governance_policy_missing",
                "Release audit payload must include a semantic governance policy profile.",
                "bundle.payload.semantic_governance_policy",
            )
        ]
    checks = policy.get("checks") or {}
    if policy.get("schema_name") != "search_harness_release_semantic_governance_policy":
        errors.append(
            validation_error(
                "invalid_semantic_governance_policy_schema",
                "Release semantic governance policy schema_name is invalid.",
                "bundle.payload.semantic_governance_policy.schema_name",
            )
        )
    if checks.get("has_release_governance_event") is not True:
        errors.append(
            validation_error(
                "release_governance_event_missing",
                "Release semantic governance policy must reference a release governance event.",
                "bundle.payload.semantic_governance_policy.checks.has_release_governance_event",
            )
        )
    events = payload.get("semantic_governance_events") or []
    chain_checks = semantic_governance_chain_checks(events if isinstance(events, list) else [])
    if checks.get("hash_links_verified") is not True or not chain_checks["hash_links_verified"]:
        errors.append(
            validation_error(
                "semantic_governance_chain_broken",
                "Semantic governance event previous-hash links must be closed and verified.",
                "bundle.payload.semantic_governance_policy.checks.hash_links_verified",
            )
        )
    if policy.get("semantic_coverage_claimed") is True:
        if checks.get("has_ontology_snapshot_reference") is not True:
            errors.append(
                validation_error(
                    "semantic_ontology_snapshot_reference_missing",
                    "Semantic coverage claims require an ontology snapshot reference.",
                    (
                        "bundle.payload.semantic_governance_policy.checks."
                        "has_ontology_snapshot_reference"
                    ),
                )
            )
        if checks.get("has_semantic_graph_snapshot_reference") is not True:
            errors.append(
                validation_error(
                    "semantic_graph_snapshot_reference_missing",
                    "Semantic coverage claims require a semantic graph snapshot reference.",
                    (
                        "bundle.payload.semantic_governance_policy.checks."
                        "has_semantic_graph_snapshot_reference"
                    ),
                )
            )
    if policy.get("complete") is not True or checks.get("complete") is not True:
        errors.append(
            validation_error(
                "semantic_governance_policy_incomplete",
                "Release semantic governance policy is incomplete.",
                "bundle.payload.semantic_governance_policy.complete",
            )
        )
    return errors
