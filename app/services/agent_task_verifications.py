from __future__ import annotations

from sqlalchemy.orm import Session

import app.services.agent_task_verifications_search_harness as search_harness_owner
import app.services.agent_task_verifications_semantics as semantics_owner
from app.db.public.agent_tasks import AgentTask
from app.schemas.agent_task_search_workflows import (
    VerifyDraftHarnessConfigTaskInput,
    VerifySearchHarnessEvaluationTaskInput,
)
from app.schemas.agent_task_semantic_generation import VerifySemanticGroundedDocumentTaskInput
from app.schemas.agent_task_semantics import VerifyDraftSemanticRegistryUpdateTaskInput
from app.schemas.search import SearchHarnessEvaluationResponse
from app.services.agent_task_verification_records import (
    count_agent_task_verifications,
    create_agent_task_verification_record,
    get_agent_task_verifications,
    list_agent_task_verifications,
)
from app.services.search_harness_evaluations import (
    evaluate_search_harness,
    get_search_harness_evaluation_detail,
)
from app.services.search_legibility import get_search_harness_descriptor
from app.services.search_release_gate import (
    SearchHarnessReleaseGateOutcome,
    evaluate_search_harness_release_gate,
    record_search_harness_release_gate,
)
from app.services.semantic_generation import verify_semantic_grounded_document
from app.services.semantics import preview_semantic_registry_update_for_document

VerificationOutcome = SearchHarnessReleaseGateOutcome

__all__ = [
    "VerificationOutcome",
    "count_agent_task_verifications",
    "create_agent_task_verification_record",
    "evaluate_search_harness_verification",
    "get_agent_task_verifications",
    "list_agent_task_verifications",
    "verify_draft_harness_config_task",
    "verify_draft_semantic_registry_update_task",
    "verify_search_harness_evaluation_task",
    "verify_semantic_grounded_document_task",
]


def evaluate_search_harness_verification(
    session: Session,
    evaluation: SearchHarnessEvaluationResponse,
    payload: VerifySearchHarnessEvaluationTaskInput,
) -> SearchHarnessReleaseGateOutcome:
    return evaluate_search_harness_release_gate(session, evaluation, payload)


def verify_search_harness_evaluation_task(
    session: Session,
    verification_task: AgentTask,
    payload: VerifySearchHarnessEvaluationTaskInput,
) -> dict:
    return search_harness_owner.verify_search_harness_evaluation_task(
        session,
        verification_task,
        payload,
        evaluate_verification_func=evaluate_search_harness_verification,
        get_evaluation_detail_func=get_search_harness_evaluation_detail,
        record_release_gate_func=record_search_harness_release_gate,
    )


def verify_draft_harness_config_task(
    session: Session,
    verification_task: AgentTask,
    payload: VerifyDraftHarnessConfigTaskInput,
) -> dict:
    return search_harness_owner.verify_draft_harness_config_task(
        session,
        verification_task,
        payload,
        evaluate_search_harness_func=evaluate_search_harness,
        evaluate_verification_func=evaluate_search_harness_verification,
        get_search_harness_descriptor_func=get_search_harness_descriptor,
    )


def verify_draft_semantic_registry_update_task(
    session: Session,
    verification_task: AgentTask,
    payload: VerifyDraftSemanticRegistryUpdateTaskInput,
) -> dict:
    return semantics_owner.verify_draft_semantic_registry_update_task(
        session,
        verification_task,
        payload,
        preview_registry_update_for_document_func=preview_semantic_registry_update_for_document,
    )


def verify_semantic_grounded_document_task(
    session: Session,
    verification_task: AgentTask,
    payload: VerifySemanticGroundedDocumentTaskInput,
) -> dict:
    return semantics_owner.verify_semantic_grounded_document_task(
        session,
        verification_task,
        payload,
        verify_grounded_document_func=verify_semantic_grounded_document,
    )
