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
)
from app.api.errors import api_error
from app.api.routers import (
    search_audit_bundles,
    search_chat,
    search_harnesses,
    search_learning,
    search_replays,
)
from app.db.session import get_db_session
from app.schemas.search import (
    SearchFeedbackCreateRequest,
    SearchFeedbackResponse,
    SearchReplayResponse,
    SearchRequest,
    SearchRequestDetailResponse,
    SearchRequestExplanationResponse,
    SearchResult,
)
from app.services.capabilities import evaluation, retrieval
from app.services.storage import StorageService

router = APIRouter()
router.include_router(search_audit_bundles.router)
router.include_router(search_chat.router)
router.include_router(search_harnesses.router)
router.include_router(search_learning.router)
router.include_router(search_replays.router)
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
create_search_harness_release_audit_bundle = retrieval.create_search_harness_release_audit_bundle
get_latest_search_harness_release_audit_bundle = (
    retrieval.get_latest_search_harness_release_audit_bundle
)
create_retrieval_training_run_audit_bundle = retrieval.create_retrieval_training_run_audit_bundle
get_latest_retrieval_training_run_audit_bundle = (
    retrieval.get_latest_retrieval_training_run_audit_bundle
)
get_audit_bundle_export = retrieval.get_audit_bundle_export
create_audit_bundle_validation_receipt = retrieval.create_audit_bundle_validation_receipt
list_audit_bundle_validation_receipts = retrieval.list_audit_bundle_validation_receipts
get_audit_bundle_validation_receipt = retrieval.get_audit_bundle_validation_receipt
get_latest_audit_bundle_validation_receipt = retrieval.get_latest_audit_bundle_validation_receipt
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
