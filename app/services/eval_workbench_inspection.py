from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

import app.services.eval_workbench as workbench_owners
from app.core.time import utcnow
from app.db.models import EvalFailureCase, EvalObservation
from app.schemas.eval_workbench import (
    EvalFailureCaseInspectionResponse,
    EvalWorkbenchResponse,
    EvalWorkbenchSummaryResponse,
)
from app.services.documents import get_latest_document_evaluation_detail
from app.services.search_harness_evaluations import get_search_harness_evaluation_detail
from app.services.search_legibility import (
    get_search_harness_descriptor,
    get_search_request_explanation,
)
from app.services.search_replays import get_search_replay_run_detail


def _linked_evidence(session: Session, case: EvalFailureCase) -> dict:
    evidence: dict = {}
    if case.search_request_id is not None:
        try:
            evidence["search_request_explanation"] = get_search_request_explanation(
                session,
                case.search_request_id,
            ).model_dump(mode="json")
        except Exception as exc:
            evidence["search_request_explanation_error"] = str(exc)
    if case.replay_run_id is not None:
        try:
            evidence["search_replay_run"] = get_search_replay_run_detail(
                session,
                case.replay_run_id,
            ).model_dump(mode="json")
        except Exception as exc:
            evidence["search_replay_run_error"] = str(exc)
    if case.harness_evaluation_id is not None:
        try:
            evidence["search_harness_evaluation"] = get_search_harness_evaluation_detail(
                session,
                case.harness_evaluation_id,
            ).model_dump(mode="json")
        except Exception as exc:
            evidence["search_harness_evaluation_error"] = str(exc)
    if case.document_id is not None:
        try:
            evidence["latest_document_evaluation"] = get_latest_document_evaluation_detail(
                session,
                case.document_id,
            ).model_dump(mode="json")
        except Exception as exc:
            evidence["latest_document_evaluation_error"] = str(exc)
    return evidence


def _recommended_workflow(case: EvalFailureCase) -> list[dict]:
    workflow = [
        {
            "step": "inspect",
            "task_payload": case.agent_task_payloads_json.get("inspect"),
            "purpose": "Load the failure case and linked evidence.",
        },
        {
            "step": "triage",
            "task_payload": case.agent_task_payloads_json.get("triage"),
            "purpose": "Classify the issue and choose a bounded repair surface.",
        },
    ]
    optimize_payload = case.agent_task_payloads_json.get("optimize_harness")
    if optimize_payload:
        workflow.extend(
            [
                {
                    "step": "optimize_harness",
                    "task_payload": optimize_payload,
                    "purpose": "Run a bounded transient harness optimization loop.",
                },
                {
                    "step": "draft_harness",
                    "task_payload_template": {
                        "task_type": "draft_harness_config_update_from_optimization",
                        "input": {
                            "source_task_id": "<optimize_search_harness_from_case task id>",
                            "draft_harness_name": "<human-readable review harness name>",
                        },
                    },
                    "purpose": "Convert the best optimizer output into a review harness draft.",
                },
                {
                    "step": "verify_harness",
                    "task_payload_template": {
                        "task_type": "verify_draft_harness_config",
                        "input": {
                            "target_task_id": "<draft task id>",
                            **(case.verification_requirements_json or {}),
                        },
                    },
                    "purpose": "Run replay-backed verification before any apply task.",
                },
                {
                    "step": "apply_harness",
                    "task_payload_template": {
                        "task_type": "apply_harness_config_update",
                        "input": {
                            "draft_task_id": "<draft task id>",
                            "verification_task_id": "<verify task id>",
                            "reason": "Apply verified agent repair.",
                        },
                    },
                    "purpose": "Await human approval before changing live harness config.",
                },
            ]
        )
    return workflow


def inspect_eval_failure_case(
    session: Session,
    case_id: UUID,
) -> EvalFailureCaseInspectionResponse:
    case = workbench_owners.get_eval_failure_case_row(session, case_id)
    observation = (
        session.get(EvalObservation, case.source_observation_id)
        if case.source_observation_id is not None
        else None
    )
    return EvalFailureCaseInspectionResponse(
        case=workbench_owners._to_case_response(case),
        observation=workbench_owners._to_observation_response(observation)
        if observation is not None
        else None,
        linked_evidence=_linked_evidence(session, case),
        recommended_workflow=_recommended_workflow(case),
    )


