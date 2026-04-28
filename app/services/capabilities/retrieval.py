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
    RetrievalTrainingRunAuditBundleRequest,
    SearchFeedbackCreateRequest,
    SearchFeedbackResponse,
    SearchHarnessDescriptorResponse,
    SearchHarnessEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessEvaluationSummaryResponse,
    SearchHarnessReleaseAuditBundleRequest,
    SearchHarnessReleaseGateRequest,
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
from app.services import (
    audit_bundles,
    chat,
    eval_workbench,
    evidence,
    retrieval_learning,
    search,
    search_harness_evaluations,
    search_history,
    search_legibility,
    search_release_gate,
    search_replays,
)
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

    def answer_question(self, session: Session, request: ChatRequest) -> ChatResponse: ...

    def record_chat_answer_feedback(
        self,
        session: Session,
        chat_answer_id: UUID,
        payload: ChatAnswerFeedbackCreateRequest,
    ) -> ChatAnswerFeedbackResponse: ...


class ServicesRetrievalCapability:
    def execute_search(
        self,
        session: Session,
        request: SearchRequest,
        *,
        origin: str,
        run_id: UUID | None = None,
        parent_search_request_id: UUID | None = None,
        evaluation_id: UUID | None = None,
    ) -> search.SearchExecution:
        return search.execute_search(
            session,
            request,
            origin=origin,
            run_id=run_id,
            parent_request_id=parent_search_request_id,
            evaluation_id=evaluation_id,
        )

    def get_search_request_detail(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchRequestDetailResponse:
        return search_history.get_search_request_detail(session, search_request_id)

    def get_search_request_explanation(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchRequestExplanationResponse:
        return search_legibility.get_search_request_explanation(session, search_request_id)

    def get_search_evidence_package(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> dict:
        return evidence.get_search_evidence_package(session, search_request_id)

    def export_search_evidence_package(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> dict:
        return evidence.export_search_evidence_package(
            session,
            search_request_id=search_request_id,
        )

    def get_search_evidence_package_export_trace(
        self,
        session: Session,
        evidence_package_export_id: UUID,
    ) -> dict:
        return evidence.get_search_evidence_package_export_trace(
            session,
            evidence_package_export_id,
        )

    def record_search_feedback(
        self,
        session: Session,
        search_request_id: UUID,
        payload: SearchFeedbackCreateRequest,
    ) -> SearchFeedbackResponse:
        return search_history.record_search_feedback(session, search_request_id, payload)

    def replay_search_request(
        self,
        session: Session,
        search_request_id: UUID,
    ) -> SearchReplayResponse:
        return search_history.replay_search_request(session, search_request_id)

    def list_search_replay_runs(
        self,
        session: Session,
    ) -> list[SearchReplayRunSummaryResponse]:
        return search_replays.list_search_replay_runs(session)

    def run_search_replay_suite(
        self,
        session: Session,
        payload: SearchReplayRunRequest,
    ) -> SearchReplayRunDetailResponse:
        return search_replays.run_search_replay_suite(session, payload)

    def compare_search_replay_runs(
        self,
        session: Session,
        *,
        baseline_replay_run_id: UUID,
        candidate_replay_run_id: UUID,
    ) -> SearchReplayComparisonResponse:
        return search_replays.compare_search_replay_runs(
            session,
            baseline_replay_run_id=baseline_replay_run_id,
            candidate_replay_run_id=candidate_replay_run_id,
        )

    def get_search_replay_run_detail(
        self,
        session: Session,
        replay_run_id: UUID,
    ) -> SearchReplayRunDetailResponse:
        return search_replays.get_search_replay_run_detail(session, replay_run_id)

    def explain_search_replay_run(
        self,
        session: Session,
        replay_run_id: UUID,
    ) -> dict:
        return eval_workbench.explain_search_replay_run(session, replay_run_id)

    def list_search_harness_definitions(self) -> list[SearchHarnessResponse]:
        return search_harness_evaluations.list_search_harness_definitions()

    def get_search_harness_descriptor(
        self,
        harness_name: str,
    ) -> SearchHarnessDescriptorResponse:
        return search_legibility.get_search_harness_descriptor(harness_name)

    def list_search_harness_evaluations(
        self,
        session: Session,
        *,
        limit: int,
        candidate_harness_name: str | None = None,
    ) -> list[SearchHarnessEvaluationSummaryResponse]:
        return search_harness_evaluations.list_search_harness_evaluations(
            session,
            limit=limit,
            candidate_harness_name=candidate_harness_name,
        )

    def evaluate_search_harness(
        self,
        session: Session,
        payload: SearchHarnessEvaluationRequest,
    ) -> SearchHarnessEvaluationResponse:
        return search_harness_evaluations.evaluate_search_harness(session, payload)

    def get_search_harness_evaluation_detail(
        self,
        session: Session,
        evaluation_id: UUID,
    ) -> SearchHarnessEvaluationResponse:
        return search_harness_evaluations.get_search_harness_evaluation_detail(
            session,
            evaluation_id,
        )

    def create_search_harness_release_gate(
        self,
        session: Session,
        payload: SearchHarnessReleaseGateRequest,
    ) -> SearchHarnessReleaseResponse:
        return search_release_gate.create_search_harness_release_gate(session, payload)

    def list_search_harness_releases(
        self,
        session: Session,
        *,
        limit: int,
        candidate_harness_name: str | None = None,
        outcome: str | None = None,
    ) -> list[SearchHarnessReleaseSummaryResponse]:
        return search_release_gate.list_search_harness_releases(
            session,
            limit=limit,
            candidate_harness_name=candidate_harness_name,
            outcome=outcome,
        )

    def get_search_harness_release_detail(
        self,
        session: Session,
        release_id: UUID,
    ) -> SearchHarnessReleaseResponse:
        return search_release_gate.get_search_harness_release_detail(session, release_id)

    def create_search_harness_release_audit_bundle(
        self,
        session: Session,
        release_id: UUID,
        payload: SearchHarnessReleaseAuditBundleRequest,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse:
        return audit_bundles.create_search_harness_release_audit_bundle(
            session,
            release_id,
            payload,
            storage_service=storage_service,
        )

    def get_latest_search_harness_release_audit_bundle(
        self,
        session: Session,
        release_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse:
        return audit_bundles.get_latest_search_harness_release_audit_bundle(
            session,
            release_id,
            storage_service=storage_service,
        )

    def create_retrieval_training_run_audit_bundle(
        self,
        session: Session,
        training_run_id: UUID,
        payload: RetrievalTrainingRunAuditBundleRequest,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse:
        return audit_bundles.create_retrieval_training_run_audit_bundle(
            session,
            training_run_id,
            payload,
            storage_service=storage_service,
        )

    def get_latest_retrieval_training_run_audit_bundle(
        self,
        session: Session,
        training_run_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse:
        return audit_bundles.get_latest_retrieval_training_run_audit_bundle(
            session,
            training_run_id,
            storage_service=storage_service,
        )

    def get_audit_bundle_export(
        self,
        session: Session,
        bundle_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleExportResponse:
        return audit_bundles.get_audit_bundle_export(
            session,
            bundle_id,
            storage_service=storage_service,
        )

    def create_audit_bundle_validation_receipt(
        self,
        session: Session,
        bundle_id: UUID,
        payload: AuditBundleValidationReceiptRequest,
        *,
        storage_service: StorageService,
    ) -> AuditBundleValidationReceiptResponse:
        return audit_bundles.create_audit_bundle_validation_receipt(
            session,
            bundle_id,
            payload,
            storage_service=storage_service,
        )

    def get_latest_audit_bundle_validation_receipt(
        self,
        session: Session,
        bundle_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleValidationReceiptResponse:
        return audit_bundles.get_latest_audit_bundle_validation_receipt(
            session,
            bundle_id,
            storage_service=storage_service,
        )

    def list_audit_bundle_validation_receipts(
        self,
        session: Session,
        bundle_id: UUID,
    ) -> list[AuditBundleValidationReceiptSummaryResponse]:
        return audit_bundles.list_audit_bundle_validation_receipts(session, bundle_id)

    def get_audit_bundle_validation_receipt(
        self,
        session: Session,
        bundle_id: UUID,
        receipt_id: UUID,
        *,
        storage_service: StorageService,
    ) -> AuditBundleValidationReceiptResponse:
        return audit_bundles.get_audit_bundle_validation_receipt(
            session,
            bundle_id,
            receipt_id,
            storage_service=storage_service,
        )

    def evaluate_retrieval_learning_candidate(
        self,
        session: Session,
        payload: RetrievalLearningCandidateEvaluationRequest,
    ) -> RetrievalLearningCandidateEvaluationResponse:
        return retrieval_learning.evaluate_retrieval_learning_candidate(session, payload)

    def list_retrieval_learning_candidate_evaluations(
        self,
        session: Session,
        *,
        limit: int,
        retrieval_training_run_id: UUID | None = None,
        candidate_harness_name: str | None = None,
    ) -> list[RetrievalLearningCandidateEvaluationSummaryResponse]:
        return retrieval_learning.list_retrieval_learning_candidate_evaluations(
            session,
            limit=limit,
            retrieval_training_run_id=retrieval_training_run_id,
            candidate_harness_name=candidate_harness_name,
        )

    def get_retrieval_learning_candidate_evaluation_detail(
        self,
        session: Session,
        candidate_evaluation_id: UUID,
    ) -> RetrievalLearningCandidateEvaluationResponse:
        return retrieval_learning.get_retrieval_learning_candidate_evaluation_detail(
            session,
            candidate_evaluation_id,
        )

    def answer_question(self, session: Session, request: ChatRequest) -> ChatResponse:
        return chat.answer_question(session, request)

    def record_chat_answer_feedback(
        self,
        session: Session,
        chat_answer_id: UUID,
        payload: ChatAnswerFeedbackCreateRequest,
    ) -> ChatAnswerFeedbackResponse:
        return chat.record_chat_answer_feedback(session, chat_answer_id, payload)


retrieval: RetrievalCapability = ServicesRetrievalCapability()
