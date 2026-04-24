from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Document, DocumentRun, DocumentRunEvaluation
from app.schemas.eval_workbench import (
    EvalFailureCaseInspectionResponse,
    EvalFailureCaseRefreshResponse,
    EvalFailureCaseResponse,
    EvalObservationResponse,
    EvalWorkbenchResponse,
)
from app.schemas.evaluations import EvaluationDetailResponse
from app.services import documents, eval_workbench, evaluations


class EvaluationCapability(Protocol):
    def evaluate_run(
        self,
        session: Session,
        document: Document,
        run: DocumentRun,
        *,
        baseline_run_id: UUID | None = None,
        corpus_path: Path | None = None,
        corpus_name: str = evaluations.DEFAULT_CORPUS_NAME,
    ) -> DocumentRunEvaluation: ...

    def get_latest_document_evaluation_detail(
        self,
        session: Session,
        document_id: UUID,
    ) -> EvaluationDetailResponse: ...

    def explain_latest_document_evaluation(
        self,
        session: Session,
        document_id: UUID,
    ) -> dict: ...

    def explain_search_harness_evaluation(
        self,
        session: Session,
        evaluation_id: UUID,
    ) -> dict: ...

    def refresh_eval_failure_cases(
        self,
        session: Session,
        *,
        limit: int,
        include_resolved: bool = False,
    ) -> EvalFailureCaseRefreshResponse: ...

    def get_eval_workbench(self, session: Session, *, limit: int) -> EvalWorkbenchResponse: ...

    def list_eval_observations(
        self,
        session: Session,
        *,
        limit: int,
    ) -> list[EvalObservationResponse]: ...

    def list_eval_failure_cases(
        self,
        session: Session,
        *,
        status_filter: list[str] | None = None,
        include_resolved: bool = False,
        limit: int,
    ) -> list[EvalFailureCaseResponse]: ...

    def get_eval_failure_case(
        self,
        session: Session,
        case_id: UUID,
    ) -> EvalFailureCaseResponse: ...

    def inspect_eval_failure_case(
        self,
        session: Session,
        case_id: UUID,
    ) -> EvalFailureCaseInspectionResponse: ...


class ServicesEvaluationCapability:
    def evaluate_run(
        self,
        session: Session,
        document: Document,
        run: DocumentRun,
        *,
        baseline_run_id: UUID | None = None,
        corpus_path: Path | None = None,
        corpus_name: str = evaluations.DEFAULT_CORPUS_NAME,
    ) -> DocumentRunEvaluation:
        return evaluations.evaluate_run(
            session,
            document,
            run,
            baseline_run_id=baseline_run_id,
            corpus_path=corpus_path,
            corpus_name=corpus_name,
        )

    def get_latest_document_evaluation_detail(
        self,
        session: Session,
        document_id: UUID,
    ) -> EvaluationDetailResponse:
        return documents.get_latest_document_evaluation_detail(session, document_id)

    def explain_latest_document_evaluation(
        self,
        session: Session,
        document_id: UUID,
    ) -> dict:
        return eval_workbench.explain_latest_document_evaluation(session, document_id)

    def explain_search_harness_evaluation(
        self,
        session: Session,
        evaluation_id: UUID,
    ) -> dict:
        return eval_workbench.explain_search_harness_evaluation(session, evaluation_id)

    def refresh_eval_failure_cases(
        self,
        session: Session,
        *,
        limit: int,
        include_resolved: bool = False,
    ) -> EvalFailureCaseRefreshResponse:
        return eval_workbench.refresh_eval_failure_cases(
            session,
            limit=limit,
            include_resolved=include_resolved,
        )

    def get_eval_workbench(self, session: Session, *, limit: int) -> EvalWorkbenchResponse:
        return eval_workbench.get_eval_workbench(session, limit=limit)

    def list_eval_observations(
        self,
        session: Session,
        *,
        limit: int,
    ) -> list[EvalObservationResponse]:
        return eval_workbench.list_eval_observations(session, limit=limit)

    def list_eval_failure_cases(
        self,
        session: Session,
        *,
        status_filter: list[str] | None = None,
        include_resolved: bool = False,
        limit: int,
    ) -> list[EvalFailureCaseResponse]:
        return eval_workbench.list_eval_failure_cases(
            session,
            status_filter=status_filter,
            include_resolved=include_resolved,
            limit=limit,
        )

    def get_eval_failure_case(
        self,
        session: Session,
        case_id: UUID,
    ) -> EvalFailureCaseResponse:
        return eval_workbench.get_eval_failure_case(session, case_id)

    def inspect_eval_failure_case(
        self,
        session: Session,
        case_id: UUID,
    ) -> EvalFailureCaseInspectionResponse:
        return eval_workbench.inspect_eval_failure_case(session, case_id)


evaluation: EvaluationCapability = ServicesEvaluationCapability()
