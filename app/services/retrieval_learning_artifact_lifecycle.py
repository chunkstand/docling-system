from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from fastapi import status
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.hashes import payload_sha256 as _payload_sha256
from app.core.json_utils import canonical_json_value as _json_payload
from app.core.time import utcnow
from app.db.public.retrieval import RetrievalRerankerArtifact
from app.schemas.search import (
    RetrievalRerankerArtifactRequest,
    RetrievalRerankerArtifactResponse,
    SearchHarnessEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessReleaseGateRequest,
    SearchHarnessReleaseResponse,
)
from app.services.retrieval_learning_artifact_contracts import (
    RETRIEVAL_RERANKER_ARTIFACT_KIND,
    RETRIEVAL_RERANKER_ARTIFACT_SCHEMA,
    RETRIEVAL_RERANKER_ARTIFACT_SCHEMA_VERSION,
)
from app.services.retrieval_learning_artifact_governance import (
    record_reranker_artifact_governance_event,
)
from app.services.retrieval_learning_artifact_impacts import change_impact_report
from app.services.retrieval_learning_artifact_views import to_reranker_artifact_response
from app.services.retrieval_learning_artifact_weights import (
    candidate_request_from_artifact_request,
    feature_weight_candidate,
)
from app.services.retrieval_learning_candidates import (
    create_candidate_evaluation_row,
    learning_candidate_package,
    resolve_training_run,
    thresholds_from_candidate_request,
)


