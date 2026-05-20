from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import (
    RetrievalRerankerArtifact,
    RetrievalTrainingRun,
    SemanticGovernanceEventKind,
)
from app.services.semantic_governance import record_semantic_governance_event


def record_reranker_artifact_governance_event(
    session: Session,
    *,
    row: RetrievalRerankerArtifact,
    training_run: RetrievalTrainingRun,
) -> None:
    event = record_semantic_governance_event(
        session,
        event_kind=SemanticGovernanceEventKind.RETRIEVAL_RERANKER_ARTIFACT_MATERIALIZED.value,
        governance_scope=f"retrieval_reranker_artifact:{row.id}",
        subject_table="retrieval_reranker_artifacts",
        subject_id=row.id,
        search_harness_evaluation_id=row.search_harness_evaluation_id,
        search_harness_release_id=row.search_harness_release_id,
        event_payload={
            "retrieval_reranker_artifact": {
                "artifact_id": str(row.id),
                "artifact_kind": row.artifact_kind,
                "artifact_name": row.artifact_name,
                "artifact_version": row.artifact_version,
                "retrieval_training_run_id": str(training_run.id),
                "judgment_set_id": str(training_run.judgment_set_id),
                "candidate_evaluation_id": str(
                    row.retrieval_learning_candidate_evaluation_id
                ),
                "search_harness_evaluation_id": str(row.search_harness_evaluation_id),
                "search_harness_release_id": (
                    str(row.search_harness_release_id)
                    if row.search_harness_release_id is not None
                    else None
                ),
                "training_dataset_sha256": row.training_dataset_sha256,
                "artifact_sha256": row.artifact_sha256,
                "change_impact_sha256": row.change_impact_sha256,
                "gate_outcome": row.gate_outcome,
                "feature_weights": row.feature_weights_json or {},
                "harness_overrides": row.harness_overrides_json or {},
            }
        },
        deduplication_key=(
            f"retrieval_reranker_artifact_materialized:{row.id}:"
            f"{row.artifact_sha256}:{row.change_impact_sha256}"
        ),
        created_by=row.created_by,
    )
    row.semantic_governance_event_id = event.id
    session.flush()
