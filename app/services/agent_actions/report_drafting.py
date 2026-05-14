from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import (
    AgentTask,
)
from app.schemas.agent_task_reports import (
    DraftTechnicalReportTaskInput,
    DraftTechnicalReportTaskOutput,
    PrepareReportAgentHarnessTaskOutput,
    VerifyTechnicalReportTaskInput,
)
from app.services.agent_actions.report_context_pack import require_passed_context_pack_gate
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.agent_task_context import (
    resolve_required_dependency_task_output_context,
)
from app.services.agent_task_verifications import (
    create_agent_task_verification_record,
)
from app.services.evidence import (
    attach_artifact_to_evidence_export,
    attach_operator_run_to_evidence_export,
    persist_technical_report_evidence_export,
    persist_technical_report_evidence_manifest,
    technical_report_search_evidence_closure_payload,
)
from app.services.evidence_operator_runs import record_knowledge_operator_run
from app.services.storage import StorageService
from app.services.technical_reports import (
    apply_technical_report_claim_support_judgments,
    draft_technical_report,
    judge_technical_report_claim_support,
    verify_technical_report,
)


def draft_technical_report_executor(
    session: Session,
    task: AgentTask,
    payload: DraftTechnicalReportTaskInput,
) -> dict:
    harness_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
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
    harness_output = PrepareReportAgentHarnessTaskOutput.model_validate(harness_context.output)
    context_pack_gate = require_passed_context_pack_gate(
        session,
        harness_task_id=payload.target_task_id,
        harness_output=harness_output,
    )
    draft_payload = draft_technical_report(
        harness_output.harness.model_dump(mode="json"),
        harness_task_id=payload.target_task_id,
        generator_mode=payload.generator_mode,
        generator_model=payload.generator_model,
        llm_draft_markdown=payload.llm_draft_markdown,
    )
    draft_payload["llm_adapter_contract"] = {
        **(draft_payload.get("llm_adapter_contract") or {}),
        "context_pack_gate": {
            "verification_id": str(context_pack_gate.id),
            "verification_task_id": str(context_pack_gate.verification_task_id),
            "outcome": context_pack_gate.outcome,
            "context_pack_sha256": (context_pack_gate.details_json or {}).get(
                "context_pack_sha256"
            ),
            "release_readiness_summary": (
                ((context_pack_gate.details_json or {}).get("trace") or {}).get(
                    "release_readiness_summary"
                )
            ),
        },
    }
    storage_service = StorageService()
    markdown_path = storage_service.get_agent_task_dir(task.id) / "technical_report_draft.md"
    markdown_path.write_text(draft_payload["markdown"])
    draft_payload["markdown_path"] = str(markdown_path)
    support_judgments_payload = judge_technical_report_claim_support(draft_payload)
    support_operator_run = record_knowledge_operator_run(
        session,
        operator_kind="judge",
        operator_name="technical_report_claim_support_judge",
        operator_version="v1",
        agent_task_id=task.id,
        config={
            "judge_kind": support_judgments_payload.get("judge_kind"),
            "min_support_score": support_judgments_payload.get("min_support_score"),
        },
        input_payload={
            "target_task_id": str(payload.target_task_id),
            "harness_task_type": harness_context.task_type,
            "claim_count": len(draft_payload.get("claims") or []),
            "evidence_card_count": len(draft_payload.get("evidence_cards") or []),
            "claims": [
                {
                    "claim_id": claim.get("claim_id"),
                    "rendered_text": claim.get("rendered_text"),
                    "evidence_card_ids": claim.get("evidence_card_ids") or [],
                    "graph_edge_ids": claim.get("graph_edge_ids") or [],
                    "source_search_request_result_ids": (
                        claim.get("source_search_request_result_ids") or []
                    ),
                }
                for claim in draft_payload.get("claims") or []
            ],
        },
        output_payload=support_judgments_payload,
        metrics={
            "claim_count": support_judgments_payload.get("claim_count", 0),
            "supported_claim_count": support_judgments_payload.get(
                "supported_claim_count",
                0,
            ),
            "unsupported_claim_count": support_judgments_payload.get(
                "unsupported_claim_count",
                0,
            ),
            "insufficient_evidence_claim_count": support_judgments_payload.get(
                "insufficient_evidence_claim_count",
                0,
            ),
        },
        metadata={
            "audit_role": (
                "records deterministic claim-level support judgments before "
                "technical report evidence is frozen"
            ),
        },
        inputs=[
            {
                "input_kind": "technical_report_claims_pending_support_judgment",
                "source_table": "agent_tasks",
                "source_id": task.id,
                "payload": {
                    "claim_count": len(draft_payload.get("claims") or []),
                    "evidence_card_count": len(draft_payload.get("evidence_cards") or []),
                },
            }
        ],
        outputs=[
            {
                "output_kind": "technical_report_claim_support_judgments",
                "target_table": "technical_report_claims",
                "payload": {
                    "supported_claim_count": support_judgments_payload.get(
                        "supported_claim_count",
                        0,
                    ),
                    "unsupported_claim_count": support_judgments_payload.get(
                        "unsupported_claim_count",
                        0,
                    ),
                    "insufficient_evidence_claim_count": support_judgments_payload.get(
                        "insufficient_evidence_claim_count",
                        0,
                    ),
                },
            }
        ],
    )
    apply_technical_report_claim_support_judgments(
        draft_payload,
        support_judgments_payload,
        support_judge_run_id=support_operator_run.id if support_operator_run is not None else None,
    )
    evidence_export = persist_technical_report_evidence_export(
        session,
        draft_payload=draft_payload,
        agent_task_id=task.id,
    )
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="technical_report_draft",
        payload=draft_payload,
        storage_service=storage_service,
        filename="technical_report_draft.json",
    )
    attach_artifact_to_evidence_export(
        session,
        evidence_package_export_id=evidence_export.id,
        agent_task_artifact_id=artifact.id,
    )
    operator_run = record_knowledge_operator_run(
        session,
        operator_kind="generate",
        operator_name="technical_report_draft",
        operator_version="v1",
        agent_task_id=task.id,
        model_name=payload.generator_model,
        config={
            "generator_mode": payload.generator_mode,
            "llm_adapter_contract": draft_payload.get("llm_adapter_contract", {}),
        },
        input_payload={
            "target_task_id": str(payload.target_task_id),
            "harness_task_type": harness_context.task_type,
            "context_pack_gate_verification_id": str(context_pack_gate.id),
            "context_pack_gate_task_id": str(context_pack_gate.verification_task_id),
            "context_pack_sha256": (context_pack_gate.details_json or {}).get(
                "context_pack_sha256"
            ),
            "claim_contract_count": len(
                harness_output.harness.model_dump(mode="json").get("claim_contract") or []
            ),
        },
        output_payload={
            "artifact_id": str(artifact.id),
            "artifact_kind": artifact.artifact_kind,
            "artifact_path": artifact.storage_path,
            "claim_count": len(draft_payload.get("claims") or []),
            "blocked_claim_count": len(draft_payload.get("blocked_claims") or []),
            "evidence_package_export_id": str(evidence_export.id),
            "evidence_package_sha256": evidence_export.package_sha256,
        },
        metrics={
            "claim_count": len(draft_payload.get("claims") or []),
            "blocked_claim_count": len(draft_payload.get("blocked_claims") or []),
            "evidence_card_count": len(draft_payload.get("evidence_cards") or []),
            "claim_derivation_count": len(draft_payload.get("claim_derivations") or []),
        },
        metadata={
            "audit_role": "records the report generation activity and its source harness",
            "evidence_package_export_id": str(evidence_export.id),
        },
        inputs=[
            {
                "input_kind": "report_agent_harness",
                "source_table": "agent_tasks",
                "source_id": payload.target_task_id,
                "payload": {
                    "target_task_type": harness_context.task_type,
                    "context_pack_sha256": (context_pack_gate.details_json or {}).get(
                        "context_pack_sha256"
                    ),
                },
            },
            {
                "input_kind": "document_generation_context_pack_gate",
                "source_table": "agent_task_verifications",
                "source_id": context_pack_gate.id,
                "payload": {
                    "verification_task_id": str(context_pack_gate.verification_task_id),
                    "outcome": context_pack_gate.outcome,
                    "context_pack_sha256": (context_pack_gate.details_json or {}).get(
                        "context_pack_sha256"
                    ),
                },
            },
        ],
        outputs=[
            {
                "output_kind": "technical_report_draft",
                "target_table": "agent_task_artifacts",
                "target_id": artifact.id,
                "artifact_path": artifact.storage_path,
                "payload": {
                    "claim_count": len(draft_payload.get("claims") or []),
                    "markdown_path": draft_payload.get("markdown_path"),
                    "evidence_package_sha256": evidence_export.package_sha256,
                },
            }
        ],
    )
    if operator_run is not None:
        attach_operator_run_to_evidence_export(
            session,
            evidence_package_export_id=evidence_export.id,
            operator_run_id=operator_run.id,
        )
    if support_operator_run is not None:
        attach_operator_run_to_evidence_export(
            session,
            evidence_package_export_id=evidence_export.id,
            operator_run_id=support_operator_run.id,
        )
    return {
        "draft": draft_payload,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
        "evidence_package_export_id": str(evidence_export.id),
        "evidence_package_sha256": evidence_export.package_sha256,
        "operator_run_id": str(operator_run.id) if operator_run is not None else None,
        "support_judge_run_id": str(support_operator_run.id)
        if support_operator_run is not None
        else None,
        "context_pack_evaluation_task_id": str(context_pack_gate.verification_task_id),
        "context_pack_verification_id": str(context_pack_gate.id),
        "context_pack_sha256": (context_pack_gate.details_json or {}).get("context_pack_sha256"),
    }


