from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

import app.api.capabilities as api_capabilities
from app.api.deps import (
    enforce_search_rate_limit,
    get_storage_service,
    require_api_capability,
    require_api_key_for_mutations,
    response_field,
)
from app.api.errors import api_error
from app.db.session import get_db_session
from app.schemas.chat import (
    ChatAnswerFeedbackCreateRequest,
    ChatAnswerFeedbackResponse,
    ChatRequest,
    ChatResponse,
)
from app.schemas.search import (
    AuditBundleExportResponse,
    AuditBundleValidationReceiptRequest,
    AuditBundleValidationReceiptResponse,
    AuditBundleValidationReceiptSummaryResponse,
    RetrievalLearningCandidateEvaluationRequest,
    RetrievalLearningCandidateEvaluationResponse,
    RetrievalLearningCandidateEvaluationSummaryResponse,
    RetrievalRerankerArtifactRequest,
    RetrievalRerankerArtifactResponse,
    RetrievalRerankerArtifactSummaryResponse,
    RetrievalTrainingRunAuditBundleRequest,
    SearchFeedbackCreateRequest,
    SearchFeedbackResponse,
    SearchHarnessDescriptorResponse,
    SearchHarnessEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessEvaluationSummaryResponse,
    SearchHarnessReleaseAuditBundleRequest,
    SearchHarnessReleaseGateRequest,
    SearchHarnessReleaseReadinessAssessmentRequest,
    SearchHarnessReleaseReadinessAssessmentResponse,
    SearchHarnessReleaseReadinessResponse,
    SearchHarnessReleaseResponse,
    SearchHarnessReleaseSummaryResponse,
    SearchHarnessResponse,
    SearchReplayComparisonResponse,
    SearchReplayResponse,
    SearchReplayRunDetailResponse,
    SearchReplayRunRequest,
    SearchReplayRunSummaryResponse,
    SearchRequest,
    SearchRequestDetailResponse,
    SearchRequestExplanationResponse,
    SearchResult,
)
from app.services.capabilities import evaluation, retrieval
from app.services.storage import StorageService

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]
StorageDep = Annotated[StorageService, Depends(get_storage_service)]
HarnessEvaluationLimitQuery = Annotated[int, Query(ge=1, le=200)]

execute_search = retrieval.execute_search
get_search_request_detail = retrieval.get_search_request_detail
get_search_request_explanation = retrieval.get_search_request_explanation
get_search_evidence_package = retrieval.get_search_evidence_package
export_search_evidence_package = retrieval.export_search_evidence_package
get_search_evidence_package_export_trace = retrieval.get_search_evidence_package_export_trace
record_search_feedback = retrieval.record_search_feedback
replay_search_request = retrieval.replay_search_request
list_search_replay_runs = retrieval.list_search_replay_runs
run_search_replay_suite = retrieval.run_search_replay_suite
compare_search_replay_runs = retrieval.compare_search_replay_runs
get_search_replay_run_detail = retrieval.get_search_replay_run_detail
explain_search_replay_run = retrieval.explain_search_replay_run
list_search_harness_definitions = retrieval.list_search_harness_definitions
get_search_harness_descriptor = retrieval.get_search_harness_descriptor
list_search_harness_evaluations = retrieval.list_search_harness_evaluations
evaluate_search_harness = retrieval.evaluate_search_harness
get_search_harness_evaluation_detail = retrieval.get_search_harness_evaluation_detail
create_search_harness_release_gate = retrieval.create_search_harness_release_gate
list_search_harness_releases = retrieval.list_search_harness_releases
get_search_harness_release_detail = retrieval.get_search_harness_release_detail
get_search_harness_release_readiness = retrieval.get_search_harness_release_readiness
create_search_harness_release_readiness_assessment = (
    retrieval.create_search_harness_release_readiness_assessment
)
get_latest_search_harness_release_readiness_assessment = (
    retrieval.get_latest_search_harness_release_readiness_assessment
)
get_search_harness_release_readiness_assessment = (
    retrieval.get_search_harness_release_readiness_assessment
)
create_search_harness_release_audit_bundle = (
    retrieval.create_search_harness_release_audit_bundle
)
get_latest_search_harness_release_audit_bundle = (
    retrieval.get_latest_search_harness_release_audit_bundle
)
create_retrieval_training_run_audit_bundle = (
    retrieval.create_retrieval_training_run_audit_bundle
)
get_latest_retrieval_training_run_audit_bundle = (
    retrieval.get_latest_retrieval_training_run_audit_bundle
)
get_audit_bundle_export = retrieval.get_audit_bundle_export
create_audit_bundle_validation_receipt = retrieval.create_audit_bundle_validation_receipt
list_audit_bundle_validation_receipts = retrieval.list_audit_bundle_validation_receipts
get_audit_bundle_validation_receipt = retrieval.get_audit_bundle_validation_receipt
get_latest_audit_bundle_validation_receipt = (
    retrieval.get_latest_audit_bundle_validation_receipt
)
evaluate_retrieval_learning_candidate = retrieval.evaluate_retrieval_learning_candidate
list_retrieval_learning_candidate_evaluations = (
    retrieval.list_retrieval_learning_candidate_evaluations
)
get_retrieval_learning_candidate_evaluation_detail = (
    retrieval.get_retrieval_learning_candidate_evaluation_detail
)
create_retrieval_reranker_artifact = retrieval.create_retrieval_reranker_artifact
list_retrieval_reranker_artifacts = retrieval.list_retrieval_reranker_artifacts
get_retrieval_reranker_artifact_detail = retrieval.get_retrieval_reranker_artifact_detail
explain_search_harness_evaluation = evaluation.explain_search_harness_evaluation
answer_question = retrieval.answer_question
record_chat_answer_feedback = retrieval.record_chat_answer_feedback


