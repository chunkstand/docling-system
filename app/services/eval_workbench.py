from __future__ import annotations

import hashlib
import json
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.time import utcnow
from app.db.models import EvalFailureCase, EvalObservation
from app.schemas.agent_tasks import AgentTaskCreateRequest
from app.schemas.eval_workbench import (
    EvalEvidenceRef,
    EvalFailureCaseInspectionResponse,
    EvalFailureCaseRefreshResponse,
    EvalFailureCaseResponse,
    EvalFailureCaseTriageResponse,
    EvalObservationResponse,
    EvalWorkbenchResponse,
    EvalWorkbenchSummaryResponse,
)
from app.services.documents import get_latest_document_evaluation_detail
from app.services.quality import get_quality_failures, list_quality_eval_candidates
from app.services.search_harness_evaluations import get_search_harness_evaluation_detail
from app.services.search_legibility import (
    get_search_harness_descriptor,
    get_search_request_explanation,
)
from app.services.search_replays import get_search_replay_run_detail

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


def _payload_fingerprint(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _case_key(parts: dict) -> str:
    return _payload_fingerprint(parts)


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


def _classification_for_quality_candidate(candidate) -> str:
    candidate_type = candidate.candidate_type
    reason = candidate.reason.lower()
    if candidate.chat_answer_id is not None:
        return "chat_grounding_failure"
    if "table" in reason or candidate.expected_result_type == "table":
        return "table_recall_gap"
    if "no results" in reason:
        return "search_recall_gap"
    if "failed answer" in reason:
        return "chat_grounding_failure"
    if candidate_type == "failed_evaluation_query":
        return "evaluation_query_failure"
    return "search_quality_gap"


def _surface_for_quality_candidate(candidate) -> str:
    if candidate.chat_answer_id is not None:
        return "chat_answer"
    if candidate.search_request_id is not None:
        return "search_request"
    return "document_evaluation"


def _candidate_evidence_refs(candidate) -> list[dict]:
    refs: list[dict] = []
    if candidate.evaluation_id is not None:
        refs.append(
            _evidence_ref(
                ref_kind="document_evaluation",
                api_path=(
                    f"/documents/{candidate.document_id}/evaluations/latest"
                    if candidate.document_id is not None
                    else None
                ),
                summary="Persisted document-run evaluation that surfaced this case.",
                evaluation_id=candidate.evaluation_id,
                document_id=candidate.document_id,
            )
        )
    if candidate.search_request_id is not None:
        refs.append(
            _evidence_ref(
                ref_kind="search_request_explanation",
                api_path=f"/search/requests/{candidate.search_request_id}/explain",
                summary="Persisted search request explanation for this quality gap.",
                search_request_id=candidate.search_request_id,
            )
        )
    if candidate.chat_answer_id is not None:
        refs.append(
            _evidence_ref(
                ref_kind="chat_answer",
                summary="Persisted chat answer feedback that surfaced this case.",
                agent_task_id=None,
            )
        )
    return refs


def _upsert_observation(session: Session, payload: dict, *, now) -> EvalObservation:
    row = (
        session.execute(
            select(EvalObservation)
            .where(EvalObservation.observation_key == payload["observation_key"])
            .limit(1)
        )
        .scalars()
        .first()
    )
    if row is None:
        row = EvalObservation(
            id=payload["id"],
            observation_key=payload["observation_key"],
            surface=payload["surface"],
            subject_kind=payload["subject_kind"],
            subject_id=payload.get("subject_id"),
            created_at=now,
            updated_at=now,
            last_seen_at=now,
            status="active",
            severity=payload["severity"],
            failure_classification=payload["failure_classification"],
            summary=payload["summary"],
            document_id=payload.get("document_id"),
            run_id=payload.get("run_id"),
            evaluation_id=payload.get("evaluation_id"),
            evaluation_query_id=payload.get("evaluation_query_id"),
            search_request_id=payload.get("search_request_id"),
            replay_run_id=payload.get("replay_run_id"),
            harness_evaluation_id=payload.get("harness_evaluation_id"),
            agent_task_id=payload.get("agent_task_id"),
            details_json=payload.get("details") or {},
            evidence_refs_json=payload.get("evidence_refs") or [],
        )
        session.add(row)
        session.flush()
        return row

    row.status = "active"
    row.severity = payload["severity"]
    row.failure_classification = payload["failure_classification"]
    row.summary = payload["summary"]
    row.subject_kind = payload["subject_kind"]
    row.subject_id = payload.get("subject_id")
    row.document_id = payload.get("document_id")
    row.run_id = payload.get("run_id")
    row.evaluation_id = payload.get("evaluation_id")
    row.evaluation_query_id = payload.get("evaluation_query_id")
    row.search_request_id = payload.get("search_request_id")
    row.replay_run_id = payload.get("replay_run_id")
    row.harness_evaluation_id = payload.get("harness_evaluation_id")
    row.agent_task_id = payload.get("agent_task_id")
    row.details_json = payload.get("details") or {}
    row.evidence_refs_json = payload.get("evidence_refs") or []
    row.updated_at = now
    row.last_seen_at = now
    return row


def _upsert_case(session: Session, payload: dict, *, now) -> EvalFailureCase:
    row = (
        session.execute(
            select(EvalFailureCase).where(EvalFailureCase.case_key == payload["case_key"]).limit(1)
        )
        .scalars()
        .first()
    )
    if row is None:
        row = EvalFailureCase(
            id=payload["id"],
            case_key=payload["case_key"],
            status="open",
            severity=payload["severity"],
            surface=payload["surface"],
            failure_classification=payload["failure_classification"],
            problem_statement=payload["problem_statement"],
            observed_behavior=payload["observed_behavior"],
            expected_behavior=payload["expected_behavior"],
            diagnosis=payload.get("diagnosis"),
            source_observation_id=payload.get("source_observation_id"),
            document_id=payload.get("document_id"),
            run_id=payload.get("run_id"),
            evaluation_id=payload.get("evaluation_id"),
            evaluation_query_id=payload.get("evaluation_query_id"),
            search_request_id=payload.get("search_request_id"),
            replay_run_id=payload.get("replay_run_id"),
            harness_evaluation_id=payload.get("harness_evaluation_id"),
            agent_task_id=payload.get("agent_task_id"),
            recommended_next_actions_json=payload.get("recommended_next_actions") or [],
            allowed_repair_surfaces_json=payload.get("allowed_repair_surfaces") or [],
            blocked_repair_surfaces_json=payload.get("blocked_repair_surfaces") or [],
            evidence_refs_json=payload.get("evidence_refs") or [],
            verification_requirements_json=payload.get("verification_requirements") or {},
            agent_task_payloads_json=payload.get("agent_task_payloads") or {},
            details_json=payload.get("details") or {},
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )
        session.add(row)
        session.flush()
        return row

    if row.status in {"resolved", "suppressed"}:
        row.status = "open"
        row.resolved_at = None
    row.severity = payload["severity"]
    row.surface = payload["surface"]
    row.failure_classification = payload["failure_classification"]
    row.problem_statement = payload["problem_statement"]
    row.observed_behavior = payload["observed_behavior"]
    row.expected_behavior = payload["expected_behavior"]
    row.diagnosis = payload.get("diagnosis")
    row.source_observation_id = payload.get("source_observation_id")
    row.document_id = payload.get("document_id")
    row.run_id = payload.get("run_id")
    row.evaluation_id = payload.get("evaluation_id")
    row.evaluation_query_id = payload.get("evaluation_query_id")
    row.search_request_id = payload.get("search_request_id")
    row.replay_run_id = payload.get("replay_run_id")
    row.harness_evaluation_id = payload.get("harness_evaluation_id")
    row.agent_task_id = payload.get("agent_task_id")
    row.recommended_next_actions_json = payload.get("recommended_next_actions") or []
    row.allowed_repair_surfaces_json = payload.get("allowed_repair_surfaces") or []
    row.blocked_repair_surfaces_json = payload.get("blocked_repair_surfaces") or []
    row.evidence_refs_json = payload.get("evidence_refs") or []
    row.verification_requirements_json = payload.get("verification_requirements") or {}
    row.agent_task_payloads_json = payload.get("agent_task_payloads") or {}
    row.details_json = payload.get("details") or {}
    row.updated_at = now
    row.last_seen_at = now
    return row


def _quality_candidate_payloads(
    session: Session,
    *,
    limit: int,
    include_resolved: bool,
) -> list[dict]:
    now = utcnow()
    payloads: list[dict] = []
    for candidate in list_quality_eval_candidates(
        session,
        limit=limit,
        include_resolved=include_resolved,
    ):
        classification = _classification_for_quality_candidate(candidate)
        surface = _surface_for_quality_candidate(candidate)
        subject_id = (
            candidate.search_request_id
            or candidate.evaluation_id
            or candidate.chat_answer_id
            or candidate.document_id
        )
        key_parts = {
            "source": "quality_candidate",
            "candidate_type": candidate.candidate_type,
            "query_text": candidate.query_text,
            "mode": candidate.mode,
            "filters": candidate.filters,
            "expected_result_type": candidate.expected_result_type,
            "document_id": str(candidate.document_id) if candidate.document_id else None,
            "evaluation_id": str(candidate.evaluation_id) if candidate.evaluation_id else None,
            "search_request_id": str(candidate.search_request_id)
            if candidate.search_request_id
            else None,
        }
        observation_key = _case_key({"observation": key_parts})
        case_key = _case_key({"case": key_parts, "classification": classification})
        evidence_refs = _candidate_evidence_refs(candidate)
        search_related = surface in {"search_request", "document_evaluation"} and (
            classification
            in {
                "search_recall_gap",
                "search_quality_gap",
                "table_recall_gap",
                "evaluation_query_failure",
            }
        )
        payloads.append(
            {
                "observation": {
                    "id": UUID(int=int(observation_key[:32], 16)),
                    "observation_key": observation_key,
                    "surface": surface,
                    "subject_kind": candidate.candidate_type,
                    "subject_id": subject_id,
                    "severity": "high"
                    if classification in {"table_recall_gap", "chat_grounding_failure"}
                    else "medium",
                    "failure_classification": classification,
                    "summary": candidate.reason,
                    "document_id": candidate.document_id,
                    "evaluation_id": candidate.evaluation_id,
                    "search_request_id": candidate.search_request_id,
                    "details": candidate.model_dump(mode="json"),
                    "evidence_refs": evidence_refs,
                },
                "case": {
                    "id": UUID(int=int(case_key[:32], 16)),
                    "case_key": case_key,
                    "surface": surface,
                    "severity": "high"
                    if classification in {"table_recall_gap", "chat_grounding_failure"}
                    else "medium",
                    "failure_classification": classification,
                    "problem_statement": (
                        f"{candidate.reason}: {candidate.query_text}"
                        if candidate.query_text
                        else candidate.reason
                    ),
                    "observed_behavior": candidate.reason,
                    "expected_behavior": (
                        f"Expected {candidate.expected_result_type or 'relevant'} evidence "
                        f"for query '{candidate.query_text}'."
                    ),
                    "diagnosis": None,
                    "document_id": candidate.document_id,
                    "evaluation_id": candidate.evaluation_id,
                    "search_request_id": candidate.search_request_id,
                    "recommended_next_actions": [
                        "inspect_eval_failure_case",
                        "triage_eval_failure_case",
                        "optimize_search_harness_from_case" if search_related else "human_review",
                    ],
                    "allowed_repair_surfaces": SEARCH_REPAIR_SURFACES if search_related else [],
                    "blocked_repair_surfaces": BLOCKED_REPAIR_SURFACES,
                    "evidence_refs": evidence_refs,
                    "verification_requirements": (
                        _verification_requirements_for_search_case() if search_related else {}
                    ),
                    "agent_task_payloads": {},
                    "details": {
                        "quality_candidate": candidate.model_dump(mode="json"),
                        "search_related": search_related,
                    },
                    "last_seen_at": now,
                },
            }
        )
    return payloads


def _quality_failure_payloads(session: Session, *, limit: int) -> list[dict]:
    failures = get_quality_failures(session)
    payloads: list[dict] = []
    for run_failure in failures.run_failures[:limit]:
        key_parts = {
            "source": "quality_run_failure",
            "document_id": str(run_failure.document_id),
            "run_id": str(run_failure.run_id),
            "failure_stage": run_failure.failure_stage,
            "error_message": run_failure.error_message,
        }
        observation_key = _case_key({"observation": key_parts})
        case_key = _case_key({"case": key_parts, "classification": "parser_validation_failure"})
        evidence_refs = [
            _evidence_ref(
                ref_kind="document_run_failure_artifact",
                api_path=f"/runs/{run_failure.run_id}/failure-artifact",
                summary="Run failure artifact for parser, persistence, or validation failure.",
                document_id=run_failure.document_id,
                run_id=run_failure.run_id,
            )
        ]
        payloads.append(
            {
                "observation": {
                    "id": UUID(int=int(observation_key[:32], 16)),
                    "observation_key": observation_key,
                    "surface": "document_evaluation",
                    "subject_kind": "run_failure",
                    "subject_id": run_failure.run_id,
                    "severity": "critical",
                    "failure_classification": "parser_validation_failure",
                    "summary": run_failure.error_message or "Document run failed.",
                    "document_id": run_failure.document_id,
                    "run_id": run_failure.run_id,
                    "details": run_failure.model_dump(mode="json"),
                    "evidence_refs": evidence_refs,
                },
                "case": {
                    "id": UUID(int=int(case_key[:32], 16)),
                    "case_key": case_key,
                    "surface": "document_evaluation",
                    "severity": "critical",
                    "failure_classification": "parser_validation_failure",
                    "problem_statement": run_failure.error_message or "Document run failed.",
                    "observed_behavior": run_failure.error_message or "Run did not complete.",
                    "expected_behavior": (
                        "Document run should validate and promote only after checks pass."
                    ),
                    "document_id": run_failure.document_id,
                    "run_id": run_failure.run_id,
                    "recommended_next_actions": ["inspect_eval_failure_case", "human_review"],
                    "allowed_repair_surfaces": [],
                    "blocked_repair_surfaces": BLOCKED_REPAIR_SURFACES,
                    "evidence_refs": evidence_refs,
                    "verification_requirements": {},
                    "agent_task_payloads": {},
                    "details": {"run_failure": run_failure.model_dump(mode="json")},
                },
            }
        )
    return payloads


def refresh_eval_failure_cases(
    session: Session,
    *,
    limit: int = 50,
    include_resolved: bool = False,
) -> EvalFailureCaseRefreshResponse:
    now = utcnow()
    payloads = [
        *_quality_candidate_payloads(session, limit=limit, include_resolved=include_resolved),
        *_quality_failure_payloads(session, limit=limit),
    ]
    cases: list[EvalFailureCase] = []
    observations: list[EvalObservation] = []
    for payload in payloads[:limit]:
        observation = _upsert_observation(session, payload["observation"], now=now)
        case_payload = dict(payload["case"])
        case_payload["source_observation_id"] = observation.id
        case = _upsert_case(session, case_payload, now=now)
        search_related = bool((case.details_json or {}).get("search_related"))
        case.agent_task_payloads_json = _default_task_payloads_for_case(
            case.id,
            search_related=search_related,
        )
        observations.append(observation)
        cases.append(case)

    open_count = session.scalar(
        select(func.count())
        .select_from(EvalFailureCase)
        .where(EvalFailureCase.status.in_(OPEN_CASE_STATUSES))
    )
    if open_count is None:
        open_count = len([case for case in cases if case.status in OPEN_CASE_STATUSES])
    return EvalFailureCaseRefreshResponse(
        refreshed_at=now,
        observation_count=len(observations),
        case_count=len(cases),
        open_case_count=int(open_count),
        cases=[_to_case_response(case) for case in cases],
    )


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
    case = get_eval_failure_case_row(session, case_id)
    observation = (
        session.get(EvalObservation, case.source_observation_id)
        if case.source_observation_id is not None
        else None
    )
    return EvalFailureCaseInspectionResponse(
        case=_to_case_response(case),
        observation=_to_observation_response(observation) if observation is not None else None,
        linked_evidence=_linked_evidence(session, case),
        recommended_workflow=_recommended_workflow(case),
    )


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


def get_eval_workbench(
    session: Session,
    *,
    limit: int = 25,
) -> EvalWorkbenchResponse:
    cases = list_eval_failure_cases(session, limit=limit)
    approval_queue = [
        case
        for case in list_eval_failure_cases(
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
