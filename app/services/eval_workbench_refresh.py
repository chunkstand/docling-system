from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.services.eval_workbench as workbench_owners
from app.core.time import utcnow
from app.db.models import EvalFailureCase, EvalObservation
from app.schemas.eval_workbench import EvalFailureCaseRefreshResponse
from app.services.quality import get_quality_failures, list_quality_eval_candidates


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
            workbench_owners._evidence_ref(
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
            workbench_owners._evidence_ref(
                ref_kind="search_request_explanation",
                api_path=f"/search/requests/{candidate.search_request_id}/explain",
                summary="Persisted search request explanation for this quality gap.",
                search_request_id=candidate.search_request_id,
            )
        )
    if candidate.chat_answer_id is not None:
        refs.append(
            workbench_owners._evidence_ref(
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
        observation_key = workbench_owners._case_key({"observation": key_parts})
        case_key = workbench_owners._case_key({"case": key_parts, "classification": classification})
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
                    "allowed_repair_surfaces": (
                        workbench_owners.SEARCH_REPAIR_SURFACES if search_related else []
                    ),
                    "blocked_repair_surfaces": workbench_owners.BLOCKED_REPAIR_SURFACES,
                    "evidence_refs": evidence_refs,
                    "verification_requirements": (
                        workbench_owners._verification_requirements_for_search_case()
                        if search_related
                        else {}
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
        observation_key = workbench_owners._case_key({"observation": key_parts})
        case_key = workbench_owners._case_key(
            {"case": key_parts, "classification": "parser_validation_failure"}
        )
        evidence_refs = [
            workbench_owners._evidence_ref(
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
                    "blocked_repair_surfaces": workbench_owners.BLOCKED_REPAIR_SURFACES,
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
        case.agent_task_payloads_json = workbench_owners._default_task_payloads_for_case(
            case.id,
            search_related=search_related,
        )
        observations.append(observation)
        cases.append(case)

    open_count = session.scalar(
        select(func.count())
        .select_from(EvalFailureCase)
        .where(EvalFailureCase.status.in_(workbench_owners.OPEN_CASE_STATUSES))
    )
    if open_count is None:
        open_count = len(
            [case for case in cases if case.status in workbench_owners.OPEN_CASE_STATUSES]
        )
    return EvalFailureCaseRefreshResponse(
        refreshed_at=now,
        observation_count=len(observations),
        case_count=len(cases),
        open_case_count=int(open_count),
        cases=[workbench_owners._to_case_response(case) for case in cases],
    )
