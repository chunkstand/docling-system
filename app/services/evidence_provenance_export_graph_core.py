from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.json_utils import json_object_payload as _json_payload
from app.services.evidence_constants import (
    TECHNICAL_REPORT_RELEASE_READINESS_DB_GATE_SCHEMA,
    TECHNICAL_REPORT_RELEASE_READINESS_DB_GATES_TABLE,
)
from app.services.evidence_manifests import (
    get_agent_task_evidence_manifest,
    get_agent_task_evidence_trace,
)
from app.services.evidence_provenance import (
    prov_export_integrity_payload as _prov_export_integrity_payload,
)
from app.services.evidence_provenance import (
    prov_identifier as _prov_identifier,
)
from app.services.evidence_provenance_export_graph_contracts import (
    JsonDict,
    ProvenanceGraphContext,
    ProvenanceGraphState,
)
from app.services.evidence_provenance_export_graph_report import populate_report_graph


def build_agent_task_provenance_export(session: Session, task_id: UUID) -> JsonDict:
    manifest = get_agent_task_evidence_manifest(session, task_id)
    trace = get_agent_task_evidence_trace(session, task_id)
    context = _build_context(manifest, trace)
    state = ProvenanceGraphState.new()

    _populate_manifest_roots(state, context)
    _populate_context_pack_graph(state, context)
    _populate_source_material_graph(state, context)

    populate_report_graph(state, context)
    return _finalize_provenance_export(state, context)


def _build_context(manifest: JsonDict, trace: JsonDict) -> ProvenanceGraphContext:
    report_trace = dict(manifest.get("report_trace") or {})
    context_pack_audit = dict(report_trace.get("context_pack_audit") or {})
    release_readiness_db_gate = dict(context_pack_audit.get("release_readiness_db_gate") or {})
    release_readiness_db_gate_record = dict(
        context_pack_audit.get("release_readiness_db_gate_record") or {}
    )
    release_readiness_db_gate_table = (
        TECHNICAL_REPORT_RELEASE_READINESS_DB_GATES_TABLE
        if release_readiness_db_gate_record.get("gate_id")
        else TECHNICAL_REPORT_RELEASE_READINESS_DB_GATE_SCHEMA
    )
    release_readiness_db_gate_id = (
        release_readiness_db_gate_record.get("gate_id")
        or release_readiness_db_gate.get("verification_id")
    )
    return ProvenanceGraphContext(
        manifest=manifest,
        trace=trace,
        report_trace=report_trace,
        retrieval_evaluation=dict(
            (manifest.get("retrieval_trace") or {}).get("source_evidence_closure") or {}
        ),
        context_pack_audit=context_pack_audit,
        release_readiness_db_gate=release_readiness_db_gate,
        release_readiness_db_gate_record=release_readiness_db_gate_record,
        release_readiness_db_gate_entity_id=_prov_identifier(
            release_readiness_db_gate_table,
            release_readiness_db_gate_id,
        ),
        manifest_entity_id=_prov_identifier(
            "evidence_manifests",
            manifest.get("evidence_manifest_id"),
        ),
        trace_entity_id=_prov_identifier("evidence_traces", manifest.get("evidence_manifest_id")),
        harness_activity_id=_prov_identifier(
            "agent_tasks",
            context_pack_audit.get("harness_task_id"),
        ),
        verification_activity_id=_prov_identifier(
            "agent_tasks",
            (manifest.get("verification_task") or {}).get("task_id"),
        ),
    )


def _populate_manifest_roots(state: ProvenanceGraphState, context: ProvenanceGraphContext) -> None:
    state.add_entity(
        context.manifest_entity_id,
        label="Technical report evidence manifest",
        entity_type="docling:TechnicalReportEvidenceManifest",
        **{
            "docling:manifest_sha256": context.manifest.get("manifest_sha256"),
            "docling:trace_sha256": context.manifest.get("trace_sha256"),
            "docling:manifest_kind": context.manifest.get("manifest_kind"),
        },
    )
    state.add_entity(
        context.trace_entity_id,
        label="Technical report evidence trace",
        entity_type="docling:TechnicalReportEvidenceTrace",
        **{"docling:trace_sha256": context.trace.get("trace_sha256")},
    )

    for task_key in ("task", "draft_task", "verification_task"):
        task = context.manifest.get(task_key) or {}
        activity_id = _prov_identifier("agent_tasks", task.get("task_id"))
        state.add_activity(
            activity_id,
            label=str(task.get("task_type") or task_key),
            activity_type="docling:AgentTask",
            started_at=task.get("created_at"),
            ended_at=task.get("completed_at") or task.get("updated_at"),
            **{
                "docling:task_type": task.get("task_type"),
                "docling:status": task.get("status"),
                "docling:workflow_version": task.get("workflow_version"),
            },
        )
        state.add_associated(activity=activity_id, agent="docling:agent/docling-system")
    state.add_generated(
        entity=context.manifest_entity_id,
        activity=context.verification_activity_id,
    )
    state.add_generated(
        entity=context.trace_entity_id,
        activity=context.verification_activity_id,
    )
    state.add_associated(
        activity=context.verification_activity_id,
        agent="docling:agent/technical-report-gate",
    )