def create_retrieval_reranker_artifact(
    session: Session,
    request: RetrievalRerankerArtifactRequest,
    *,
    get_search_harness_fn: Callable[[str], Any],
    evaluate_search_harness_fn: Callable[..., SearchHarnessEvaluationResponse],
    record_search_harness_release_gate_fn: Callable[..., SearchHarnessReleaseResponse],
) -> RetrievalRerankerArtifactResponse:
    training_run = resolve_training_run(session, request.retrieval_training_run_id)
    created_at = utcnow()
    artifact_id = uuid.uuid4()
    artifact_name = request.artifact_name or (
        f"{request.candidate_harness_name}-reranker-{artifact_id.hex[:8]}"
    )
    try:
        feature_weights, harness_overrides, override_spec = feature_weight_candidate(
            training_run=training_run,
            base_harness_name=request.base_harness_name,
            candidate_harness_name=request.candidate_harness_name,
            artifact_name=artifact_name,
            get_search_harness_fn=get_search_harness_fn,
        )
    except ValueError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "search_harness_not_found",
            str(exc),
            base_harness_name=request.base_harness_name,
        ) from exc

    candidate_request = candidate_request_from_artifact_request(request)
    evaluation = evaluate_search_harness_fn(
        session,
        SearchHarnessEvaluationRequest(
            candidate_harness_name=request.candidate_harness_name,
            baseline_harness_name=request.baseline_harness_name,
            source_types=request.source_types,
            limit=request.limit,
        ),
        harness_overrides=harness_overrides,
    )
    if evaluation.evaluation_id is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "search_harness_evaluation_missing_id",
            "Reranker artifacts require a durable search harness evaluation.",
        )
    release = record_search_harness_release_gate_fn(
        session,
        evaluation,
        SearchHarnessReleaseGateRequest(
            evaluation_id=evaluation.evaluation_id,
            max_total_regressed_count=request.max_total_regressed_count,
            max_mrr_drop=request.max_mrr_drop,
            max_zero_result_count_increase=request.max_zero_result_count_increase,
            max_foreign_top_result_count_increase=(
                request.max_foreign_top_result_count_increase
            ),
            min_total_shared_query_count=request.min_total_shared_query_count,
            requested_by=request.requested_by,
            review_note=request.review_note,
        ),
        requested_by=request.requested_by,
        review_note=request.review_note,
    )
    candidate_package = learning_candidate_package(
        training_run=training_run,
        evaluation=evaluation,
        release=release,
        request=candidate_request,
    )
    candidate_row = create_candidate_evaluation_row(
        session,
        training_run=training_run,
        evaluation=evaluation,
        release=release,
        baseline_harness_name=request.baseline_harness_name,
        candidate_harness_name=request.candidate_harness_name,
        source_types=list(request.source_types),
        limit=request.limit,
        thresholds=thresholds_from_candidate_request(candidate_request),
        details={
            "schema_name": "retrieval_learning_candidate_evaluation_details",
            "schema_version": "1.0",
            "learning_loop_stage": "training_dataset_to_reranker_artifact_gate",
            "training_dataset_summary": training_run.summary_json or {},
            "reranker_artifact": {
                "artifact_id": str(artifact_id),
                "artifact_name": artifact_name,
                "artifact_kind": RETRIEVAL_RERANKER_ARTIFACT_KIND,
                "override_spec": override_spec,
            },
            "release_gate": {
                "outcome": release.outcome,
                "metrics": release.metrics,
                "reasons": release.reasons,
                "details": release.details,
            },
        },
        learning_package_sha256=_payload_sha256(candidate_package),
        created_by=request.requested_by,
        review_note=request.review_note,
        created_at=created_at,
    )

    artifact_version = (
        f"{request.candidate_harness_name}+{training_run.training_dataset_sha256[:12]}"
    )
    artifact_payload = _json_payload(
        {
            "schema_name": RETRIEVAL_RERANKER_ARTIFACT_SCHEMA,
            "schema_version": RETRIEVAL_RERANKER_ARTIFACT_SCHEMA_VERSION,
            "artifact_id": artifact_id,
            "artifact_kind": RETRIEVAL_RERANKER_ARTIFACT_KIND,
            "artifact_name": artifact_name,
            "artifact_version": artifact_version,
            "candidate_harness_name": request.candidate_harness_name,
            "base_harness_name": request.base_harness_name,
            "baseline_harness_name": request.baseline_harness_name,
            "retrieval_training_run": {
                "retrieval_training_run_id": training_run.id,
                "judgment_set_id": training_run.judgment_set_id,
                "training_dataset_sha256": training_run.training_dataset_sha256,
                "training_example_count": training_run.example_count,
            },
            "feature_weights": feature_weights,
            "harness_overrides": harness_overrides,
            "evaluation": evaluation.model_dump(mode="json"),
            "release": release.model_dump(mode="json"),
        }
    )
    artifact_sha256 = _payload_sha256(artifact_payload)
    impact_report = change_impact_report(
        session,
        artifact_id=artifact_id,
        artifact_payload=artifact_payload,
        artifact_sha256=artifact_sha256,
        training_run=training_run,
        evaluation=evaluation,
        release=release,
    )
    change_impact_sha256 = _payload_sha256(impact_report)
    row = RetrievalRerankerArtifact(
        id=artifact_id,
        retrieval_training_run_id=training_run.id,
        judgment_set_id=training_run.judgment_set_id,
        retrieval_learning_candidate_evaluation_id=candidate_row.id,
        search_harness_evaluation_id=evaluation.evaluation_id,
        search_harness_release_id=release.release_id,
        artifact_kind=RETRIEVAL_RERANKER_ARTIFACT_KIND,
        artifact_name=artifact_name,
        artifact_version=artifact_version,
        status="evaluated" if evaluation.status == "completed" else "failed",
        gate_outcome=release.outcome,
        baseline_harness_name=request.baseline_harness_name,
        candidate_harness_name=request.candidate_harness_name,
        source_types_json=list(request.source_types),
        limit=request.limit,
        training_dataset_sha256=training_run.training_dataset_sha256,
        training_example_count=training_run.example_count,
        positive_count=training_run.positive_count,
        negative_count=training_run.negative_count,
        missing_count=training_run.missing_count,
        hard_negative_count=training_run.hard_negative_count,
        thresholds_json=thresholds_from_candidate_request(candidate_request),
        metrics_json=release.metrics,
        reasons_json=list(release.reasons),
        feature_weights_json=feature_weights,
        harness_overrides_json=harness_overrides,
        artifact_payload_json=artifact_payload,
        evaluation_snapshot_json=evaluation.model_dump(mode="json"),
        release_snapshot_json=release.model_dump(mode="json"),
        change_impact_report_json=impact_report,
        artifact_sha256=artifact_sha256,
        change_impact_sha256=change_impact_sha256,
        created_by=request.requested_by,
        review_note=request.review_note,
        created_at=created_at,
        completed_at=created_at,
    )
    session.add(row)
    session.flush()
    record_reranker_artifact_governance_event(
        session,
        row=row,
        training_run=training_run,
    )
    return to_reranker_artifact_response(session, row)
