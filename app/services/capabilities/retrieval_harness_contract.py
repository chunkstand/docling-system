from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.search import (
    SearchHarnessDescriptorResponse,
    SearchHarnessEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessEvaluationSummaryResponse,
    SearchHarnessReleaseGateRequest,
    SearchHarnessReleaseReadinessAssessmentRequest,
    SearchHarnessReleaseReadinessAssessmentResponse,
    SearchHarnessReleaseReadinessResponse,
    SearchHarnessReleaseResponse,
    SearchHarnessReleaseSummaryResponse,
    SearchHarnessResponse,
)


class RetrievalHarnessCapability(Protocol):
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
