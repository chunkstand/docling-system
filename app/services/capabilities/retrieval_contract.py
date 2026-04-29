from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

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
)
from app.services import search
from app.services.storage import StorageService


class RetrievalCapability(Protocol):
    def execute_search(
        self,
        session: Session,
        request: SearchRequest,
        *,
        origin: str,
        run_id: UUID | None = None,
        parent_search_request_id: UUID | None = None,
        evaluation_id: UUID | None = None,
    ) -> search.SearchExecution: ...

    def get_search_request_detail(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchRequestDetailResponse: ...

    def get_search_request_explanation(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchRequestExplanationResponse: ...

    def get_search_evidence_package(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> dict: ...

    def export_search_evidence_package(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> dict: ...

    def get_search_evidence_package_export_trace(
        self,
        session: Session,
        evidence_package_export_id: UUID,
    ) -> dict: ...

    def record_search_feedback(
        self,
        session: Session,
        search_request_id: UUID,
        payload: SearchFeedbackCreateRequest,
    ) -> SearchFeedbackResponse: ...

    def replay_search_request(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchReplayResponse: ...

    def list_search_replay_runs(
        self,
        session: Session,
    ) -> list[SearchReplayRunSummaryResponse]: ...

    def run_search_replay_suite(
        self,
        session: Session,
        payload: SearchReplayRunRequest,
    ) -> SearchReplayRunDetailResponse: ...

    def compare_search_replay_runs(
        self,
        session: Session,
        *,
        baseline_replay_run_id: UUID,
        candidate_replay_run_id: UUID,
    ) -> SearchReplayComparisonResponse: ...

    def get_search_replay_run_detail(
        self,
        session: Session,
        replay_run_id: UUID,
    ) -> SearchReplayRunDetailResponse: ...

    def explain_search_replay_run(
        self,
        session: Session,
        replay_run_id: UUID,
    ) -> dict: ...

    def list_search_harness_definitions(self) -> list[SearchHarnessResponse]: ...

    def get_search_harness_descriptor(
        self,
        harness_name: str,
    ) -> SearchHarnessDescriptorResponse: ...

    def list_search_harness_evaluations(
        self,
        session: Session,
        *,
        limit: int,
        candidate_harness_name: str | None = None,
    ) -> list[SearchHarnessEvaluationSummaryResponse]: ...

    def evaluate_search_harness(
        self,
        session: Session,
        payload: SearchHarnessEvaluationRequest,
    ) -> SearchHarnessEvaluationResponse: ...

    def get_search_harness_evaluation_detail(
        self,
        session: Session,
        evaluation_id: UUID,
    ) -> SearchHarnessEvaluationResponse: ...

    def create_search_harness_release_gate(
        self,
        session: Session,
        payload: SearchHarnessReleaseGateRequest,
    ) -> SearchHarnessReleaseResponse: ...

    def list_search_harness_releases(
        self,
        session: Session,
        *,
        limit: int,
        candidate_harness_name: str | None = None,
        outcome: str | None = None,
    ) -> list[SearchHarnessReleaseSummaryResponse]: ...

    def get_search_harness_release_detail(
        self,
        session: Session,
        release_id: UUID,
    ) -> SearchHarnessReleaseResponse: ...

    def get_search_harness_release_readiness(
        self,
        session: Session,
        release_id: UUID,
    ) -> SearchHarnessReleaseReadinessResponse: ...

    def create_search_harness_release_readiness_assessment(
        self,
        session: Session,
        release_id: UUID,
        payload: SearchHarnessReleaseReadinessAssessmentRequest,
    ) -> SearchHarnessReleaseReadinessAssessmentResponse: ...

    def get_latest_search_harness_release_readiness_assessment(
        self,
        session: Session,
        release_id: UUID,
    ) -> SearchHarnessReleaseReadinessAssessmentResponse: ...

    def get_search_harness_release_readiness_assessment(
        self,
        session: Session,
        release_id: UUID,
        assessment_id: UUID,
    ) -> SearchHarnessReleaseReadinessAssessmentResponse: ...

    def create_search_harness_release_audit_bundle(
        self,
        session: Session,
        release_id: UUID,
        payload: SearchHarnessReleaseAuditBundleRequest,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse: ...

    def get_latest_search_harness_release_audit_bundle(
        self,
        session: Session,
        release_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse: ...

    def create_retrieval_training_run_audit_bundle(
        self,
        session: Session,
        training_run_id: UUID,
        payload: RetrievalTrainingRunAuditBundleRequest,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse: ...

    def get_latest_retrieval_training_run_audit_bundle(
        self,
        session: Session,
        training_run_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse: ...

    def get_audit_bundle_export(
        self,
        session: Session,
        bundle_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse: ...

    def create_audit_bundle_validation_receipt(
        self,
        session: Session,
        bundle_id: UUID,
        payload: AuditBundleValidationReceiptRequest,
        *,
        storage_service: StorageService,
    ) -> AuditBundleValidationReceiptResponse: ...

    def list_audit_bundle_validation_receipts(
        self,
        session: Session,
        bundle_id: UUID,
    ) -> list[AuditBundleValidationReceiptSummaryResponse]: ...

    def get_audit_bundle_validation_receipt(
        self,
        session: Session,
        bundle_id: UUID,
        receipt_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleValidationReceiptResponse: ...

    def get_latest_audit_bundle_validation_receipt(
        self,
        session: Session,
        bundle_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleValidationReceiptResponse: ...

    def evaluate_retrieval_learning_candidate(
        self,
        session: Session,
        payload: RetrievalLearningCandidateEvaluationRequest,
    ) -> RetrievalLearningCandidateEvaluationResponse: ...

    def list_retrieval_learning_candidate_evaluations(
        self,
        session: Session,
        *,
        limit: int,
        retrieval_training_run_id: UUID | None = None,
        candidate_harness_name: str | None = None,
    ) -> list[RetrievalLearningCandidateEvaluationSummaryResponse]: ...

    def get_retrieval_learning_candidate_evaluation_detail(
        self,
        session: Session,
        candidate_evaluation_id: UUID,
    ) -> RetrievalLearningCandidateEvaluationResponse: ...

    def create_retrieval_reranker_artifact(
        self,
        session: Session,
        payload: RetrievalRerankerArtifactRequest,
    ) -> RetrievalRerankerArtifactResponse: ...

    def list_retrieval_reranker_artifacts(
        self,
        session: Session,
        *,
        limit: int,
        retrieval_training_run_id: UUID | None = None,
        candidate_harness_name: str | None = None,
    ) -> list[RetrievalRerankerArtifactSummaryResponse]: ...

    def get_retrieval_reranker_artifact_detail(
        self,
        session: Session,
        artifact_id: UUID,
    ) -> RetrievalRerankerArtifactResponse: ...

    def answer_question(self, session: Session, request: ChatRequest) -> ChatResponse: ...

    def record_chat_answer_feedback(
        self,
        session: Session,
        chat_answer_id: UUID,
        payload: ChatAnswerFeedbackCreateRequest,
    ) -> ChatAnswerFeedbackResponse: ...
