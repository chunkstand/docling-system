from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.semantic_governance_core as _semantic_governance_core
from app.db.public.agent_tasks import AgentTaskArtifact
from app.db.public.audit_and_evidence import (
    EvidenceManifest,
    TechnicalReportClaimRetrievalFeedback,
    TechnicalReportReleaseReadinessDbGate,
)
from app.db.public.retrieval import SearchHarnessRelease, SearchRequestRecord
from app.db.public.semantic_memory import (
    SemanticGovernanceEvent,
    SemanticGovernanceEventKind,
    SemanticGraphSnapshot,
    SemanticOntologySnapshot,
    WorkspaceSemanticGraphState,
    WorkspaceSemanticState,
)


def _active_semantic_basis(session: Session) -> dict[str, Any]:
    ontology_state = session.get(
        WorkspaceSemanticState, _semantic_governance_core.WORKSPACE_SEMANTIC_STATE_KEY
    )
    graph_state = session.get(
        WorkspaceSemanticGraphState, _semantic_governance_core.WORKSPACE_SEMANTIC_GRAPH_STATE_KEY
    )
    ontology_snapshot = (
        session.get(SemanticOntologySnapshot, ontology_state.active_ontology_snapshot_id)
        if ontology_state is not None and ontology_state.active_ontology_snapshot_id is not None
        else None
    )
    graph_snapshot = (
        session.get(SemanticGraphSnapshot, graph_state.active_graph_snapshot_id)
        if graph_state is not None and graph_state.active_graph_snapshot_id is not None
        else None
    )
    return {
        "workspace_key": _semantic_governance_core.WORKSPACE_SEMANTIC_STATE_KEY,
        "active_ontology_snapshot_id": (
            str(ontology_snapshot.id) if ontology_snapshot is not None else None
        ),
        "active_ontology_version": (
            ontology_snapshot.ontology_version if ontology_snapshot is not None else None
        ),
        "active_ontology_sha256": (
            ontology_snapshot.sha256 if ontology_snapshot is not None else None
        ),
        "active_semantic_graph_snapshot_id": (
            str(graph_snapshot.id) if graph_snapshot is not None else None
        ),
        "active_semantic_graph_version": (
            graph_snapshot.graph_version if graph_snapshot is not None else None
        ),
        "active_semantic_graph_sha256": (
            graph_snapshot.sha256 if graph_snapshot is not None else None
        ),
    }


def active_semantic_basis(session: Session) -> dict[str, Any]:
    return _active_semantic_basis(session)


def _search_requests_for_manifest(
    session: Session,
    manifest: EvidenceManifest | None,
) -> list[SearchRequestRecord]:
    search_request_ids = _semantic_governance_core._uuids(
        manifest.search_request_ids_json if manifest is not None else []
    )
    if not search_request_ids:
        return []
    return list(
        session.scalars(
            select(SearchRequestRecord)
            .where(SearchRequestRecord.id.in_(search_request_ids))
            .order_by(SearchRequestRecord.created_at.asc())
        )
    )


def _latest_passed_releases_by_harness(
    session: Session,
    harness_names: Iterable[str],
) -> dict[str, str]:
    releases: dict[str, str] = {}
    for harness_name in sorted({name for name in harness_names if name}):
        release = session.scalar(
            select(SearchHarnessRelease)
            .where(
                SearchHarnessRelease.candidate_harness_name == harness_name,
                SearchHarnessRelease.outcome == "passed",
            )
            .order_by(SearchHarnessRelease.created_at.desc())
            .limit(1)
        )
        if release is not None:
            releases[harness_name] = str(release.id)
    return releases