@router.post(
    "/search",
    response_model=list[SearchResult],
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_QUERY)),
        Depends(enforce_search_rate_limit),
    ],
)
def search_corpus(
    request: SearchRequest,
    response: Response,
    session: DbSession,
) -> list[SearchResult]:
    try:
        execution = execute_search(session, request, origin="api")
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_search_request",
            str(exc),
        ) from exc
    session.commit()
    if execution.request_id is not None:
        response.headers["X-Search-Request-Id"] = str(execution.request_id)
    return execution.results


@router.post(
    "/search/executions",
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_QUERY)),
        Depends(enforce_search_rate_limit),
    ],
)
def execute_search_with_explanation_ref(
    request: SearchRequest,
    response: Response,
    session: DbSession,
) -> dict:
    try:
        execution = execute_search(session, request, origin="api")
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_search_request",
            str(exc),
        ) from exc
    session.commit()
    search_request_id = str(execution.request_id) if execution.request_id is not None else None
    if search_request_id is not None:
        response.headers["X-Search-Request-Id"] = search_request_id
    return {
        "schema_name": "search_execution",
        "schema_version": "1.0",
        "search_request_id": search_request_id,
        "explanation_api_path": (
            f"/search/requests/{search_request_id}/explain"
            if search_request_id is not None
            else None
        ),
        "results": [row.model_dump(mode="json") for row in execution.results],
    }


@router.get(
    "/search/requests/{search_request_id}",
    response_model=SearchRequestDetailResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_HISTORY_READ))],
)
def read_search_request(
    search_request_id: UUID,
    session: DbSession,
) -> SearchRequestDetailResponse:
    return get_search_request_detail(session, search_request_id)


@router.get(
    "/search/requests/{search_request_id}/explain",
    response_model=SearchRequestExplanationResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_HISTORY_READ))],
)
def explain_search_request(
    search_request_id: UUID,
    session: DbSession,
) -> SearchRequestExplanationResponse:
    return get_search_request_explanation(session, search_request_id)


@router.get(
    "/search/requests/{search_request_id}/evidence-package",
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_HISTORY_READ))],
)
def read_search_evidence_package(
    search_request_id: UUID,
    session: DbSession,
) -> dict:
    try:
        return get_search_evidence_package(session, search_request_id)
    except ValueError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "search_request_not_found",
            str(exc),
            search_request_id=str(search_request_id),
        ) from exc


@router.post(
    "/search/requests/{search_request_id}/evidence-package/export",
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_HISTORY_READ)),
    ],
)
def export_search_evidence_package_route(
    search_request_id: UUID,
    session: DbSession,
) -> dict:
    try:
        response = export_search_evidence_package(session, search_request_id)
        session.commit()
        return response
    except ValueError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "search_request_not_found",
            str(exc),
            search_request_id=str(search_request_id),
        ) from exc