def _populate_context_pack_graph(
    state: ProvenanceGraphState,
    context: ProvenanceGraphContext,
) -> None:
    if context.harness_activity_id:
        state.add_activity(
            context.harness_activity_id,
            label="prepare_report_agent_harness",
            activity_type="docling:AgentTask",
            **{"docling:task_type": "prepare_report_agent_harness"},
        )
        state.add_associated(
            activity=context.harness_activity_id,
            agent="docling:agent/docling-system",
        )
    for eval_task_id in context.context_pack_audit.get("evaluation_task_ids") or []:
        activity_id = _prov_identifier("agent_tasks", eval_task_id)
        state.add_activity(
            activity_id,
            label="evaluate_document_generation_context_pack",
            activity_type="docling:ContextPackEvaluationTask",
            **{"docling:task_type": "evaluate_document_generation_context_pack"},
        )
        state.add_associated(activity=activity_id, agent="docling:agent/context-pack-gate")

    for artifact in context.context_pack_audit.get("context_pack_artifacts") or []:
        entity_id = _prov_identifier("agent_task_artifacts", artifact.get("artifact_id"))
        state.add_entity(
            entity_id,
            label="Document generation context pack",
            entity_type="docling:DocumentGenerationContextPack",
            **{
                "docling:artifact_kind": artifact.get("artifact_kind"),
                "docling:payload_sha256": artifact.get("payload_sha256"),
                "docling:context_pack_sha256": (
                    context.context_pack_audit.get("context_pack_sha256s") or [None]
                )[0],
            },
        )
        state.add_generated(entity=entity_id, activity=context.harness_activity_id)

    for artifact in context.context_pack_audit.get("evaluation_artifacts") or []:
        entity_id = _prov_identifier("agent_task_artifacts", artifact.get("artifact_id"))
        eval_activity_id = _prov_identifier("agent_tasks", artifact.get("task_id"))
        state.add_entity(
            entity_id,
            label="Document generation context-pack evaluation",
            entity_type="docling:DocumentGenerationContextPackEvaluation",
            **{
                "docling:artifact_kind": artifact.get("artifact_kind"),
                "docling:payload_sha256": artifact.get("payload_sha256"),
            },
        )
        state.add_generated(entity=entity_id, activity=eval_activity_id)

    for verification in context.context_pack_audit.get("verifications") or []:
        entity_id = _prov_identifier(
            "agent_task_verifications",
            verification.get("verification_id"),
        )
        eval_activity_id = _prov_identifier("agent_tasks", verification.get("verification_task_id"))
        state.add_entity(
            entity_id,
            label="Document generation context-pack verifier record",
            entity_type="docling:ContextPackVerificationRecord",
            **{
                "docling:outcome": verification.get("outcome"),
                "docling:context_pack_sha256": (verification.get("details") or {}).get(
                    "context_pack_sha256"
                ),
            },
        )
        state.add_generated(entity=entity_id, activity=eval_activity_id)
        for artifact in context.context_pack_audit.get("context_pack_artifacts") or []:
            state.add_used(
                activity=eval_activity_id,
                entity=_prov_identifier("agent_task_artifacts", artifact.get("artifact_id")),
            )
    if context.release_readiness_db_gate_entity_id:
        db_gate_verification_id = context.release_readiness_db_gate.get("verification_id")
        db_gate_eval_activity_id = _prov_identifier(
            "agent_tasks",
            context.release_readiness_db_gate.get("verification_task_id")
            or context.release_readiness_db_gate_record.get("source_verification_task_id"),
        )
        state.add_entity(
            context.release_readiness_db_gate_entity_id,
            label="Release readiness DB gate summary",
            entity_type="docling:ReleaseReadinessDbGate",
            **{
                "docling:check_key": context.release_readiness_db_gate.get("check_key"),
                "docling:passed": context.release_readiness_db_gate.get("passed"),
                "docling:required": context.release_readiness_db_gate.get("required"),
                "docling:complete": context.release_readiness_db_gate.get("complete"),
                "docling:failure_count": context.release_readiness_db_gate.get("failure_count"),
                "docling:source_search_request_count": context.release_readiness_db_gate.get(
                    "source_search_request_count"
                ),
                "docling:verified_request_count": context.release_readiness_db_gate.get(
                    "verified_request_count"
                ),
                "docling:gate_id": context.release_readiness_db_gate_record.get("gate_id"),
                "docling:source_verification_id": (
                    context.release_readiness_db_gate_record.get("source_verification_id")
                    or db_gate_verification_id
                ),
                "docling:gate_payload_sha256": (
                    context.release_readiness_db_gate_record.get("gate_payload_sha256")
                    or context.release_readiness_db_gate.get("gate_payload_sha256")
                ),
                "docling:evidence_manifest_id": context.release_readiness_db_gate_record.get(
                    "evidence_manifest_id"
                ),
                "docling:prov_export_artifact_id": context.release_readiness_db_gate_record.get(
                    "prov_export_artifact_id"
                ),
                "docling:semantic_governance_event_id": (
                    context.release_readiness_db_gate_record.get("semantic_governance_event_id")
                ),
            },
        )
        state.add_generated(
            entity=context.release_readiness_db_gate_entity_id,
            activity=db_gate_eval_activity_id,
        )
        for verification in context.context_pack_audit.get("verifications") or []:
            verification_id = verification.get("verification_id")
            if str(verification_id) != str(db_gate_verification_id):
                continue
            state.add_derived(
                generated_entity=context.release_readiness_db_gate_entity_id,
                used_entity=_prov_identifier("agent_task_verifications", verification_id),
                **{
                    "docling:edge_type": (
                        "context_pack_verifier_record_to_release_readiness_db_gate"
                    ),
                },
            )

    for readiness_ref in context.context_pack_audit.get("release_readiness_assessments") or []:
        entity_id = _prov_identifier(
            "search_harness_release_readiness_assessments",
            readiness_ref.get("assessment_id"),
        )
        if entity_id is None:
            continue
        state.add_entity(
            entity_id,
            label="Search harness release readiness assessment",
            entity_type="docling:SearchHarnessReleaseReadinessAssessment",
            **{
                "docling:search_harness_release_id": readiness_ref.get(
                    "search_harness_release_id"
                ),
                "docling:harness_name": readiness_ref.get("harness_name"),
                "docling:readiness_status": readiness_ref.get("readiness_status"),
                "docling:ready": readiness_ref.get("ready"),
                "docling:selection_status": readiness_ref.get("selection_status"),
                "docling:assessment_payload_sha256": readiness_ref.get(
                    "assessment_payload_sha256"
                ),
            },
        )
        state.add_used(activity=context.harness_activity_id, entity=entity_id)
        for eval_task_id in context.context_pack_audit.get("evaluation_task_ids") or []:
            state.add_used(activity=_prov_identifier("agent_tasks", eval_task_id), entity=entity_id)
        state.add_derived(
            generated_entity=context.release_readiness_db_gate_entity_id,
            used_entity=entity_id,
            **{
                "docling:edge_type": (
                    "release_readiness_assessment_to_release_readiness_db_gate"
                ),
            },
        )

    if context.verification_activity_id and context.release_readiness_db_gate_entity_id:
        state.add_used(
            activity=context.verification_activity_id,
            entity=context.release_readiness_db_gate_entity_id,
        )


