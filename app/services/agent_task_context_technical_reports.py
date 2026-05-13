from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.db.models import AgentTask, AgentTaskVerification
from app.schemas.agent_tasks import (
    BuildReportEvidenceCardsTaskOutput,
    ContextFreshnessStatus,
    ContextRef,
    DraftTechnicalReportTaskOutput,
    EvaluateClaimSupportJudgeTaskOutput,
    EvaluateDocumentGenerationContextPackTaskOutput,
    PlanTechnicalReportTaskOutput,
    PrepareReportAgentHarnessTaskOutput,
    TaskContextEnvelope,
    TaskContextSummary,
    VerifyTechnicalReportTaskOutput,
)
from app.services.agent_task_context_registry import (
    AgentTaskContextBuilder,
    resolve_context_builder_registry,
)
from app.services.agent_task_context_resolvers import (
    resolve_required_dependency_task_output_context,
)
from app.services.agent_task_context_store import (
    artifact_context_ref,
    derive_freshness_status,
    payload_sha256,
    task_output_context_ref,
    verification_payload,
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


def _build_plan_technical_report_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = PlanTechnicalReportTaskOutput.model_validate(payload)
    now = utcnow()
    refs: list[ContextRef] = []
    artifact_ref = artifact_context_ref(
        session,
        task=task,
        artifact_id=output.artifact_id,
        action=action,
        ref_key="technical_report_plan_artifact",
        summary="Persisted technical report plan and semantic source brief.",
        now=now,
    )
    if artifact_ref is not None:
        refs.append(artifact_ref)
    summary = TaskContextSummary(
        headline=(
            f"Planned technical report {output.plan.title!r} with "
            f"{len(output.plan.sections)} section(s)."
        ),
        goal="Turn the semantic dossier into a section, claim, graph, and retrieval plan.",
        decision="The report plan is ready for evidence-card construction.",
        next_action="Create build_report_evidence_cards to bind planned claims to evidence cards.",
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "section_count": len(output.plan.sections),
            "expected_claim_count": len(output.plan.expected_claims),
            "expected_graph_edge_count": len(output.plan.expected_graph_edge_ids),
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


def _build_build_report_evidence_cards_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = BuildReportEvidenceCardsTaskOutput.model_validate(payload)
    now = utcnow()
    plan_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.evidence_bundle.plan_task_id,
        dependency_kind="target_task",
        expected_task_type="plan_technical_report",
        expected_schema_name="plan_technical_report_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Evidence-card construction must declare the report plan as a target_task dependency."
        ),
        rerun_message=(
            "Technical report plan must be rerun after the context migration "
            "before evidence cards can be built."
        ),
    )
    refs: list[ContextRef] = [
        task_output_context_ref(
            ref_key="plan_task_output",
            summary="Typed technical report plan consumed by this evidence-card task.",
            context=plan_context,
            now=now,
        )
    ]
    artifact_ref = artifact_context_ref(
        session,
        task=task,
        artifact_id=output.artifact_id,
        action=action,
        ref_key="evidence_cards_artifact",
        summary="Persisted technical report evidence-card bundle.",
        now=now,
    )
    if artifact_ref is not None:
        refs.append(artifact_ref)
    summary = TaskContextSummary(
        headline=(
            f"Built {len(output.evidence_bundle.evidence_cards)} evidence card(s) "
            f"for {output.evidence_bundle.plan.title!r}."
        ),
        goal="Bind report claims to typed source evidence, facts, tables, and graph edges.",
        decision="Evidence cards are ready for wake-up harness packaging.",
        next_action="Create prepare_report_agent_harness to package the LLM wake-up context.",
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "evidence_card_count": len(output.evidence_bundle.evidence_cards),
            "claim_contract_count": len(output.evidence_bundle.claim_evidence_map),
            "graph_edge_count": len(output.evidence_bundle.graph_context),
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


def _build_prepare_report_agent_harness_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = PrepareReportAgentHarnessTaskOutput.model_validate(payload)
    now = utcnow()
    evidence_task_id = UUID(str(output.harness.workflow_state["evidence_task_id"]))
    evidence_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=evidence_task_id,
        dependency_kind="target_task",
        expected_task_type="build_report_evidence_cards",
        expected_schema_name="build_report_evidence_cards_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Report harness packaging must declare the evidence-card task "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Report evidence cards must be rerun after the context migration "
            "before harness packaging."
        ),
    )
    refs: list[ContextRef] = [
        task_output_context_ref(
            ref_key="evidence_cards_task_output",
            summary="Typed evidence-card bundle consumed by this report harness.",
            context=evidence_context,
            now=now,
        )
    ]
    artifact_ref = artifact_context_ref(
        session,
        task=task,
        artifact_id=output.artifact_id,
        action=action,
        ref_key="report_agent_harness_artifact",
        summary="LLM wake-up harness with tools, skills, evidence cards, and checks.",
        now=now,
    )
    if artifact_ref is not None:
        refs.append(artifact_ref)
    summary = TaskContextSummary(
        headline=(
            f"Prepared report wake-up harness for {output.harness.report_request['title']!r}."
        ),
        goal=(
            "Package the correct context, tools, skills, evidence, graph memory, and verifier gate."
        ),
        decision="The harness is ready for evaluate_document_generation_context_pack.",
        next_action=(
            "Create evaluate_document_generation_context_pack before rendering a report draft."
        ),
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "tool_count": len(output.harness.allowed_tools),
            "skill_count": len(output.harness.required_skills),
            "evidence_card_count": len(output.harness.evidence_cards),
            "claim_contract_count": len(output.harness.claim_contract),
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


def _build_evaluate_document_generation_context_pack_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = EvaluateDocumentGenerationContextPackTaskOutput.model_validate(payload)
    now = utcnow()
    harness_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.evaluation.target_task_id,
        dependency_kind="target_task",
        expected_task_type="prepare_report_agent_harness",
        expected_schema_name="prepare_report_agent_harness_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Context-pack evaluation must declare the report harness as a target_task dependency."
        ),
        rerun_message=(
            "Report harness must be rerun after the context-pack migration before evaluation."
        ),
    )
    refs: list[ContextRef] = [
        task_output_context_ref(
            ref_key="report_agent_harness_task_output",
            summary="Typed report harness consumed by this context-pack evaluation.",
            context=harness_context,
            now=now,
        )
    ]
    if output.context_pack_artifact_id is not None:
        context_pack_ref = artifact_context_ref(
            session,
            task=session.get(AgentTask, output.evaluation.target_task_id) or task,
            artifact_id=output.context_pack_artifact_id,
            action=action,
            ref_key="document_generation_context_pack_artifact",
            summary="Reusable document-generation context pack evaluated by this task.",
            now=now,
        )
        if context_pack_ref is not None:
            context_pack_ref.schema_name = "document_generation_context_pack"
            context_pack_ref.schema_version = output.context_pack.schema_version
            refs.append(context_pack_ref)
    verification_row = session.get(AgentTaskVerification, output.verification.verification_id)
    if verification_row is not None:
        refs.append(
            ContextRef(
                ref_key="verification_record",
                ref_kind="verification_record",
                summary="Verifier record persisted for the context-pack quality gate.",
                task_id=output.evaluation.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=payload_sha256(verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )
    artifact_ref = artifact_context_ref(
        session,
        task=task,
        artifact_id=output.artifact_id,
        action=action,
        ref_key="context_pack_evaluation_artifact",
        summary="Persisted pre-generation context-pack evaluation artifact.",
        now=now,
    )
    if artifact_ref is not None:
        refs.append(artifact_ref)

    gate_outcome = output.evaluation.gate_outcome
    summary = TaskContextSummary(
        headline=(
            f"Context pack evaluation {gate_outcome} with "
            f"{output.evaluation.summary.get('check_count', 0)} check(s)."
        ),
        goal="Evaluate the reusable generation context before any report draft is produced.",
        decision=(
            "The context pack is ready for draft_technical_report."
            if gate_outcome == "passed"
            else "The context pack has quality gaps that should be repaired before drafting."
        ),
        next_action=(
            "Create draft_technical_report from the evaluated report harness."
            if gate_outcome == "passed"
            else "Repair the report evidence cards or harness context and rerun evaluation."
        ),
        approval_state="not_required",
        verification_state=gate_outcome,
        problem="; ".join(output.evaluation.reasons) if output.evaluation.reasons else None,
        evidence=f"Context pack sha256: {output.evaluation.context_pack_sha256}",
        metrics={
            "gate_outcome": gate_outcome,
            "check_count": output.evaluation.summary.get("check_count"),
            "failed_check_count": output.evaluation.summary.get("failed_check_count"),
            "traceable_claim_ratio": output.evaluation.summary.get("traceable_claim_ratio"),
            "context_ref_count": output.evaluation.summary.get("context_ref_count"),
            "source_evidence_package_count": output.evaluation.summary.get(
                "source_evidence_package_count"
            ),
            "context_pack_sha256": output.evaluation.context_pack_sha256,
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


def _build_draft_technical_report_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = DraftTechnicalReportTaskOutput.model_validate(payload)
    now = utcnow()
    harness_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.draft.harness_task_id,
        dependency_kind="target_task",
        expected_task_type="prepare_report_agent_harness",
        expected_schema_name="prepare_report_agent_harness_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Technical report drafting must declare the report harness as a target_task dependency."
        ),
        rerun_message=(
            "Report agent harness must be rerun after the context migration before drafting."
        ),
    )
    refs: list[ContextRef] = [
        task_output_context_ref(
            ref_key="report_agent_harness_task_output",
            summary="Typed report wake-up harness consumed by this draft task.",
            context=harness_context,
            now=now,
        )
    ]
    artifact_ref = artifact_context_ref(
        session,
        task=task,
        artifact_id=output.artifact_id,
        action=action,
        ref_key="technical_report_draft_artifact",
        summary="Persisted technical report draft and markdown sidecar.",
        now=now,
    )
    if artifact_ref is not None:
        refs.append(artifact_ref)
    summary = TaskContextSummary(
        headline=(
            f"Drafted technical report {output.draft.title!r} with "
            f"{len(output.draft.claims)} claim(s)."
        ),
        goal="Render the report harness into a verification-ready technical report.",
        decision="Draft created and ready for technical report verification.",
        next_action="Create verify_technical_report to enforce evidence, graph, and context gates.",
        approval_state="not_required",
        verification_state="pending",
        metrics={
            "section_count": len(output.draft.sections),
            "claim_count": len(output.draft.claims),
            "blocked_claim_count": len(output.draft.blocked_claims),
            "generator_mode": output.draft.generator_mode,
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


def _build_verify_technical_report_context(
    session: Session,
    task: AgentTask,
    payload: dict,
    *,
    action,
) -> TaskContextEnvelope:
    output = VerifyTechnicalReportTaskOutput.model_validate(payload)
    now = utcnow()
    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=output.verification.target_task_id,
        dependency_kind="target_task",
        expected_task_type="draft_technical_report",
        expected_schema_name="draft_technical_report_output",
        expected_schema_version="1.0",
        dependency_error_message=(
            "Technical report verification must declare the report draft "
            "as a target_task dependency."
        ),
        rerun_message=(
            "Technical report draft must be rerun after the context migration before verification."
        ),
    )
    refs: list[ContextRef] = [
        task_output_context_ref(
            ref_key="technical_report_draft_task_output",
            summary="Typed technical report draft consumed by this verification task.",
            context=draft_context,
            now=now,
        )
    ]
    verification_row = session.get(AgentTaskVerification, output.verification.verification_id)
    if verification_row is not None:
        refs.append(
            ContextRef(
                ref_key="verification_record",
                ref_kind="verification_record",
                summary="Verifier record persisted for the technical report gate.",
                task_id=output.verification.target_task_id,
                verification_id=verification_row.id,
                observed_sha256=payload_sha256(verification_payload(verification_row)),
                source_updated_at=verification_row.completed_at or verification_row.created_at,
                checked_at=now,
                freshness_status=ContextFreshnessStatus.FRESH,
            )
        )
    artifact_ref = artifact_context_ref(
        session,
        task=task,
        artifact_id=output.artifact_id,
        action=action,
        ref_key="technical_report_verification_artifact",
        summary="Persisted technical report verification artifact.",
        now=now,
    )
    if artifact_ref is not None:
        refs.append(artifact_ref)
    summary = TaskContextSummary(
        headline=(
            f"Verified technical report {output.draft.title!r} with "
            f"{output.summary.get('claim_count', 0)} claim(s)."
        ),
        goal="Verify report claim traceability, graph approval, citations, and wake-up context.",
        decision=(
            "Verification passed; the technical report is ready for review."
            if output.verification.outcome == "passed"
            else "Verification failed; revise the technical report before review."
        ),
        next_action=(
            "Record an operator outcome or use the verified report downstream."
            if output.verification.outcome == "passed"
            else "Revise the draft or evidence harness and rerun verification."
        ),
        approval_state="not_required",
        verification_state=output.verification.outcome,
        metrics={
            "claim_count": output.summary.get("claim_count"),
            "unsupported_claim_count": output.summary.get("unsupported_claim_count"),
            "traceable_claim_ratio": output.summary.get("traceable_claim_ratio"),
            "context_blocker_count": output.summary.get("context_blocker_count"),
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