@router.get(
    "/search/evidence-package-exports/{evidence_package_export_id}/trace-graph",
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_HISTORY_READ))],
)
def read_search_evidence_package_export_trace(
    evidence_package_export_id: UUID,
    session: DbSession,
) -> dict:
    try:
        response = get_search_evidence_package_export_trace(
            session,
            evidence_package_export_id,
        )
        session.commit()
        return response
    except ValueError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "search_evidence_package_export_not_found",
            str(exc),
            evidence_package_export_id=str(evidence_package_export_id),
        ) from exc


@router.post(
    "/search/requests/{search_request_id}/feedback",
    response_model=SearchFeedbackResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_FEEDBACK)),
    ],
)
def create_search_feedback(
    search_request_id: UUID,
    payload: SearchFeedbackCreateRequest,
    session: DbSession,
) -> SearchFeedbackResponse:
    feedback = record_search_feedback(session, search_request_id, payload)
    session.commit()
    return feedback


@router.post(
    "/search/requests/{search_request_id}/replay",
    response_model=SearchReplayResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_REPLAY)),
    ],
)
def replay_logged_search(
    search_request_id: UUID,
    session: DbSession,
) -> SearchReplayResponse:
    replay = replay_search_request(session, search_request_id)
    session.commit()
    return replay


@router.get(
    "/search/replays",
    response_model=list[SearchReplayRunSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_REPLAY))],
)
def read_search_replays(
    session: DbSession,
) -> list[SearchReplayRunSummaryResponse]:
    return list_search_replay_runs(session)


