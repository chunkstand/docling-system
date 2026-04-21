from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import SemanticOntologySourceKind
from app.services.semantic_orchestration import (
    draft_semantic_registry_update,
    draft_semantic_registry_update_from_bootstrap_report,
    semantic_registry_apply_metrics,
    semantic_registry_verification_metrics,
    semantic_registry_verification_summary,
)
from app.services.semantic_registry import (
    ensure_workspace_semantic_registry,
    get_active_semantic_ontology_snapshot,
    persist_semantic_ontology_snapshot,
)
from app.services.semantics import preview_semantic_registry_update_for_document


def _snapshot_payload(snapshot) -> dict[str, Any]:
    payload = snapshot.payload_json or {}
    return {
        "snapshot_id": snapshot.id,
        "ontology_name": snapshot.ontology_name,
        "ontology_version": snapshot.ontology_version,
        "upper_ontology_version": snapshot.upper_ontology_version,
        "sha256": snapshot.sha256,
        "source_kind": snapshot.source_kind,
        "source_task_id": snapshot.source_task_id,
        "source_task_type": snapshot.source_task_type,
        "concept_count": len(payload.get("concepts") or []),
        "category_count": len(payload.get("categories") or []),
        "relation_count": len(payload.get("relations") or []),
        "relation_keys": sorted(
            str(item.get("relation_key") or "").strip()
            for item in (payload.get("relations") or [])
            if str(item.get("relation_key") or "").strip()
        ),
        "created_at": snapshot.created_at,
        "activated_at": snapshot.activated_at,
    }


def _ontology_snapshot_success_metrics(snapshot_payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "metric_key": "portable_bootstrap",
            "stakeholder": "Milestone",
            "passed": bool(snapshot_payload.get("snapshot_id"))
            and bool(snapshot_payload.get("upper_ontology_version")),
            "summary": "The workspace can initialize ontology state from a portable seed.",
            "details": {
                "ontology_version": snapshot_payload.get("ontology_version"),
                "upper_ontology_version": snapshot_payload.get("upper_ontology_version"),
            },
        },
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": bool(snapshot_payload.get("sha256"))
            and bool(snapshot_payload.get("ontology_version")),
            "summary": "The active ontology snapshot is explicitly versioned and hash-stamped.",
            "details": {
                "ontology_version": snapshot_payload.get("ontology_version"),
                "sha256": snapshot_payload.get("sha256"),
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": bool(snapshot_payload.get("snapshot_id"))
            and "relation_keys" in snapshot_payload,
            "summary": "Ontology state is available as typed snapshot context for agents.",
            "details": {
                "relation_count": snapshot_payload.get("relation_count"),
                "concept_count": snapshot_payload.get("concept_count"),
            },
        },
        {
            "metric_key": "owned_context",
            "stakeholder": "Jones",
            "passed": bool(snapshot_payload.get("snapshot_id")),
            "summary": (
                "Ontology state is stored in the workspace database, not in repo-local folklore."
            ),
            "details": {
                "snapshot_id": str(snapshot_payload.get("snapshot_id") or ""),
            },
        },
        {
            "metric_key": "explicit_control_surface",
            "stakeholder": "Ronacher",
            "passed": snapshot_payload.get("source_kind")
            in {
                SemanticOntologySourceKind.UPPER_SEED.value,
                SemanticOntologySourceKind.ONTOLOGY_EXTENSION_APPLY.value,
            },
            "summary": "Ontology activation remains bounded to explicit snapshot states.",
            "details": {
                "source_kind": snapshot_payload.get("source_kind"),
            },
        },
    ]


def initialize_workspace_ontology(session: Session) -> dict[str, Any]:
    ensure_workspace_semantic_registry(session)
    snapshot = get_active_semantic_ontology_snapshot(session)
    payload = _snapshot_payload(snapshot)
    return {
        "snapshot": payload,
        "success_metrics": _ontology_snapshot_success_metrics(payload),
    }


def get_active_ontology_snapshot_payload(session: Session) -> dict[str, Any]:
    snapshot = get_active_semantic_ontology_snapshot(session)
    payload = _snapshot_payload(snapshot)
    return {
        "snapshot": payload,
        "success_metrics": _ontology_snapshot_success_metrics(payload),
    }


def draft_ontology_extension(
    session: Session,
    gap_report: dict[str, Any],
    *,
    source_task_id: UUID,
    source_task_type: str | None,
    proposed_ontology_version: str | None,
    rationale: str | None,
    candidate_ids: list[str] | None = None,
) -> dict[str, Any]:
    base_snapshot = get_active_semantic_ontology_snapshot(session)
    draft = draft_semantic_registry_update(
        session,
        gap_report,
        source_task_id=source_task_id,
        source_task_type=source_task_type,
        proposed_registry_version=proposed_ontology_version,
        rationale=rationale,
        candidate_ids=candidate_ids,
    )
    return {
        "base_snapshot_id": base_snapshot.id,
        "base_ontology_version": base_snapshot.ontology_version,
        "proposed_ontology_version": draft["proposed_registry_version"],
        "upper_ontology_version": base_snapshot.upper_ontology_version,
        "source_task_id": source_task_id,
        "source_task_type": source_task_type,
        "rationale": draft.get("rationale"),
        "document_ids": draft.get("document_ids") or [],
        "operations": draft.get("operations") or [],
        "effective_ontology": draft.get("effective_registry") or {},
        "success_metrics": draft.get("success_metrics") or [],
    }


