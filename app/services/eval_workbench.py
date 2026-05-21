from __future__ import annotations

from importlib import import_module
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.hashes import payload_sha256
from app.core.time import utcnow
from app.db.public.evaluation_feedback import EvalFailureCase, EvalObservation
from app.schemas.agent_task_core import AgentTaskCreateRequest
from app.schemas.eval_workbench import (
    EvalEvidenceRef,
    EvalFailureCaseResponse,
    EvalFailureCaseTriageResponse,
    EvalObservationResponse,
)

OPEN_CASE_STATUSES = {
    "open",
    "triaged",
    "drafted",
    "verified",
    "awaiting_approval",
}

SEARCH_REPAIR_SURFACES = [
    "retrieval_profile_overrides",
    "reranker_overrides",
]

BLOCKED_REPAIR_SURFACES = [
    "canonical_document_artifacts",
    "document_ingest_contracts",
    "evaluation_corpus_weakening",
    "yaml_as_source_of_truth",
]


def _case_key(parts: dict) -> str:
    return payload_sha256(parts)


def _case_not_found(case_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "eval_failure_case_not_found",
        "Eval failure case not found.",
        case_id=str(case_id),
    )


def _evidence_ref(
    *,
    ref_kind: str,
    api_path: str | None = None,
    summary: str | None = None,
    **ids,
) -> dict:
    return {
        "ref_kind": ref_kind,
        "api_path": api_path,
        "summary": summary,
        **{key: str(value) for key, value in ids.items() if value is not None},
    }


def _normalize_refs(rows: list[dict]) -> list[EvalEvidenceRef]:
    return [EvalEvidenceRef.model_validate(row) for row in rows]


def _to_observation_response(row: EvalObservation) -> EvalObservationResponse:
    return EvalObservationResponse(
        observation_id=row.id,
        observation_key=row.observation_key,
        surface=row.surface,
        subject_kind=row.subject_kind,
        subject_id=row.subject_id,
        status=row.status,
        severity=row.severity,
        failure_classification=row.failure_classification,
        summary=row.summary,
        document_id=row.document_id,
        run_id=row.run_id,
        evaluation_id=row.evaluation_id,
        evaluation_query_id=row.evaluation_query_id,
        search_request_id=row.search_request_id,
        replay_run_id=row.replay_run_id,
        harness_evaluation_id=row.harness_evaluation_id,
        agent_task_id=row.agent_task_id,
        details=row.details_json or {},
        evidence_refs=_normalize_refs(row.evidence_refs_json or []),
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_seen_at=row.last_seen_at,
    )


def _to_case_response(row: EvalFailureCase) -> EvalFailureCaseResponse:
    return EvalFailureCaseResponse(
        case_id=row.id,
        case_key=row.case_key,
        status=row.status,
        severity=row.severity,
        surface=row.surface,
        failure_classification=row.failure_classification,
        problem_statement=row.problem_statement,
        observed_behavior=row.observed_behavior,
        expected_behavior=row.expected_behavior,
        diagnosis=row.diagnosis,
        source_observation_id=row.source_observation_id,
        document_id=row.document_id,
        run_id=row.run_id,
        evaluation_id=row.evaluation_id,
        evaluation_query_id=row.evaluation_query_id,
        search_request_id=row.search_request_id,
        replay_run_id=row.replay_run_id,
        harness_evaluation_id=row.harness_evaluation_id,
        agent_task_id=row.agent_task_id,
        recommended_next_actions=list(row.recommended_next_actions_json or []),
        allowed_repair_surfaces=list(row.allowed_repair_surfaces_json or []),
        blocked_repair_surfaces=list(row.blocked_repair_surfaces_json or []),
        evidence_refs=_normalize_refs(row.evidence_refs_json or []),
        verification_requirements=row.verification_requirements_json or {},
        agent_task_payloads=row.agent_task_payloads_json or {},
        details=row.details_json or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_seen_at=row.last_seen_at,
        resolved_at=row.resolved_at,
    )


def _create_task_payload(
    task_type: str,
    payload: dict,
    *,
    workflow_version: str = "eval_v1",
) -> dict:
    return AgentTaskCreateRequest(
        task_type=task_type,
        input=payload,
        workflow_version=workflow_version,
    ).model_dump(mode="json")


def _default_task_payloads_for_case(case_id: UUID, *, search_related: bool) -> dict:
    payloads = {
        "inspect": _create_task_payload("inspect_eval_failure_case", {"case_id": str(case_id)}),
        "triage": _create_task_payload("triage_eval_failure_case", {"case_id": str(case_id)}),
    }
    if search_related:
        payloads["optimize_harness"] = _create_task_payload(
            "optimize_search_harness_from_case",
            {
                "case_id": str(case_id),
                "base_harness_name": "wide_v2",
                "baseline_harness_name": "wide_v2",
                "source_types": ["evaluation_queries", "feedback", "live_search_gaps"],
                "limit": 25,
                "iterations": 2,
            },
        )
    return payloads


def _verification_requirements_for_search_case() -> dict:
    return {
        "max_total_regressed_count": 0,
        "max_mrr_drop": 0.0,
        "max_zero_result_count_increase": 0,
        "max_foreign_top_result_count_increase": 0,
        "min_total_shared_query_count": 1,
        "requires_human_approval_for_apply": True,
    }