def _populate_source_material_graph(
    state: ProvenanceGraphState,
    context: ProvenanceGraphContext,
) -> None:
    for document in context.manifest.get("source_documents") or []:
        entity_id = _prov_identifier("documents", document.get("id"))
        state.add_entity(
            entity_id,
            label=str(document.get("source_filename") or "source document"),
            entity_type="docling:SourceDocument",
            **{
                "docling:sha256": document.get("sha256"),
                "docling:source_filename": document.get("source_filename"),
                "docling:title": document.get("title"),
            },
        )
        state.add_attributed(entity=entity_id, agent="docling:agent/docling-system")

    for run in context.manifest.get("document_runs") or []:
        state.add_entity(
            _prov_identifier("document_runs", run.get("id")),
            label="Document run",
            entity_type="docling:DocumentRun",
            **{
                "docling:document_id": run.get("document_id"),
                "docling:validation_status": run.get("validation_status"),
                "docling:docling_json_sha256": (run.get("artifact_hashes") or {}).get(
                    "docling_json_sha256"
                ),
                "docling:document_yaml_sha256": (run.get("artifact_hashes") or {}).get(
                    "document_yaml_sha256"
                ),
            },
        )

    for source_record in context.manifest.get("source_records") or []:
        state.add_entity(
            _prov_identifier(source_record.get("source_table"), source_record.get("id")),
            label=str(source_record.get("source_type") or source_record.get("source_table")),
            entity_type="docling:SourceRecord",
            **{
                "docling:document_id": source_record.get("document_id"),
                "docling:run_id": source_record.get("run_id"),
                "docling:source_type": source_record.get("source_type"),
                "docling:source_snapshot_sha256": source_record.get("source_snapshot_sha256"),
            },
        )
