from __future__ import annotations

import uuid
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.core.hashes import payload_sha256
from app.core.time import utcnow
from app.db.public.agent_tasks import AgentTask, AgentTaskArtifact, AgentTaskVerification
from app.db.public.audit_and_evidence import (
    EvidenceManifest,
    TechnicalReportClaimRetrievalFeedback,
    TechnicalReportReleaseReadinessDbGate,
)
from app.db.public.retrieval import (
    SearchRequestRecord,
    SearchRequestResult,
    SearchRequestResultSpan,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.court_grade_readiness_bootstrap_support import (
    ClaimFeedbackExecution,
    ensure_bootstrap_result_span,
    execute_bootstrap_search,
    result_at_rank,
)
from app.services.evidence_constants import (
    RELEASE_READINESS_DB_GATE_CHECK_KEY,
    TECHNICAL_REPORT_EVIDENCE_MANIFEST_KIND,
)
from app.services.evidence_provenance import (
    TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
    TECHNICAL_REPORT_PROV_EXPORT_FILENAME,
)
from app.services.semantic_governance import (
    record_technical_report_claim_retrieval_feedback_event,
    record_technical_report_release_readiness_db_gate_event,
)
from app.services.storage import StorageService


def _draft_task_payload(executions: list[ClaimFeedbackExecution]) -> dict[str, Any]:
    claims: list[dict[str, Any]] = []
    for execution in executions:
        support_verdict = execution.seed["support_verdict"]
        feedback_status = execution.seed["feedback_status"]
        support_judgment: dict[str, Any] = {}
        if feedback_status == "contradicted":
            support_judgment = {
                "unsupported_reasons": ["evidence_contains_contradiction_cue"],
            }
        elif support_verdict == "insufficient_evidence":
            support_judgment = {"missing_reasons": ["bootstrap_missing_evidence"]}
        claims.append(
            {
                "claim_id": execution.seed["claim_id"],
                "rendered_text": execution.seed["claim_text"],
                "support_verdict": support_verdict,
                "support_score": execution.seed.get("support_score"),
                "support_judgment": support_judgment,
                "provenance_lock_sha256": str(
                    payload_sha256(
                        {
                            "claim_id": execution.seed["claim_id"],
                            "claim_text": execution.seed["claim_text"],
                            "query_text": execution.request.query_text,
                        }
                    )
                ),
                "support_judgment_sha256": str(payload_sha256(support_judgment)),
                "source_search_request_ids": [str(execution.request.id)],
                "source_search_request_result_ids": (
                    [str(execution.result.id)] if execution.result is not None else []
                ),
            }
        )
    return {
        "document_kind": "technical_report",
        "title": "Court-grade readiness bootstrap technical report feedback",
        "goal": "Seed deterministic claim-feedback lanes for readiness verification.",
        "claims": claims,
        "markdown": "\n".join(f"- {row['rendered_text']}" for row in claims),
    }


def _create_claim_feedback_tasks(
    session: Session,
    *,
    draft_payload: dict[str, Any],
) -> tuple[AgentTask, AgentTask, AgentTaskVerification]:
    now = utcnow()
    draft_task = AgentTask(
        id=uuid.uuid4(),
        task_type="draft_technical_report",
        status="completed",
        priority=100,
        side_effect_level="promotable",
        requires_approval=False,
        input_json={"source": "court_grade_readiness_bootstrap"},
        result_json={"payload": {"draft": draft_payload}},
        attempts=1,
        workflow_version="court_grade_readiness_bootstrap_v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    verification_task = AgentTask(
        id=uuid.uuid4(),
        task_type="verify_technical_report",
        status="completed",
        priority=100,
        side_effect_level="promotable",
        requires_approval=False,
        input_json={"target_task_id": str(draft_task.id)},
        result_json={"payload": {"verification": {"target_task_id": str(draft_task.id)}}},
        attempts=1,
        workflow_version="court_grade_readiness_bootstrap_v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    session.add_all([draft_task, verification_task])
    session.flush()

    request_ids = sorted(
        {
            request_id
            for claim in draft_payload.get("claims") or []
            for request_id in (claim.get("source_search_request_ids") or [])
        }
    )
    verification = AgentTaskVerification(
        id=uuid.uuid4(),
        target_task_id=draft_task.id,
        verification_task_id=verification_task.id,
        verifier_type="technical_report_gate",
        outcome="passed",
        metrics_json={
            "source_search_request_count": len(request_ids),
            "verified_request_count": len(request_ids),
        },
        reasons_json=[],
        details_json={
            "checks": [
                {
                    "check_key": RELEASE_READINESS_DB_GATE_CHECK_KEY,
                    "passed": True,
                    "required": True,
                    "observed": {
                        "complete": True,
                        "failure_count": 0,
                        "source_search_request_count": len(request_ids),
                        "verified_request_count": len(request_ids),
                        "verified_request_ids": request_ids,
                    },
                }
            ]
        },
        created_at=now,
        completed_at=now,
    )
    session.add(verification)
    session.flush()
    return draft_task, verification_task, verification


def _create_claim_feedback_manifest(
    session: Session,
    *,
    draft_task: AgentTask,
    verification_task: AgentTask,
    executions: list[ClaimFeedbackExecution],
) -> EvidenceManifest:
    claim_ids = [execution.seed["claim_id"] for execution in executions]
    search_request_ids = [str(execution.request.id) for execution in executions]
    run_ids = sorted(
        {
            str(execution.result.run_id)
            for execution in executions
            if execution.result is not None
        }
    )
    document_ids = sorted(
        {
            str(execution.result.document_id)
            for execution in executions
            if execution.result is not None
        }
    )
    payload = {
        "schema_name": "technical_report_court_evidence_seed_manifest",
        "schema_version": "1.0",
        "draft_task": {"task_id": str(draft_task.id)},
        "verification_task": {"task_id": str(verification_task.id)},
        "claim_ids": claim_ids,
        "search_request_ids": search_request_ids,
        "document_ids": document_ids,
        "run_ids": run_ids,
    }
    row = EvidenceManifest(
        id=uuid.uuid4(),
        manifest_kind=TECHNICAL_REPORT_EVIDENCE_MANIFEST_KIND,
        agent_task_id=verification_task.id,
        draft_task_id=draft_task.id,
        verification_task_id=verification_task.id,
        evidence_package_export_id=None,
        manifest_sha256=str(payload_sha256(payload)),
        trace_sha256=None,
        manifest_payload_json=payload,
        source_snapshot_sha256s_json=[],
        document_ids_json=document_ids,
        run_ids_json=run_ids,
        claim_ids_json=claim_ids,
        search_request_ids_json=search_request_ids,
        operator_run_ids_json=[],
        manifest_status="completed",
        created_at=utcnow(),
    )
    session.add(row)
    session.flush()
    return row


def _create_claim_feedback_prov_artifact(
    session: Session,
    *,
    verification_task: AgentTask,
    evidence_manifest: EvidenceManifest,
    executions: list[ClaimFeedbackExecution],
    storage_service: StorageService,
) -> AgentTaskArtifact:
    payload = {
        "schema_name": "technical_report_prov_export",
        "schema_version": "1.0",
        "artifact_kind": TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        "verification_task_id": str(verification_task.id),
        "evidence_manifest_id": str(evidence_manifest.id),
        "claim_ids": [execution.seed["claim_id"] for execution in executions],
        "source_search_request_ids": [str(execution.request.id) for execution in executions],
    }
    return create_agent_task_artifact(
        session,
        task_id=verification_task.id,
        artifact_kind=TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        payload=payload,
        storage_service=storage_service,
        filename=TECHNICAL_REPORT_PROV_EXPORT_FILENAME,
    )


def _release_gate_payload(
    *,
    verification: AgentTaskVerification,
    verification_task_id: uuid.UUID,
    source_search_request_ids: list[str],
) -> dict[str, Any]:
    summary = {
        "complete": True,
        "failure_count": 0,
        "source_search_request_count": len(source_search_request_ids),
        "verified_request_count": len(source_search_request_ids),
        "verified_request_ids": source_search_request_ids,
    }
    return {
        "schema_name": "technical_report_release_readiness_db_gate",
        "schema_version": "1.0",
        "check_key": RELEASE_READINESS_DB_GATE_CHECK_KEY,
        "verification_id": str(verification.id),
        "verification_task_id": str(verification_task_id),
        "passed": True,
        "required": True,
        "source_search_request_ids": source_search_request_ids,
        "source_search_request_count": len(source_search_request_ids),
        "verified_request_ids": source_search_request_ids,
        "verified_request_count": len(source_search_request_ids),
        "failure_count": 0,
        "missing_expected_request_ids": [],
        "unexpected_verified_request_ids": [],
        "coverage_complete": True,
        "summary": summary,
        "complete": True,
    }


def _create_claim_feedback_release_gate(
    session: Session,
    *,
    verification_task: AgentTask,
    verification: AgentTaskVerification,
    evidence_manifest: EvidenceManifest,
    prov_export_artifact: AgentTaskArtifact,
    executions: list[ClaimFeedbackExecution],
) -> TechnicalReportReleaseReadinessDbGate:
    request_ids = [str(execution.request.id) for execution in executions]
    gate_payload = _release_gate_payload(
        verification=verification,
        verification_task_id=verification_task.id,
        source_search_request_ids=request_ids,
    )
    now = utcnow()
    row = TechnicalReportReleaseReadinessDbGate(
        id=uuid.uuid4(),
        technical_report_verification_task_id=verification_task.id,
        source_verification_id=verification.id,
        source_verification_task_id=verification_task.id,
        harness_task_id=None,
        evidence_manifest_id=evidence_manifest.id,
        prov_export_artifact_id=prov_export_artifact.id,
        semantic_governance_event_id=None,
        check_key=RELEASE_READINESS_DB_GATE_CHECK_KEY,
        passed=True,
        required=True,
        coverage_complete=True,
        complete=True,
        source_search_request_count=len(request_ids),
        verified_request_count=len(request_ids),
        failure_count=0,
        source_search_request_ids_json=request_ids,
        verified_request_ids_json=request_ids,
        missing_expected_request_ids_json=[],
        unexpected_verified_request_ids_json=[],
        summary_json=gate_payload["summary"],
        gate_payload_json=gate_payload,
        gate_payload_sha256=str(payload_sha256(gate_payload)),
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.flush()
    event = record_technical_report_release_readiness_db_gate_event(session, gate=row)
    row.semantic_governance_event_id = event.id
    row.updated_at = utcnow()
    session.flush()
    return row


def _bootstrap_claim_feedback_evidence_refs(
    span: SearchRequestResultSpan | None,
    *,
    request: SearchRequestRecord,
    result: SearchRequestResult | None,
) -> list[dict[str, Any]]:
    if span is None or result is None:
        return []
    return [
        {
            "search_request_result_span_id": str(span.id),
            "search_request_id": str(request.id),
            "search_request_result_id": str(result.id),
            "retrieval_evidence_span_id": None,
            "span_rank": span.span_rank,
            "score_kind": span.score_kind,
            "score": span.score,
            "source_type": span.source_type,
            "source_id": str(span.source_id),
            "span_index": span.span_index,
            "page_from": span.page_from,
            "page_to": span.page_to,
            "text_excerpt": span.text_excerpt,
            "content_sha256": span.content_sha256,
            "source_snapshot_sha256": span.source_snapshot_sha256,
            "metadata": span.metadata_json or {},
        }
    ]


def _bootstrap_claim_feedback_retrieval_context(
    *,
    request: SearchRequestRecord,
    result: SearchRequestResult | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_name": "technical_report_claim_retrieval_context",
        "schema_version": "1.0",
        "primary_query_text": request.query_text,
        "primary_mode": request.mode,
        "primary_harness_name": request.harness_name,
        "primary_reranker_name": request.reranker_name,
        "primary_reranker_version": request.reranker_version,
        "primary_retrieval_profile_name": request.retrieval_profile_name,
        "primary_harness_config": request.harness_config_json or {},
        "requests": [
            {
                "search_request_id": str(request.id),
                "query_text": request.query_text,
                "mode": request.mode,
                "filters": request.filters_json or {},
                "limit": request.limit,
            }
        ],
        "results": [],
    }
    if result is not None:
        payload["results"].append(
            {
                "search_request_result_id": str(result.id),
                "search_request_id": str(request.id),
                "rank": result.rank,
                "result_type": result.result_type,
                "document_id": str(result.document_id),
                "run_id": str(result.run_id),
                "chunk_id": str(result.chunk_id) if result.chunk_id else None,
                "table_id": str(result.table_id) if result.table_id else None,
                "source_filename": result.source_filename,
                "preview_text": result.preview_text,
            }
        )
    return payload


def _create_claim_feedback_row(
    session: Session,
    *,
    verification_task: AgentTask,
    evidence_manifest: EvidenceManifest,
    prov_export_artifact: AgentTaskArtifact,
    release_gate: TechnicalReportReleaseReadinessDbGate,
    execution: ClaimFeedbackExecution,
) -> TechnicalReportClaimRetrievalFeedback:
    source_payload = {
        "schema_name": "technical_report_claim_retrieval_feedback_source",
        "schema_version": "1.0",
        "technical_report_verification_task_id": str(verification_task.id),
        "claim_id": execution.seed["claim_id"],
        "claim_text": execution.seed["claim_text"],
        "support_verdict": execution.seed["support_verdict"],
        "support_score": execution.seed.get("support_score"),
        "feedback_status": execution.seed["feedback_status"],
        "learning_label": execution.seed["learning_label"],
        "hard_negative_kind": execution.seed.get("hard_negative_kind"),
        "source_search_request_ids": [str(execution.request.id)],
        "source_search_request_result_ids": (
            [str(execution.result.id)] if execution.result is not None else []
        ),
        "search_request_result_span_ids": (
            [str(execution.span.id)] if execution.span is not None else []
        ),
        "retrieval_evidence_span_ids": [],
    }
    source_payload_sha256 = str(payload_sha256(source_payload))
    feedback_payload = {
        "schema_name": "technical_report_claim_retrieval_feedback",
        "schema_version": "1.0",
        "feedback_kind": "generation_claim_retrieval_feedback",
        "technical_report_verification_task_id": str(verification_task.id),
        "claim_id": execution.seed["claim_id"],
        "feedback_status": execution.seed["feedback_status"],
        "learning_label": execution.seed["learning_label"],
        "hard_negative_kind": execution.seed.get("hard_negative_kind"),
        "source_payload_sha256": source_payload_sha256,
        "source": source_payload,
    }
    now = utcnow()
    row = TechnicalReportClaimRetrievalFeedback(
        id=uuid.uuid4(),
        technical_report_verification_task_id=verification_task.id,
        claim_evidence_derivation_id=None,
        evidence_manifest_id=evidence_manifest.id,
        prov_export_artifact_id=prov_export_artifact.id,
        release_readiness_db_gate_id=release_gate.id,
        semantic_governance_event_id=None,
        claim_id=execution.seed["claim_id"],
        claim_text=execution.seed["claim_text"],
        support_verdict=execution.seed["support_verdict"],
        support_score=execution.seed.get("support_score"),
        feedback_status=execution.seed["feedback_status"],
        learning_label=execution.seed["learning_label"],
        hard_negative_kind=execution.seed.get("hard_negative_kind"),
        source_search_request_id=execution.request.id,
        search_request_result_id=execution.result.id if execution.result is not None else None,
        source_search_request_ids_json=[str(execution.request.id)],
        source_search_request_result_ids_json=(
            [str(execution.result.id)] if execution.result is not None else []
        ),
        search_request_result_span_ids_json=(
            [str(execution.span.id)] if execution.span is not None else []
        ),
        retrieval_evidence_span_ids_json=[],
        semantic_ontology_snapshot_ids_json=[],
        semantic_graph_snapshot_ids_json=[],
        retrieval_reranker_artifact_ids_json=[],
        search_harness_release_ids_json=[],
        release_audit_bundle_ids_json=[],
        release_validation_receipt_ids_json=[],
        evidence_refs_json=_bootstrap_claim_feedback_evidence_refs(
            execution.span,
            request=execution.request,
            result=execution.result,
        ),
        retrieval_context_json=_bootstrap_claim_feedback_retrieval_context(
            request=execution.request,
            result=execution.result,
        ),
        feedback_payload_json=feedback_payload,
        feedback_payload_sha256=str(payload_sha256(feedback_payload)),
        source_payload_json=source_payload,
        source_payload_sha256=source_payload_sha256,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.flush()
    event = record_technical_report_claim_retrieval_feedback_event(session, feedback=row)
    row.semantic_governance_event_id = event.id
    row.updated_at = utcnow()
    session.flush()
    return row


def seed_claim_feedback(
    session: Session,
    *,
    document_id: uuid.UUID,
    seed_rows: list[dict[str, Any]],
    storage_service: StorageService,
) -> dict[str, Any]:
    executions: list[ClaimFeedbackExecution] = []
    for seed in seed_rows:
        request, results = execute_bootstrap_search(
            session,
            query_text=seed["query_text"],
            mode=seed["mode"],
            document_id=document_id,
        )
        result = result_at_rank(
            results,
            result_rank=seed.get("result_rank"),
            query_text=seed["query_text"],
        )
        span = ensure_bootstrap_result_span(
            session, request=request, result=result
        ) if result else None
        executions.append(
            ClaimFeedbackExecution(
                seed=seed,
                request=request,
                result=result,
                span=span,
            )
        )

    draft_payload = _draft_task_payload(executions)
    draft_task, verification_task, verification = _create_claim_feedback_tasks(
        session,
        draft_payload=draft_payload,
    )
    evidence_manifest = _create_claim_feedback_manifest(
        session,
        draft_task=draft_task,
        verification_task=verification_task,
        executions=executions,
    )
    prov_export_artifact = _create_claim_feedback_prov_artifact(
        session,
        verification_task=verification_task,
        evidence_manifest=evidence_manifest,
        executions=executions,
        storage_service=storage_service,
    )
    release_gate = _create_claim_feedback_release_gate(
        session,
        verification_task=verification_task,
        verification=verification,
        evidence_manifest=evidence_manifest,
        prov_export_artifact=prov_export_artifact,
        executions=executions,
    )
    counts_by_status: Counter[str] = Counter()
    counts_by_label: Counter[str] = Counter()
    feedback_ids: list[str] = []
    for execution in executions:
        row = _create_claim_feedback_row(
            session,
            verification_task=verification_task,
            evidence_manifest=evidence_manifest,
            prov_export_artifact=prov_export_artifact,
            release_gate=release_gate,
            execution=execution,
        )
        feedback_ids.append(str(row.id))
        counts_by_status[row.feedback_status] += 1
        counts_by_label[row.learning_label] += 1

    session.flush()
    return {
        "created_rows": len(executions),
        "feedback_ids": feedback_ids,
        "verification_task_id": str(verification_task.id),
        "draft_task_id": str(draft_task.id),
        "verification_id": str(verification.id),
        "evidence_manifest_id": str(evidence_manifest.id),
        "prov_export_artifact_id": str(prov_export_artifact.id),
        "release_readiness_db_gate_id": str(release_gate.id),
        "counts_by_status": dict(sorted(counts_by_status.items())),
        "counts_by_learning_label": dict(sorted(counts_by_label.items())),
    }