def list_eval_failure_cases(
    session: Session,
    *,
    status_filter: list[str] | None = None,
    include_resolved: bool = False,
    limit: int = 50,
) -> list[EvalFailureCaseResponse]:
    statement = select(EvalFailureCase).order_by(
        EvalFailureCase.updated_at.desc(),
        EvalFailureCase.created_at.desc(),
    )
    if status_filter:
        statement = statement.where(EvalFailureCase.status.in_(status_filter))
    elif not include_resolved:
        statement = statement.where(EvalFailureCase.status.in_(OPEN_CASE_STATUSES))
    rows = session.execute(statement.limit(limit)).scalars().all()
    return [_to_case_response(row) for row in rows]


def list_eval_observations(
    session: Session,
    *,
    limit: int = 50,
) -> list[EvalObservationResponse]:
    rows = (
        session.execute(
            select(EvalObservation)
            .order_by(EvalObservation.last_seen_at.desc(), EvalObservation.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [_to_observation_response(row) for row in rows]


def get_eval_failure_case_row(session: Session, case_id: UUID) -> EvalFailureCase:
    row = session.get(EvalFailureCase, case_id)
    if row is None:
        raise _case_not_found(case_id)
    return row


def get_eval_failure_case(session: Session, case_id: UUID) -> EvalFailureCaseResponse:
    return _to_case_response(get_eval_failure_case_row(session, case_id))


def triage_eval_failure_case(
    session: Session,
    case_id: UUID,
    *,
    agent_task_id: UUID | None = None,
) -> EvalFailureCaseTriageResponse:
    case = get_eval_failure_case_row(session, case_id)
    search_related = bool((case.details_json or {}).get("search_related"))
    if case.failure_classification in {"table_recall_gap", "search_recall_gap"}:
        next_action = "optimize_search_harness_from_case"
        confidence = "medium"
    elif case.failure_classification == "chat_grounding_failure":
        next_action = "human_review"
        confidence = "medium"
    elif search_related:
        next_action = "run_search_replay_suite"
        confidence = "low"
    else:
        next_action = "human_review"
        confidence = "low"

    diagnosis = case.diagnosis or _diagnosis_from_case(case)
    repair_case = {
        "schema_name": "eval_failure_repair_case",
        "schema_version": "1.0",
        "case_id": str(case.id),
        "failure_classification": case.failure_classification,
        "problem_statement": case.problem_statement,
        "diagnosis": diagnosis,
        "allowed_repair_surfaces": case.allowed_repair_surfaces_json or [],
        "blocked_repair_surfaces": case.blocked_repair_surfaces_json or [],
        "recommended_next_action": next_action,
        "evidence_refs": case.evidence_refs_json or [],
    }
    case.status = "triaged"
    case.diagnosis = diagnosis
    case.agent_task_id = agent_task_id
    case.updated_at = utcnow()
    case.details_json = {
        **(case.details_json or {}),
        "latest_triage": {
            "next_action": next_action,
            "confidence": confidence,
            "agent_task_id": str(agent_task_id) if agent_task_id else None,
        },
    }
    return EvalFailureCaseTriageResponse(
        case=_to_case_response(case),
        recommendation={
            "next_action": next_action,
            "confidence": confidence,
            "summary": f"{case.failure_classification}: {case.problem_statement}",
        },
        repair_case=repair_case,
        next_task_payloads=[
            payload
            for payload in [
                case.agent_task_payloads_json.get("optimize_harness"),
                case.agent_task_payloads_json.get("inspect"),
            ]
            if payload
        ],
    )


def _diagnosis_from_case(case: EvalFailureCase) -> str:
    if case.failure_classification == "table_recall_gap":
        return "The query expects table evidence but observed telemetry found no table hit."
    if case.failure_classification == "search_recall_gap":
        return "Candidate generation returned no usable evidence; repair recall before ranking."
    if case.failure_classification == "chat_grounding_failure":
        return "Answer feedback indicates insufficient or unsupported grounded context."
    if case.failure_classification == "parser_validation_failure":
        return "The run failed before validated promotion; inspect failure artifacts first."
    return "The quality signal needs bounded replay or human inspection before mutation."


refresh_owners = import_module("app.services.eval_workbench_refresh")
inspection_owners = import_module("app.services.eval_workbench_inspection")

_classification_for_quality_candidate = refresh_owners._classification_for_quality_candidate
_surface_for_quality_candidate = refresh_owners._surface_for_quality_candidate
_candidate_evidence_refs = refresh_owners._candidate_evidence_refs
_upsert_observation = refresh_owners._upsert_observation
_upsert_case = refresh_owners._upsert_case
_quality_candidate_payloads = refresh_owners._quality_candidate_payloads
_quality_failure_payloads = refresh_owners._quality_failure_payloads
refresh_eval_failure_cases = refresh_owners.refresh_eval_failure_cases
_linked_evidence = inspection_owners._linked_evidence
_recommended_workflow = inspection_owners._recommended_workflow
inspect_eval_failure_case = inspection_owners.inspect_eval_failure_case
get_eval_workbench = inspection_owners.get_eval_workbench
explain_latest_document_evaluation = inspection_owners.explain_latest_document_evaluation
explain_search_replay_run = inspection_owners.explain_search_replay_run
explain_search_harness_evaluation = inspection_owners.explain_search_harness_evaluation