def verify_technical_report_executor(
    session: Session,
    task: AgentTask,
    payload: VerifyTechnicalReportTaskInput,
) -> dict:
    draft_context = resolve_required_dependency_task_output_context(
        session,
        task_id=task.id,
        depends_on_task_id=payload.target_task_id,
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
    draft_output = DraftTechnicalReportTaskOutput.model_validate(draft_context.output)
    draft_payload = draft_output.draft.model_dump(mode="json")
    draft_payload["llm_adapter_contract"] = {
        **(draft_payload.get("llm_adapter_contract") or {}),
        "harness_context_refs": [ref.model_dump(mode="json") for ref in draft_context.refs],
    }
    outcome = verify_technical_report(
        draft_payload,
        max_unsupported_claim_count=payload.max_unsupported_claim_count,
        require_full_claim_traceability=payload.require_full_claim_traceability,
        require_full_concept_coverage=payload.require_full_concept_coverage,
        require_graph_edges_approved=payload.require_graph_edges_approved,
        block_stale_context=payload.block_stale_context,
        require_claim_support_judgments=payload.require_claim_support_judgments,
        min_claim_support_score=payload.min_claim_support_score,
    )
    source_evidence_closure = technical_report_search_evidence_closure_payload(
        session,
        draft_payload,
    )
    summary = {
        **outcome.summary,
        "source_evidence_package_export_count": source_evidence_closure[
            "expected_source_evidence_package_export_count"
        ],
        "source_evidence_package_trace_complete_count": source_evidence_closure[
            "trace_complete_count"
        ],
        "source_evidence_package_trace_incomplete_count": source_evidence_closure[
            "incomplete_trace_count"
        ],
        "claims_missing_source_evidence_package_export_count": source_evidence_closure[
            "claims_missing_source_evidence_package_export_count"
        ],
        "cited_cards_without_acceptable_source_evidence_match_count": (
            source_evidence_closure["cited_cards_without_acceptable_source_evidence_match_count"]
        ),
        "cited_cards_with_document_run_fallback_match_count": source_evidence_closure[
            "cited_cards_with_document_run_fallback_match_count"
        ],
        "cited_cards_without_recomputed_source_coverage_count": source_evidence_closure[
            "cited_cards_without_recomputed_source_coverage_count"
        ],
        "cited_cards_with_expected_record_without_recomputed_record_match_count": (
            source_evidence_closure[
                "cited_cards_with_expected_record_without_recomputed_record_match_count"
            ]
        ),
        "reported_recomputed_match_mismatch_count": source_evidence_closure[
            "reported_recomputed_match_mismatch_count"
        ],
        "source_record_recall": source_evidence_closure["source_record_recall"],
        "source_evidence_closure_complete": source_evidence_closure["complete"],
    }
    reasons = list(outcome.verification_reasons)
    if payload.require_frozen_source_evidence and not source_evidence_closure["complete"]:
        reasons.append(
            "Every generated claim must be backed by frozen search evidence packages "
            "with complete persisted trace integrity and source-record or page-span "
            "coverage."
        )
    verification_outcome = "failed" if reasons else "passed"
    success_metrics = [
        *outcome.success_metrics,
        {
            "metric_key": "source_evidence_closure",
            "stakeholder": "Luc Moreau / James Cheney",
            "passed": source_evidence_closure["complete"],
            "summary": (
                "Every generated claim is linked to frozen retrieval evidence with "
                "persisted trace integrity."
            ),
            "details": {
                "source_evidence_package_export_count": source_evidence_closure[
                    "expected_source_evidence_package_export_count"
                ],
                "trace_complete_count": source_evidence_closure["trace_complete_count"],
                "incomplete_trace_count": source_evidence_closure["incomplete_trace_count"],
                "weak_source_match_count": source_evidence_closure[
                    "cited_cards_without_acceptable_source_evidence_match_count"
                ],
                "recomputed_source_coverage_gap_count": source_evidence_closure[
                    "cited_cards_without_recomputed_source_coverage_count"
                ],
                "source_record_recall": source_evidence_closure["source_record_recall"],
            },
        },
    ]
    details = {
        **outcome.verification_details,
        "target_task_id": str(draft_context.task_id),
        "target_task_type": draft_context.task_type,
        "source_evidence_closure": source_evidence_closure,
    }
    record = create_agent_task_verification_record(
        session,
        target_task_id=draft_context.task_id,
        verification_task_id=task.id,
        verifier_type="technical_report_gate",
        outcome=verification_outcome,
        metrics=summary,
        reasons=reasons,
        details=details,
    )
    result = {
        "draft": draft_payload,
        "summary": summary,
        "success_metrics": success_metrics,
        "verification": record.model_dump(mode="json"),
    }
    artifact = create_agent_task_artifact(
        session,
        task_id=task.id,
        artifact_kind="technical_report_verification",
        payload=result,
        storage_service=StorageService(),
        filename="technical_report_verification.json",
    )
    operator_run = record_knowledge_operator_run(
        session,
        operator_kind="verify",
        operator_name="technical_report_gate",
        operator_version="v1",
        agent_task_id=task.id,
        config={
            **outcome.verification_details.get("thresholds", {}),
            "require_frozen_source_evidence": payload.require_frozen_source_evidence,
            "require_claim_support_judgments": payload.require_claim_support_judgments,
            "min_claim_support_score": payload.min_claim_support_score,
        },
        input_payload={
            "target_task_id": str(payload.target_task_id),
            "draft_task_type": draft_context.task_type,
            "claim_count": summary.get("claim_count", 0),
        },
        output_payload={
            "verification_id": str(record.verification_id),
            "verification_outcome": verification_outcome,
            "artifact_id": str(artifact.id),
            "artifact_kind": artifact.artifact_kind,
            "artifact_path": artifact.storage_path,
        },
        metrics=summary,
        metadata={
            "verification_outcome": verification_outcome,
            "audit_role": "records the verifier gate for a generated technical report",
        },
        inputs=[
            {
                "input_kind": "technical_report_draft",
                "source_table": "agent_tasks",
                "source_id": payload.target_task_id,
                "payload": {
                    "target_task_type": draft_context.task_type,
                    "context_ref_count": outcome.summary.get("context_ref_count", 0),
                },
            }
        ],
        outputs=[
            {
                "output_kind": "technical_report_verification",
                "target_table": "agent_task_verifications",
                "target_id": record.verification_id,
                "payload": {
                    "outcome": verification_outcome,
                    "reasons": reasons,
                },
            },
            {
                "output_kind": "technical_report_verification_artifact",
                "target_table": "agent_task_artifacts",
                "target_id": artifact.id,
                "artifact_path": artifact.storage_path,
                "payload": {"artifact_kind": artifact.artifact_kind},
            },
        ],
    )
    evidence_manifest = None
    if verification_outcome == "passed":
        evidence_manifest = persist_technical_report_evidence_manifest(
            session,
            task_id=task.id,
        )
    return {
        **result,
        "artifact_id": str(artifact.id),
        "artifact_kind": artifact.artifact_kind,
        "artifact_path": artifact.storage_path,
        "operator_run_id": str(operator_run.id) if operator_run is not None else None,
        "evidence_manifest_id": str(evidence_manifest.id)
        if evidence_manifest is not None
        else None,
        "evidence_manifest_sha256": evidence_manifest.manifest_sha256
        if evidence_manifest is not None
        else None,
    }