def _finalize_provenance_export(
    state: ProvenanceGraphState,
    context: ProvenanceGraphContext,
) -> JsonDict:
    relation_count = (
        len(state.was_generated_by)
        + len(state.used)
        + len(state.was_derived_from)
        + len(state.was_associated_with)
        + len(state.was_attributed_to)
    )
    prov_export = {
        "schema_name": "technical_report_prov_export",
        "schema_version": "1.0",
        "prov_compatibility": {
            "model": "W3C PROV-compatible JSON",
            "profile": "docling-system-technical-report-audit-v1",
        },
        "prefix": {
            "prov": "http://www.w3.org/ns/prov#",
            "docling": "https://docling-system.local/prov#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        },
        "entity": state.entities,
        "activity": state.activities,
        "agent": state.agents,
        "wasGeneratedBy": state.was_generated_by,
        "used": state.used,
        "wasDerivedFrom": state.was_derived_from,
        "wasAssociatedWith": state.was_associated_with,
        "wasAttributedTo": state.was_attributed_to,
        "retrieval_evaluation": context.retrieval_evaluation,
        "source_evidence_closure": context.retrieval_evaluation,
        "audit": {
            "manifest_sha256": context.manifest.get("manifest_sha256"),
            "trace_sha256": context.trace.get("trace_sha256"),
            "manifest_integrity": context.manifest.get("manifest_integrity"),
            "trace_integrity": context.trace.get("trace_integrity"),
            "audit_checklist": context.manifest.get("audit_checklist"),
            "release_readiness_db_gate": context.release_readiness_db_gate,
            "claim_retrieval_feedback_integrity": context.report_trace.get(
                "claim_retrieval_feedback_integrity"
            ),
        },
        "prov_summary": {
            "entity_count": len(state.entities),
            "activity_count": len(state.activities),
            "agent_count": len(state.agents),
            "was_generated_by_count": len(state.was_generated_by),
            "used_count": len(state.used),
            "was_derived_from_count": len(state.was_derived_from),
            "was_associated_with_count": len(state.was_associated_with),
            "was_attributed_to_count": len(state.was_attributed_to),
            "relation_count": relation_count,
            "retrieval_evaluation_complete": bool(context.retrieval_evaluation.get("complete")),
            "source_record_recall": context.retrieval_evaluation.get("source_record_recall"),
            "release_readiness_db_gate_complete": (
                context.release_readiness_db_gate.get("complete") is True
            ),
            "release_readiness_db_gate_failure_count": context.release_readiness_db_gate.get(
                "failure_count"
            ),
            "release_readiness_db_verified_request_count": (
                context.release_readiness_db_gate.get("verified_request_count")
            ),
            "release_readiness_db_source_search_request_count": (
                context.release_readiness_db_gate.get("source_search_request_count")
            ),
            "claim_retrieval_feedback_count": len(
                context.report_trace.get("claim_retrieval_feedback") or []
            ),
            "claim_retrieval_feedback_integrity_complete": bool(
                (context.report_trace.get("claim_retrieval_feedback_integrity") or {}).get(
                    "complete"
                )
            ),
        },
    }
    prov_export["prov_integrity"] = _prov_export_integrity_payload(prov_export)
    return _json_payload(prov_export)
