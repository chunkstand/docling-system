from __future__ import annotations

from app.hotspot_prevention_classifier_support import ClassifiedLine, blocked
from app.hotspot_prevention_diff import ChangedLine


def classify_agent_task_verifications_addition(
    *,
    stripped: str,
    line: ChangedLine,
) -> ClassifiedLine | None:
    lowered = stripped.lower()
    if any(
        token in stripped
        for token in (
            "evaluate_search_harness(",
            "get_search_harness_evaluation_detail",
            "record_search_harness_release_gate",
            "get_search_harness_descriptor",
            "evaluate_search_harness_verification",
            "repair_case",
            "SearchHarnessEvaluationRequest(",
            "SearchHarnessEvaluationResponse",
        )
    ) or any(token in lowered for token in ("release_gate", "harness_descriptor")):
        return blocked(
            line,
            "search_harness_verification_logic",
            "search-harness verification behavior belongs in "
            "app/services/agent_task_verifications_search_harness.py",
        )
    if any(
        token in stripped
        for token in (
            "preview_semantic_registry_update_for_document",
            "verify_semantic_grounded_document",
            "semantic_registry_verification_",
            "VerifyDraftSemanticRegistryUpdateTaskInput",
            "VerifySemanticGroundedDocumentTaskInput",
            "DraftSemanticGroundedDocumentTaskOutput",
            "DraftSemanticRegistryUpdateTaskOutput",
        )
    ) or any(token in lowered for token in ("semantic_registry", "grounded_document")):
        return blocked(
            line,
            "semantic_verification_logic",
            "semantic verification behavior belongs in "
            "app/services/agent_task_verifications_semantics.py",
        )
    if stripped.startswith(("def _", "async def _")):
        return blocked(
            line,
            "verification_helper",
            "new verification helpers belong in the focused verification owner modules",
        )
    if stripped.startswith(("def ", "async def ", "class ")):
        return blocked(
            line,
            "verification_orchestration",
            "new verification composition belongs in the focused verification owner modules",
        )
    return None


def classify_agent_task_worker_addition(
    *,
    stripped: str,
    line: ChangedLine,
) -> ClassifiedLine | None:
    lowered = stripped.lower()
    if any(
        token in stripped
        for token in (
            "claim_next_agent_task",
            "requeue_stale_agent_tasks",
            "heartbeat_agent_task",
            "agent_task_lease_heartbeat",
            "with_for_update(",
            "skip_locked",
            "locked_at",
            "locked_by",
            "last_heartbeat_at",
            "next_attempt_at",
            "worker_lease_timeout_seconds",
        )
    ) or "stale_lease" in lowered:
        return blocked(
            line,
            "lease_management_logic",
            "worker lease claim, heartbeat, and stale-requeue logic belongs in "
            "app/services/agent_task_worker_leases.py",
        )
    if any(
        token in stripped
        for token in (
            "finalize_agent_task_",
            "failure_artifact",
            "derive_attempt_cost",
            "derive_attempt_performance",
            "refresh_claim_support_policy_change_impacts_for_replay_task",
            "persist_agent_task_provenance_export",
            "refresh_technical_report_evidence_manifest",
            "PROMOTABLE_SIDE_EFFECT",
        )
    ) or any(token in lowered for token in ("promotable", "error_message", "result_json")):
        return blocked(
            line,
            "failure_retry_logic",
            "worker retry, checkpoint, and finalization logic belongs in "
            "app/services/agent_task_worker_finalization.py",
        )
    if stripped.startswith(("def _", "async def _")):
        return blocked(
            line,
            "worker_runtime_helper",
            "new worker helpers belong in the focused worker owner modules",
        )
    if stripped.startswith(("def ", "async def ", "class ")):
        return blocked(
            line,
            "worker_execution_orchestration",
            "new worker execution orchestration belongs in "
            "app/services/agent_task_worker_processing.py",
        )
    return None
