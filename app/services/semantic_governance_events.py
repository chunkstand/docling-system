from __future__ import annotations

from sqlalchemy.orm import Session

import app.services.semantic_governance_context as _semantic_governance_context
import app.services.semantic_governance_core as _semantic_governance_core
from app.db.public.retrieval import SearchHarnessRelease, SearchHarnessReleaseReadinessAssessment
from app.db.public.semantic_memory import (
    SemanticGovernanceEvent,
    SemanticGovernanceEventKind,
    SemanticGraphSnapshot,
    SemanticOntologySnapshot,
)


def record_ontology_snapshot_governance_events(
    session: Session,
    snapshot: SemanticOntologySnapshot,
    *,
    activated: bool,
) -> list[SemanticGovernanceEvent]:
    payload = {
        "ontology_snapshot": {
            "ontology_snapshot_id": str(snapshot.id),
            "ontology_name": snapshot.ontology_name,
            "ontology_version": snapshot.ontology_version,
            "upper_ontology_version": snapshot.upper_ontology_version,
            "source_kind": snapshot.source_kind,
            "source_task_id": _semantic_governance_core._uuid_text(snapshot.source_task_id),
            "source_task_type": snapshot.source_task_type,
            "parent_snapshot_id": _semantic_governance_core._uuid_text(snapshot.parent_snapshot_id),
            "sha256": snapshot.sha256,
            "activated_at": _semantic_governance_core._created_at_text(snapshot.activated_at),
        }
    }
    events = [
        _semantic_governance_core.record_semantic_governance_event(
            session,
            event_kind=SemanticGovernanceEventKind.ONTOLOGY_SNAPSHOT_RECORDED.value,
            governance_scope=_semantic_governance_core.WORKSPACE_SEMANTIC_SCOPE,
            subject_table="semantic_ontology_snapshots",
            subject_id=snapshot.id,
            task_id=snapshot.source_task_id,
            ontology_snapshot_id=snapshot.id,
            event_payload=payload,
            deduplication_key=f"ontology_snapshot_recorded:{snapshot.id}:{snapshot.sha256}",
            created_by=snapshot.source_task_type,
        )
    ]
    if activated:
        events.append(
            _semantic_governance_core.record_semantic_governance_event(
                session,
                event_kind=SemanticGovernanceEventKind.ONTOLOGY_SNAPSHOT_ACTIVATED.value,
                governance_scope=_semantic_governance_core.WORKSPACE_SEMANTIC_SCOPE,
                subject_table="semantic_ontology_snapshots",
                subject_id=snapshot.id,
                task_id=snapshot.source_task_id,
                ontology_snapshot_id=snapshot.id,
                event_payload={
                    **payload,
                    "workspace_state": {
                        "workspace_key": _semantic_governance_core.WORKSPACE_SEMANTIC_STATE_KEY,
                        "active_ontology_snapshot_id": str(snapshot.id),
                    },
                },
                deduplication_key=f"ontology_snapshot_activated:{snapshot.id}:{snapshot.sha256}",
                created_by=snapshot.source_task_type,
            )
        )
    return events


def record_semantic_graph_snapshot_governance_events(
    session: Session,
    snapshot: SemanticGraphSnapshot,
    *,
    activated: bool,
) -> list[SemanticGovernanceEvent]:
    payload = {
        "semantic_graph_snapshot": {
            "semantic_graph_snapshot_id": str(snapshot.id),
            "graph_name": snapshot.graph_name,
            "graph_version": snapshot.graph_version,
            "ontology_snapshot_id": _semantic_governance_core._uuid_text(
                snapshot.ontology_snapshot_id
            ),
            "source_kind": snapshot.source_kind,
            "source_task_id": _semantic_governance_core._uuid_text(snapshot.source_task_id),
            "source_task_type": snapshot.source_task_type,
            "parent_snapshot_id": _semantic_governance_core._uuid_text(snapshot.parent_snapshot_id),
            "sha256": snapshot.sha256,
            "activated_at": _semantic_governance_core._created_at_text(snapshot.activated_at),
        }
    }
    events = [
        _semantic_governance_core.record_semantic_governance_event(
            session,
            event_kind=SemanticGovernanceEventKind.SEMANTIC_GRAPH_SNAPSHOT_RECORDED.value,
            governance_scope=_semantic_governance_core.WORKSPACE_SEMANTIC_SCOPE,
            subject_table="semantic_graph_snapshots",
            subject_id=snapshot.id,
            task_id=snapshot.source_task_id,
            ontology_snapshot_id=snapshot.ontology_snapshot_id,
            semantic_graph_snapshot_id=snapshot.id,
            event_payload=payload,
            deduplication_key=f"semantic_graph_snapshot_recorded:{snapshot.id}:{snapshot.sha256}",
            created_by=snapshot.source_task_type,
        )
    ]
    if activated:
        events.append(
            _semantic_governance_core.record_semantic_governance_event(
                session,
                event_kind=SemanticGovernanceEventKind.SEMANTIC_GRAPH_SNAPSHOT_ACTIVATED.value,
                governance_scope=_semantic_governance_core.WORKSPACE_SEMANTIC_SCOPE,
                subject_table="semantic_graph_snapshots",
                subject_id=snapshot.id,
                task_id=snapshot.source_task_id,
                ontology_snapshot_id=snapshot.ontology_snapshot_id,
                semantic_graph_snapshot_id=snapshot.id,
                event_payload={
                    **payload,
                    "workspace_graph_state": {
                        "workspace_key": (
                            _semantic_governance_core.WORKSPACE_SEMANTIC_GRAPH_STATE_KEY
                        ),
                        "active_graph_snapshot_id": str(snapshot.id),
                    },
                },
                deduplication_key=f"semantic_graph_snapshot_activated:{snapshot.id}:{snapshot.sha256}",
                created_by=snapshot.source_task_type,
            )
        )
    return events