def record_technical_report_prov_export_governance_event(
    session: Session,
    *,
    artifact: AgentTaskArtifact,
    evidence_manifest: EvidenceManifest | None,
    change_impact: dict[str, Any] | None = None,
) -> SemanticGovernanceEvent:
    artifact_payload = _semantic_governance_core._json_payload(artifact.payload_json or {})
    frozen_export = artifact_payload.get("frozen_export") or {}
    receipt = frozen_export.get("export_receipt") or {}
    semantic_basis = _active_semantic_basis(session)
    search_requests = _search_requests_for_manifest(session, evidence_manifest)
    harness_names = sorted({row.harness_name for row in search_requests})
    latest_release_ids_by_harness = _latest_passed_releases_by_harness(session, harness_names)
    ontology_snapshot_id = _semantic_governance_core._uuid_or_none(
        semantic_basis.get("active_ontology_snapshot_id")
    )
    graph_snapshot_id = _semantic_governance_core._uuid_or_none(
        semantic_basis.get("active_semantic_graph_snapshot_id")
    )
    evidence_manifest_id = evidence_manifest.id if evidence_manifest is not None else None
    evidence_package_export_id = (
        evidence_manifest.evidence_package_export_id if evidence_manifest is not None else None
    )
    return _semantic_governance_core.record_semantic_governance_event(
        session,
        event_kind=SemanticGovernanceEventKind.TECHNICAL_REPORT_PROV_EXPORT_FROZEN.value,
        governance_scope=f"agent_task:{artifact.task_id}",
        subject_table="agent_task_artifacts",
        subject_id=artifact.id,
        task_id=artifact.task_id,
        ontology_snapshot_id=ontology_snapshot_id,
        semantic_graph_snapshot_id=graph_snapshot_id,
        evidence_manifest_id=evidence_manifest_id,
        evidence_package_export_id=evidence_package_export_id,
        agent_task_artifact_id=artifact.id,
        receipt_sha256=receipt.get("receipt_sha256"),
        event_payload={
            "technical_report_prov_export": {
                "artifact_id": str(artifact.id),
                "artifact_kind": artifact.artifact_kind,
                "task_id": str(artifact.task_id),
                "storage_path": artifact.storage_path,
                "export_payload_sha256": frozen_export.get("export_payload_sha256"),
                "prov_hash_basis_sha256": frozen_export.get("prov_hash_basis_sha256"),
                "receipt_sha256": receipt.get("receipt_sha256"),
                "receipt_signature_status": receipt.get("signature_status"),
                "receipt_signing_key_id": receipt.get("signing_key_id"),
            },
            "evidence_manifest": {
                "evidence_manifest_id": (
                    str(evidence_manifest.id) if evidence_manifest is not None else None
                ),
                "manifest_sha256": (
                    evidence_manifest.manifest_sha256 if evidence_manifest is not None else None
                ),
                "trace_sha256": (
                    evidence_manifest.trace_sha256 if evidence_manifest is not None else None
                ),
                "evidence_package_export_id": (
                    str(evidence_package_export_id)
                    if evidence_package_export_id is not None
                    else None
                ),
                "search_request_ids": (
                    list(evidence_manifest.search_request_ids_json or [])
                    if evidence_manifest is not None
                    else []
                ),
            },
            "semantic_basis": semantic_basis,
            "retrieval_basis": {
                "search_request_count": len(search_requests),
                "search_request_ids": [str(row.id) for row in search_requests],
                "harness_names": harness_names,
                "retrieval_profile_names": sorted(
                    {row.retrieval_profile_name for row in search_requests}
                ),
                "rerankers": sorted(
                    {f"{row.reranker_name}:{row.reranker_version}" for row in search_requests}
                ),
                "latest_passed_search_harness_release_ids_by_harness": (
                    latest_release_ids_by_harness
                ),
            },
            "change_impact": change_impact or {"status": "not_evaluated_at_freeze"},
        },
        deduplication_key=(
            f"technical_report_prov_export_frozen:{artifact.id}:"
            f"{receipt.get('receipt_sha256') or frozen_export.get('export_payload_sha256')}"
        ),
        created_by="technical_report_verification",
    )


def record_technical_report_release_readiness_db_gate_event(
    session: Session,
    *,
    gate: TechnicalReportReleaseReadinessDbGate,
) -> SemanticGovernanceEvent:
    semantic_basis = _active_semantic_basis(session)
    ontology_snapshot_id = _semantic_governance_core._uuid_or_none(
        semantic_basis.get("active_ontology_snapshot_id")
    )
    graph_snapshot_id = _semantic_governance_core._uuid_or_none(
        semantic_basis.get("active_semantic_graph_snapshot_id")
    )
    return _semantic_governance_core.record_semantic_governance_event(
        session,
        event_kind=SemanticGovernanceEventKind.TECHNICAL_REPORT_READINESS_DB_GATE_RECORDED.value,
        governance_scope=f"agent_task:{gate.technical_report_verification_task_id}",
        subject_table="technical_report_release_readiness_db_gates",
        subject_id=gate.id,
        task_id=gate.technical_report_verification_task_id,
        ontology_snapshot_id=ontology_snapshot_id,
        semantic_graph_snapshot_id=graph_snapshot_id,
        evidence_manifest_id=gate.evidence_manifest_id,
        agent_task_artifact_id=gate.prov_export_artifact_id,
        event_payload={
            "technical_report_release_readiness_db_gate": {
                "gate_id": str(gate.id),
                "technical_report_verification_task_id": str(
                    gate.technical_report_verification_task_id
                ),
                "source_verification_id": str(gate.source_verification_id),
                "source_verification_task_id": _semantic_governance_core._uuid_text(
                    gate.source_verification_task_id
                ),
                "harness_task_id": _semantic_governance_core._uuid_text(gate.harness_task_id),
                "evidence_manifest_id": _semantic_governance_core._uuid_text(
                    gate.evidence_manifest_id
                ),
                "prov_export_artifact_id": _semantic_governance_core._uuid_text(
                    gate.prov_export_artifact_id
                ),
                "check_key": gate.check_key,
                "passed": gate.passed,
                "coverage_complete": gate.coverage_complete,
                "complete": gate.complete,
                "source_search_request_count": gate.source_search_request_count,
                "verified_request_count": gate.verified_request_count,
                "failure_count": gate.failure_count,
                "source_search_request_ids": list(gate.source_search_request_ids_json or []),
                "verified_request_ids": list(gate.verified_request_ids_json or []),
                "missing_expected_request_ids": list(gate.missing_expected_request_ids_json or []),
                "unexpected_verified_request_ids": list(
                    gate.unexpected_verified_request_ids_json or []
                ),
                "gate_payload_sha256": gate.gate_payload_sha256,
            },
            "semantic_basis": semantic_basis,
        },
        deduplication_key=(
            "technical_report_readiness_db_gate_recorded:"
            f"{gate.id}:{gate.gate_payload_sha256}:"
            f"{gate.evidence_manifest_id}:{gate.prov_export_artifact_id}"
        ),
        created_by="technical_report_verification",
    )


