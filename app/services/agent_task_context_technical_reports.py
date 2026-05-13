from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import AgentTask
from app.schemas.agent_tasks import (
    ContextFreshnessStatus,
    EvaluateClaimSupportJudgeTaskOutput,
    TaskContextEnvelope,
    TaskContextSummary,
)
from app.services.agent_task_context_registry import (
    AgentTaskContextBuilder,
    resolve_context_builder_registry,
)
from app.services.agent_task_context_store import (
    artifact_context_ref,
    derive_freshness_status,
)

TECHNICAL_REPORT_CONTEXT_BUILDER_SYMBOLS = {
    "plan_technical_report": "_build_plan_technical_report_context",
    "build_report_evidence_cards": "_build_build_report_evidence_cards_context",
    "prepare_report_agent_harness": "_build_prepare_report_agent_harness_context",
    "evaluate_document_generation_context_pack": (
        "_build_evaluate_document_generation_context_pack_context"
    ),
    "draft_technical_report": "_build_draft_technical_report_context",
    "verify_technical_report": "_build_verify_technical_report_context",
    "evaluate_claim_support_judge": "_build_evaluate_claim_support_judge_context",
}


def _build_evaluate_claim_support_judge_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = EvaluateClaimSupportJudgeTaskOutput.model_validate(payload)
    now = utcnow()
    gate_outcome = str(output.summary.get("gate_outcome") or "unknown")
    gate_passed = gate_outcome == "passed"
    refs = []
    artifact_ref = artifact_context_ref(
        session,
        task=task,
        artifact_id=output.artifact_id,
        action=action,
        ref_key="claim_support_judge_evaluation_artifact",
        summary="Persisted claim support judge replay evaluation artifact.",
        now=now,
    )
    if artifact_ref is not None:
        refs.append(artifact_ref)
    summary = TaskContextSummary(
        headline=(
            f"Claim support judge evaluation {gate_outcome} with "
            f"{output.summary.get('case_count', 0)} replay case(s)."
        ),
        goal=(
            "Replay fixed hard-case fixtures to calibrate the technical report claim support judge."
        ),
        decision=(
            "Support judge calibration is ready for gated technical report verification."
            if gate_passed
            else "Support judge calibration failed; repair the judge or fixtures before promotion."
        ),
        next_action=(
            "Use verify_technical_report with support judgments enabled."
            if gate_passed
            else "Inspect failed case_results and rerun evaluate_claim_support_judge."
        ),
        approval_state="not_required",
        verification_state=gate_outcome,
        problem="; ".join(output.reasons) if output.reasons else None,
        evidence=(
            f"Fixture set sha256: {output.fixture_set_sha256}; "
            f"policy sha256: {output.policy_sha256 or 'unknown'}"
        ),
        metrics={
            "gate_outcome": gate_outcome,
            "case_count": output.summary.get("case_count"),
            "passed_case_count": output.summary.get("passed_case_count"),
            "failed_case_count": output.summary.get("failed_case_count"),
            "overall_accuracy": output.summary.get("overall_accuracy"),
            "fixture_set_id": str(output.fixture_set_id) if output.fixture_set_id else None,
            "fixture_set_sha256": output.fixture_set_sha256,
            "policy_id": str(output.policy_id) if output.policy_id else None,
            "policy_name": output.policy_name,
            "policy_version": output.policy_version,
            "policy_sha256": output.policy_sha256,
            "judge_version": output.judge_version,
        },
    )
    return TaskContextEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        task_status=task.status,
        workflow_version=task.workflow_version,
        generated_at=now,
        task_updated_at=task.updated_at,
        output_schema_name=action.output_schema_name,
        output_schema_version=action.output_schema_version,
        freshness_status=derive_freshness_status(refs) or ContextFreshnessStatus.FRESH,
        summary=summary,
        refs=refs,
        output=output.model_dump(mode="json"),
    )


def build_technical_report_context_builders(
    available_symbols: Mapping[str, object],
) -> dict[str, AgentTaskContextBuilder]:
    return resolve_context_builder_registry(
        {**dict(available_symbols), **globals()},
        builder_symbols=TECHNICAL_REPORT_CONTEXT_BUILDER_SYMBOLS,
        registry_name="technical_reports",
    )