@router.get(
    "/search/harnesses",
    response_model=list[SearchHarnessResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harnesses() -> list[SearchHarnessResponse]:
    return list_search_harness_definitions()


@router.get(
    "/search/harnesses/{harness_name}/descriptor",
    response_model=SearchHarnessDescriptorResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harness_descriptor(harness_name: str) -> SearchHarnessDescriptorResponse:
    try:
        return get_search_harness_descriptor(harness_name)
    except ValueError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "search_harness_not_found",
            str(exc),
            harness_name=harness_name,
        ) from exc


@router.get(
    "/search/harness-evaluations",
    response_model=list[SearchHarnessEvaluationSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harness_evaluations(
    session: DbSession,
    limit: HarnessEvaluationLimitQuery = 20,
    candidate_harness_name: str | None = None,
) -> list[SearchHarnessEvaluationSummaryResponse]:
    return list_search_harness_evaluations(
        session,
        limit=limit,
        candidate_harness_name=candidate_harness_name,
    )


@router.post(
    "/search/harness-evaluations",
    response_model=SearchHarnessEvaluationResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_search_harness_evaluation(
    response: Response,
    payload: SearchHarnessEvaluationRequest,
    session: DbSession,
) -> SearchHarnessEvaluationResponse:
    try:
        evaluation_response = evaluate_search_harness(session, payload)
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_search_harness_evaluation",
            str(exc),
        ) from exc
    session.commit()
    evaluation_id = response_field(evaluation_response, "evaluation_id")
    if evaluation_id is not None:
        response.headers["Location"] = f"/search/harness-evaluations/{evaluation_id}"
    return evaluation_response


@router.get(
    "/search/harness-evaluations/{evaluation_id}",
    response_model=SearchHarnessEvaluationResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harness_evaluation(
    evaluation_id: UUID,
    session: DbSession,
) -> SearchHarnessEvaluationResponse:
    return get_search_harness_evaluation_detail(session, evaluation_id)


@router.get(
    "/search/harness-evaluations/{evaluation_id}/explain",
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def explain_search_harness_evaluation_route(
    evaluation_id: UUID,
    session: DbSession,
) -> dict:
    return explain_search_harness_evaluation(session, evaluation_id)


@router.get(
    "/search/harness-releases",
    response_model=list[SearchHarnessReleaseSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harness_releases(
    session: DbSession,
    limit: HarnessEvaluationLimitQuery = 20,
    candidate_harness_name: str | None = None,
    outcome: str | None = Query(default=None, pattern="^(passed|failed|error)$"),
) -> list[SearchHarnessReleaseSummaryResponse]:
    return list_search_harness_releases(
        session,
        limit=limit,
        candidate_harness_name=candidate_harness_name,
        outcome=outcome,
    )


@router.post(
    "/search/harness-releases",
    response_model=SearchHarnessReleaseResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_search_harness_release(
    response: Response,
    payload: SearchHarnessReleaseGateRequest,
    session: DbSession,
) -> SearchHarnessReleaseResponse:
    release_response = create_search_harness_release_gate(session, payload)
    session.commit()
    release_id = response_field(release_response, "release_id")
    response.headers["Location"] = f"/search/harness-releases/{release_id}"
    return release_response


@router.get(
    "/search/harness-releases/{release_id}",
    response_model=SearchHarnessReleaseResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harness_release(
    release_id: UUID,
    session: DbSession,
) -> SearchHarnessReleaseResponse:
    return get_search_harness_release_detail(session, release_id)


@router.get(
    "/search/harness-releases/{release_id}/readiness",
    response_model=SearchHarnessReleaseReadinessResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harness_release_readiness(
    release_id: UUID,
    session: DbSession,
) -> SearchHarnessReleaseReadinessResponse:
    return get_search_harness_release_readiness(session, release_id)


@router.post(
    "/search/harness-releases/{release_id}/readiness-assessments",
    response_model=SearchHarnessReleaseReadinessAssessmentResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_search_harness_release_readiness_assessment_route(
    response: Response,
    release_id: UUID,
    payload: SearchHarnessReleaseReadinessAssessmentRequest,
    session: DbSession,
) -> SearchHarnessReleaseReadinessAssessmentResponse:
    assessment = create_search_harness_release_readiness_assessment(
        session,
        release_id,
        payload,
    )
    session.commit()
    assessment_id = response_field(assessment, "assessment_id")
    response.headers["Location"] = (
        f"/search/harness-releases/{release_id}/readiness-assessments/{assessment_id}"
    )
    return assessment


@router.get(
    "/search/harness-releases/{release_id}/readiness-assessments/latest",
    response_model=SearchHarnessReleaseReadinessAssessmentResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_latest_search_harness_release_readiness_assessment(
    release_id: UUID,
    session: DbSession,
) -> SearchHarnessReleaseReadinessAssessmentResponse:
    return get_latest_search_harness_release_readiness_assessment(session, release_id)


@router.get(
    "/search/harness-releases/{release_id}/readiness-assessments/{assessment_id}",
    response_model=SearchHarnessReleaseReadinessAssessmentResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_search_harness_release_readiness_assessment(
    release_id: UUID,
    assessment_id: UUID,
    session: DbSession,
) -> SearchHarnessReleaseReadinessAssessmentResponse:
    return get_search_harness_release_readiness_assessment(
        session,
        release_id,
        assessment_id,
    )


@router.get(
    "/search/retrieval-learning/candidate-evaluations",
    response_model=list[RetrievalLearningCandidateEvaluationSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_retrieval_learning_candidate_evaluations(
    session: DbSession,
    limit: HarnessEvaluationLimitQuery = 20,
    retrieval_training_run_id: UUID | None = None,
    candidate_harness_name: str | None = None,
) -> list[RetrievalLearningCandidateEvaluationSummaryResponse]:
    return list_retrieval_learning_candidate_evaluations(
        session,
        limit=limit,
        retrieval_training_run_id=retrieval_training_run_id,
        candidate_harness_name=candidate_harness_name,
    )


@router.post(
    "/search/retrieval-learning/candidate-evaluations",
    response_model=RetrievalLearningCandidateEvaluationResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_retrieval_learning_candidate_evaluation(
    response: Response,
    payload: RetrievalLearningCandidateEvaluationRequest,
    session: DbSession,
) -> RetrievalLearningCandidateEvaluationResponse:
    candidate_response = evaluate_retrieval_learning_candidate(session, payload)
    session.commit()
    candidate_evaluation_id = response_field(candidate_response, "candidate_evaluation_id")
    response.headers["Location"] = (
        f"/search/retrieval-learning/candidate-evaluations/{candidate_evaluation_id}"
    )
    return candidate_response


@router.get(
    "/search/retrieval-learning/candidate-evaluations/{candidate_evaluation_id}",
    response_model=RetrievalLearningCandidateEvaluationResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_retrieval_learning_candidate_evaluation(
    candidate_evaluation_id: UUID,
    session: DbSession,
) -> RetrievalLearningCandidateEvaluationResponse:
    return get_retrieval_learning_candidate_evaluation_detail(
        session,
        candidate_evaluation_id,
    )


@router.get(
    "/search/retrieval-learning/reranker-artifacts",
    response_model=list[RetrievalRerankerArtifactSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_retrieval_reranker_artifacts(
    session: DbSession,
    limit: HarnessEvaluationLimitQuery = 20,
    retrieval_training_run_id: UUID | None = None,
    candidate_harness_name: str | None = None,
) -> list[RetrievalRerankerArtifactSummaryResponse]:
    return list_retrieval_reranker_artifacts(
        session,
        limit=limit,
        retrieval_training_run_id=retrieval_training_run_id,
        candidate_harness_name=candidate_harness_name,
    )


@router.post(
    "/search/retrieval-learning/reranker-artifacts",
    response_model=RetrievalRerankerArtifactResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_retrieval_reranker_artifact_route(
    response: Response,
    payload: RetrievalRerankerArtifactRequest,
    session: DbSession,
) -> RetrievalRerankerArtifactResponse:
    artifact = create_retrieval_reranker_artifact(session, payload)
    session.commit()
    artifact_id = response_field(artifact, "artifact_id")
    response.headers["Location"] = (
        f"/search/retrieval-learning/reranker-artifacts/{artifact_id}"
    )
    return artifact


@router.get(
    "/search/retrieval-learning/reranker-artifacts/{artifact_id}",
    response_model=RetrievalRerankerArtifactResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_retrieval_reranker_artifact(
    artifact_id: UUID,
    session: DbSession,
) -> RetrievalRerankerArtifactResponse:
    return get_retrieval_reranker_artifact_detail(session, artifact_id)


@router.post(
    "/search/harness-releases/{release_id}/audit-bundles",
    response_model=AuditBundleExportResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_search_harness_release_audit_bundle_route(
    response: Response,
    release_id: UUID,
    payload: SearchHarnessReleaseAuditBundleRequest,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleExportResponse:
    bundle = create_search_harness_release_audit_bundle(
        session,
        release_id,
        payload,
        storage_service=storage_service,
    )
    session.commit()
    bundle_id = response_field(bundle, "bundle_id")
    response.headers["Location"] = f"/search/audit-bundles/{bundle_id}"
    return bundle


@router.get(
    "/search/harness-releases/{release_id}/audit-bundles/latest",
    response_model=AuditBundleExportResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_latest_search_harness_release_audit_bundle(
    release_id: UUID,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleExportResponse:
    return get_latest_search_harness_release_audit_bundle(
        session,
        release_id,
        storage_service=storage_service,
    )


@router.post(
    "/search/retrieval-training-runs/{training_run_id}/audit-bundles",
    response_model=AuditBundleExportResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_retrieval_training_run_audit_bundle_route(
    response: Response,
    training_run_id: UUID,
    payload: RetrievalTrainingRunAuditBundleRequest,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleExportResponse:
    bundle = create_retrieval_training_run_audit_bundle(
        session,
        training_run_id,
        payload,
        storage_service=storage_service,
    )
    session.commit()
    bundle_id = response_field(bundle, "bundle_id")
    response.headers["Location"] = f"/search/audit-bundles/{bundle_id}"
    return bundle


@router.get(
    "/search/retrieval-training-runs/{training_run_id}/audit-bundles/latest",
    response_model=AuditBundleExportResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_latest_retrieval_training_run_audit_bundle(
    training_run_id: UUID,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleExportResponse:
    return get_latest_retrieval_training_run_audit_bundle(
        session,
        training_run_id,
        storage_service=storage_service,
    )


@router.get(
    "/search/audit-bundles/{bundle_id}",
    response_model=AuditBundleExportResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_audit_bundle_export(
    bundle_id: UUID,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleExportResponse:
    return get_audit_bundle_export(session, bundle_id, storage_service=storage_service)


@router.post(
    "/search/audit-bundles/{bundle_id}/validation-receipts",
    response_model=AuditBundleValidationReceiptResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE)),
    ],
)
def create_audit_bundle_validation_receipt_route(
    response: Response,
    bundle_id: UUID,
    payload: AuditBundleValidationReceiptRequest,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleValidationReceiptResponse:
    receipt = create_audit_bundle_validation_receipt(
        session,
        bundle_id,
        payload,
        storage_service=storage_service,
    )
    session.commit()
    receipt_id = response_field(receipt, "receipt_id")
    response.headers["Location"] = (
        f"/search/audit-bundles/{bundle_id}/validation-receipts/{receipt_id}"
    )
    return receipt


@router.get(
    "/search/audit-bundles/{bundle_id}/validation-receipts",
    response_model=list[AuditBundleValidationReceiptSummaryResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def list_audit_bundle_validation_receipts_route(
    bundle_id: UUID,
    session: DbSession,
) -> list[AuditBundleValidationReceiptSummaryResponse]:
    return list_audit_bundle_validation_receipts(session, bundle_id)


@router.get(
    "/search/audit-bundles/{bundle_id}/validation-receipts/latest",
    response_model=AuditBundleValidationReceiptResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_latest_audit_bundle_validation_receipt(
    bundle_id: UUID,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleValidationReceiptResponse:
    return get_latest_audit_bundle_validation_receipt(
        session,
        bundle_id,
        storage_service=storage_service,
    )


@router.get(
    "/search/audit-bundles/{bundle_id}/validation-receipts/{receipt_id}",
    response_model=AuditBundleValidationReceiptResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_EVALUATE))],
)
def read_audit_bundle_validation_receipt(
    bundle_id: UUID,
    receipt_id: UUID,
    session: DbSession,
    storage_service: StorageDep,
) -> AuditBundleValidationReceiptResponse:
    return get_audit_bundle_validation_receipt(
        session,
        bundle_id,
        receipt_id,
        storage_service=storage_service,
    )


@router.post(
    "/search/replays",
    response_model=SearchReplayRunDetailResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.SEARCH_REPLAY)),
    ],
)
def create_search_replay_run(
    response: Response,
    payload: SearchReplayRunRequest,
    session: DbSession,
) -> SearchReplayRunDetailResponse:
    try:
        replay_run = run_search_replay_suite(session, payload)
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_search_replay_request",
            str(exc),
        ) from exc
    session.commit()
    replay_run_id = response_field(replay_run, "replay_run_id")
    if replay_run_id is not None:
        response.headers["Location"] = f"/search/replays/{replay_run_id}"
    return replay_run


@router.get(
    "/search/replays/compare",
    response_model=SearchReplayComparisonResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_REPLAY))],
)
def read_search_replay_comparison(
    baseline_replay_run_id: UUID,
    candidate_replay_run_id: UUID,
    session: DbSession,
) -> SearchReplayComparisonResponse:
    return compare_search_replay_runs(
        session,
        baseline_replay_run_id=baseline_replay_run_id,
        candidate_replay_run_id=candidate_replay_run_id,
    )


@router.get(
    "/search/replays/{replay_run_id}",
    response_model=SearchReplayRunDetailResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_REPLAY))],
)
def read_search_replay_run(
    replay_run_id: UUID,
    session: DbSession,
) -> SearchReplayRunDetailResponse:
    return get_search_replay_run_detail(session, replay_run_id)


@router.get(
    "/search/replays/{replay_run_id}/explain",
    dependencies=[Depends(require_api_capability(api_capabilities.SEARCH_REPLAY))],
)
def explain_search_replay_run_route(
    replay_run_id: UUID,
    session: DbSession,
) -> dict:
    return explain_search_replay_run(session, replay_run_id)


@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.CHAT_QUERY)),
    ],
)
def chat_with_corpus(
    request: ChatRequest,
    session: DbSession,
) -> ChatResponse:
    try:
        response = answer_question(session, request)
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_chat_request",
            str(exc),
        ) from exc
    session.commit()
    return response


@router.post(
    "/chat/answers/{chat_answer_id}/feedback",
    response_model=ChatAnswerFeedbackResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.CHAT_FEEDBACK)),
    ],
)
def create_chat_answer_feedback(
    chat_answer_id: UUID,
    payload: ChatAnswerFeedbackCreateRequest,
    session: DbSession,
) -> ChatAnswerFeedbackResponse:
    response = record_chat_answer_feedback(session, chat_answer_id, payload)
    session.commit()
    return response