def draft_ontology_extension_from_bootstrap_report(
    session: Session,
    bootstrap_report: dict[str, Any],
    *,
    source_task_id: UUID,
    source_task_type: str | None,
    proposed_ontology_version: str | None,
    rationale: str | None,
    candidate_ids: list[str] | None = None,
) -> dict[str, Any]:
    base_snapshot = get_active_semantic_ontology_snapshot(session)
    draft = draft_semantic_registry_update_from_bootstrap_report(
        session,
        bootstrap_report,
        source_task_id=source_task_id,
        source_task_type=source_task_type,
        proposed_registry_version=proposed_ontology_version,
        rationale=rationale,
        candidate_ids=candidate_ids,
    )
    return {
        "base_snapshot_id": base_snapshot.id,
        "base_ontology_version": base_snapshot.ontology_version,
        "proposed_ontology_version": draft["proposed_registry_version"],
        "upper_ontology_version": base_snapshot.upper_ontology_version,
        "source_task_id": source_task_id,
        "source_task_type": source_task_type,
        "rationale": draft.get("rationale"),
        "document_ids": draft.get("document_ids") or [],
        "operations": draft.get("operations") or [],
        "effective_ontology": draft.get("effective_registry") or {},
        "success_metrics": draft.get("success_metrics") or [],
    }


def verify_draft_ontology_extension(
    session: Session,
    draft: dict[str, Any],
    *,
    document_ids: list[UUID],
    max_regressed_document_count: int,
    max_failed_expectation_increase: int,
    min_improved_document_count: int,
) -> tuple[
    list[dict[str, Any]], dict[str, Any], dict[str, Any], list[str], str, list[dict[str, Any]]
]:
    resolved_document_ids = document_ids or list(draft.get("document_ids") or [])
    if not resolved_document_ids:
        raise ValueError("Ontology extension verification requires at least one document.")
    document_deltas = [
        preview_semantic_registry_update_for_document(
            session,
            document_id,
            draft["effective_ontology"],
        )
        for document_id in resolved_document_ids
    ]
    summary = semantic_registry_verification_summary(document_deltas)
    reasons: list[str] = []
    if summary["regressed_document_count"] > max_regressed_document_count:
        reasons.append("Draft regresses more documents than the allowed threshold.")
    if summary["regressed_expectation_count"] > max_failed_expectation_increase:
        reasons.append("Draft increases failed semantic expectations beyond the allowed threshold.")
    if summary["improved_document_count"] < min_improved_document_count:
        reasons.append("Draft does not improve enough documents to justify publication.")
    outcome = "passed" if not reasons else "failed"
    metrics = {
        "document_count": summary["document_count"],
        "improved_document_count": summary["improved_document_count"],
        "regressed_document_count": summary["regressed_document_count"],
        "total_improved_count": summary["improved_expectation_count"],
        "total_regressed_count": summary["regressed_expectation_count"],
        "total_added_concept_count": summary["added_concept_count"],
        "total_removed_concept_count": summary["removed_concept_count"],
    }
    success_metrics = semantic_registry_verification_metrics(
        draft={
            "proposed_registry_version": draft["proposed_ontology_version"],
            "operations": draft.get("operations") or [],
        },
        document_deltas=document_deltas,
    )
    return document_deltas, summary, metrics, reasons, outcome, success_metrics


def apply_ontology_extension(
    session: Session,
    draft: dict[str, Any],
    *,
    source_task_id: UUID,
    source_task_type: str,
    reason: str | None,
) -> dict[str, Any]:
    base_snapshot_id = UUID(str(draft["base_snapshot_id"]))
    snapshot = persist_semantic_ontology_snapshot(
        session,
        draft["effective_ontology"],
        source_kind=SemanticOntologySourceKind.ONTOLOGY_EXTENSION_APPLY.value,
        source_task_id=source_task_id,
        source_task_type=source_task_type,
        parent_snapshot_id=base_snapshot_id,
        activate=True,
    )
    session.commit()
    return {
        "applied_snapshot_id": snapshot.id,
        "applied_ontology_version": snapshot.ontology_version,
        "applied_ontology_sha256": snapshot.sha256,
        "upper_ontology_version": snapshot.upper_ontology_version,
        "reason": reason,
        "applied_operations": draft.get("operations") or [],
        "success_metrics": semantic_registry_apply_metrics(
            applied_registry_version=snapshot.ontology_version,
            applied_operations=draft.get("operations") or [],
            verification_outcome="passed",
        ),
    }