def record_search_harness_release_governance_event(
    session: Session,
    release: SearchHarnessRelease,
) -> SemanticGovernanceEvent:
    semantic_basis = _semantic_governance_context._active_semantic_basis(session)
    ontology_snapshot_id = _semantic_governance_core._uuid_or_none(
        semantic_basis.get("active_ontology_snapshot_id")
    )
    graph_snapshot_id = _semantic_governance_core._uuid_or_none(
        semantic_basis.get("active_semantic_graph_snapshot_id")
    )
    return _semantic_governance_core.record_semantic_governance_event(
        session,
        event_kind=SemanticGovernanceEventKind.SEARCH_HARNESS_RELEASE_RECORDED.value,
        governance_scope=f"search_harness:{release.candidate_harness_name}",
        subject_table="search_harness_releases",
        subject_id=release.id,
        ontology_snapshot_id=ontology_snapshot_id,
        semantic_graph_snapshot_id=graph_snapshot_id,
        search_harness_evaluation_id=release.search_harness_evaluation_id,
        search_harness_release_id=release.id,
        event_payload={
            "search_harness_release": {
                "search_harness_release_id": str(release.id),
                "search_harness_evaluation_id": str(release.search_harness_evaluation_id),
                "outcome": release.outcome,
                "baseline_harness_name": release.baseline_harness_name,
                "candidate_harness_name": release.candidate_harness_name,
                "source_types": list(release.source_types_json or []),
                "metrics": release.metrics_json or {},
                "thresholds": release.thresholds_json or {},
                "release_package_sha256": release.release_package_sha256,
                "created_by": release.requested_by,
                "review_note": release.review_note,
            },
            "semantic_basis": semantic_basis,
        },
        deduplication_key=f"search_harness_release_recorded:{release.id}",
        created_by=release.requested_by,
    )


def record_search_harness_release_readiness_assessment_event(
    session: Session,
    *,
    assessment: SearchHarnessReleaseReadinessAssessment,
) -> SemanticGovernanceEvent:
    semantic_basis = _semantic_governance_context._active_semantic_basis(session)
    ontology_snapshot_id = _semantic_governance_core._uuid_or_none(
        semantic_basis.get("active_ontology_snapshot_id")
    )
    graph_snapshot_id = _semantic_governance_core._uuid_or_none(
        semantic_basis.get("active_semantic_graph_snapshot_id")
    )
    return _semantic_governance_core.record_semantic_governance_event(
        session,
        event_kind=(SemanticGovernanceEventKind.SEARCH_HARNESS_RELEASE_READINESS_ASSESSED.value),
        governance_scope=f"search_harness_release:{assessment.search_harness_release_id}",
        subject_table="search_harness_release_readiness_assessments",
        subject_id=assessment.id,
        ontology_snapshot_id=ontology_snapshot_id,
        semantic_graph_snapshot_id=graph_snapshot_id,
        search_harness_release_id=assessment.search_harness_release_id,
        receipt_sha256=assessment.assessment_payload_sha256,
        event_payload={
            "search_harness_release_readiness_assessment": {
                "assessment_id": str(assessment.id),
                "search_harness_release_id": str(assessment.search_harness_release_id),
                "release_audit_bundle_id": _semantic_governance_core._uuid_text(
                    assessment.release_audit_bundle_id
                ),
                "release_validation_receipt_id": _semantic_governance_core._uuid_text(
                    assessment.release_validation_receipt_id
                ),
                "readiness_profile": assessment.readiness_profile,
                "readiness_status": assessment.readiness_status,
                "ready": assessment.ready,
                "blockers": list(assessment.blockers_json or []),
                "readiness_payload_sha256": assessment.readiness_payload_sha256,
                "assessment_payload_sha256": assessment.assessment_payload_sha256,
                "created_by": assessment.created_by,
                "review_note": assessment.review_note,
            },
            "semantic_basis": semantic_basis,
        },
        deduplication_key=(
            "search_harness_release_readiness_assessed:"
            f"{assessment.id}:{assessment.assessment_payload_sha256}"
        ),
        created_by=assessment.created_by,
    )