def get_eval_workbench(
    session: Session,
    *,
    limit: int = 25,
) -> EvalWorkbenchResponse:
    cases = workbench_owners.list_eval_failure_cases(session, limit=limit)
    approval_queue = [
        case
        for case in workbench_owners.list_eval_failure_cases(
            session,
            status_filter=["awaiting_approval"],
            include_resolved=True,
            limit=limit,
        )
    ]
    recommended_payloads = []
    for case in cases:
        recommended_payloads.extend(case.agent_task_payloads.values())
    return EvalWorkbenchResponse(
        generated_at=utcnow(),
        summary=EvalWorkbenchSummaryResponse(
            open_case_count=len(cases),
            awaiting_approval_count=len(approval_queue),
            high_severity_count=sum(1 for case in cases if case.severity in {"high", "critical"}),
            refreshed_case_count=0,
            refreshed_observation_count=0,
        ),
        cases=cases,
        approval_queue=approval_queue,
        recommended_task_payloads=recommended_payloads,
        freshness_warnings=[],
    )


def explain_latest_document_evaluation(session: Session, document_id: UUID) -> dict:
    detail = get_latest_document_evaluation_detail(session, document_id)
    failed_queries = [row for row in detail.query_results if not row.passed]
    return {
        "schema_name": "document_evaluation_explanation",
        "schema_version": "1.0",
        "document_id": str(document_id),
        "evaluation_id": str(detail.evaluation_id),
        "status": detail.status,
        "summary": detail.summary,
        "diagnosis": {
            "category": "healthy" if not failed_queries else "failed_evaluation_queries",
            "failed_query_count": len(failed_queries),
            "structural_passed": detail.summary.get("structural_passed"),
        },
        "failed_queries": [row.model_dump(mode="json") for row in failed_queries[:10]],
        "recommended_next_action": (
            "No action required."
            if not failed_queries
            else "Create refresh_eval_failure_cases and triage the resulting cases."
        ),
    }


def explain_search_replay_run(session: Session, replay_run_id: UUID) -> dict:
    detail = get_search_replay_run_detail(session, replay_run_id)
    failures = [row for row in detail.query_results if not row.passed]
    return {
        "schema_name": "search_replay_explanation",
        "schema_version": "1.0",
        "replay_run_id": str(replay_run_id),
        "source_type": detail.source_type,
        "harness_name": detail.harness_name,
        "diagnosis": {
            "category": "healthy" if not failures else "replay_failures",
            "failed_query_count": len(failures),
            "zero_result_count": detail.zero_result_count,
            "max_rank_shift": detail.max_rank_shift,
        },
        "failed_queries": [row.model_dump(mode="json") for row in failures[:10]],
        "recommended_next_action": (
            "No action required."
            if not failures
            else "Create triage_replay_regression or optimize_search_harness_from_case."
        ),
    }


def explain_search_harness_evaluation(session: Session, evaluation_id: UUID) -> dict:
    detail = get_search_harness_evaluation_detail(session, evaluation_id)
    regressed_sources = [row for row in detail.sources if row.regressed_count > 0]
    try:
        candidate_descriptor = get_search_harness_descriptor(
            detail.candidate_harness_name
        ).model_dump(mode="json")
    except ValueError:
        candidate_descriptor = {}
    return {
        "schema_name": "search_harness_evaluation_explanation",
        "schema_version": "1.0",
        "evaluation_id": str(evaluation_id),
        "baseline_harness_name": detail.baseline_harness_name,
        "candidate_harness_name": detail.candidate_harness_name,
        "diagnosis": {
            "category": "healthy" if not regressed_sources else "harness_regression",
            "total_shared_query_count": detail.total_shared_query_count,
            "total_improved_count": detail.total_improved_count,
            "total_regressed_count": detail.total_regressed_count,
        },
        "regressed_sources": [row.model_dump(mode="json") for row in regressed_sources],
        "candidate_descriptor": candidate_descriptor,
        "recommended_next_action": (
            "Verify and draft/apply if approval is desired."
            if detail.total_regressed_count == 0
            else "Inspect changed replay queries before drafting a harness override."
        ),
    }