def record_technical_report_claim_retrieval_feedback_event(
    session: Session,
    *,
    feedback: TechnicalReportClaimRetrievalFeedback,
) -> SemanticGovernanceEvent:
    semantic_basis = _active_semantic_basis(session)
    ontology_snapshot_id = _semantic_governance_core._uuid_or_none(
        semantic_basis.get("active_ontology_snapshot_id")
    )
    graph_snapshot_id = _semantic_governance_core._uuid_or_none(
        semantic_basis.get("active_semantic_graph_snapshot_id")
    )
    return _semantic_governance_core.record_semantic_governance_event(
        session,
        event_kind=(
            SemanticGovernanceEventKind.TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_RECORDED.value
        ),
        governance_scope=f"agent_task:{feedback.technical_report_verification_task_id}",
        subject_table="technical_report_claim_retrieval_feedback",
        subject_id=feedback.id,
        task_id=feedback.technical_report_verification_task_id,
        ontology_snapshot_id=ontology_snapshot_id,
        semantic_graph_snapshot_id=graph_snapshot_id,
        evidence_manifest_id=feedback.evidence_manifest_id,
        agent_task_artifact_id=feedback.prov_export_artifact_id,
        receipt_sha256=feedback.feedback_payload_sha256,
        event_payload={
            "technical_report_claim_retrieval_feedback": {
                "feedback_id": str(feedback.id),
                "technical_report_verification_task_id": str(
                    feedback.technical_report_verification_task_id
                ),
                "claim_id": feedback.claim_id,
                "claim_evidence_derivation_id": _semantic_governance_core._uuid_text(
                    feedback.claim_evidence_derivation_id
                ),
                "evidence_manifest_id": _semantic_governance_core._uuid_text(
                    feedback.evidence_manifest_id
                ),
                "prov_export_artifact_id": _semantic_governance_core._uuid_text(
                    feedback.prov_export_artifact_id
                ),
                "release_readiness_db_gate_id": _semantic_governance_core._uuid_text(
                    feedback.release_readiness_db_gate_id
                ),
                "support_verdict": feedback.support_verdict,
                "support_score": feedback.support_score,
                "feedback_status": feedback.feedback_status,
                "learning_label": feedback.learning_label,
                "hard_negative_kind": feedback.hard_negative_kind,
                "source_search_request_ids": list(feedback.source_search_request_ids_json or []),
                "source_search_request_result_ids": list(
                    feedback.source_search_request_result_ids_json or []
                ),
                "search_request_result_span_ids": list(
                    feedback.search_request_result_span_ids_json or []
                ),
                "retrieval_evidence_span_ids": list(
                    feedback.retrieval_evidence_span_ids_json or []
                ),
                "feedback_payload_sha256": feedback.feedback_payload_sha256,
                "source_payload_sha256": feedback.source_payload_sha256,
            },
            "semantic_basis": semantic_basis,
        },
        deduplication_key=(
            "technical_report_claim_retrieval_feedback_recorded:"
            f"{feedback.id}:{feedback.feedback_payload_sha256}:"
            f"{feedback.evidence_manifest_id}:{feedback.prov_export_artifact_id}"
        ),
        created_by="technical_report_verification",
    )
