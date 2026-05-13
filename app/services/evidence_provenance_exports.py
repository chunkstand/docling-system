# ruff: noqa: E501, F401, I001
from __future__ import annotations

import json
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AgentTaskArtifactImmutabilityEvent,
    EvidencePackageExport,
)
from app.services.evidence_audit_views import (
    persist_technical_report_release_readiness_db_gate,
)
from app.services.evidence_claim_feedback import (
    persist_technical_report_claim_retrieval_feedback_ledger,
)
from app.services.evidence_claim_support_impacts import (
    change_impact_payload as _change_impact_payload,
)
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import string_values as _string_values
from app.services.evidence_common import uuid_or_none_safe as _uuid_or_none_safe
from app.services.evidence_constants import (
    TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
    TECHNICAL_REPORT_RELEASE_READINESS_DB_GATES_TABLE,
    TECHNICAL_REPORT_RELEASE_READINESS_DB_GATE_SCHEMA,
)
from app.services.evidence_manifests import (
    existing_evidence_manifest as _existing_evidence_manifest,
    get_agent_task_evidence_manifest,
    get_agent_task_evidence_trace,
)
import app.services.evidence_provenance as _evidence_provenance

from app.services.evidence_provenance import (
    TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
    TECHNICAL_REPORT_PROV_EXPORT_FILENAME,
    add_prov_activity as _prov_activity,
    add_prov_entity as _prov_entity,
    add_prov_relation as _prov_relation,
    frozen_export_receipt as _frozen_export_receipt,
    frozen_export_sha256 as _frozen_export_sha256,
    prov_export_integrity_payload as _prov_export_integrity_payload,
    prov_identifier as _prov_identifier,
)
from app.services.evidence_technical_report_context import (
    draft_task_id_for_audit as _draft_task_id_for_audit,
    technical_report_upstream_task_ids as _technical_report_upstream_task_ids,
    verification_task_id_for_manifest as _verification_task_id_for_manifest,
)
from app.services.semantic_governance import (
    record_technical_report_prov_export_governance_event,
)
from app.services.storage import StorageService

def _build_agent_task_provenance_export(session: Session, task_id: UUID) -> dict[str, Any]:
    manifest = get_agent_task_evidence_manifest(session, task_id)
    trace = get_agent_task_evidence_trace(session, task_id)
    retrieval_evaluation = dict(
        (manifest.get("retrieval_trace") or {}).get("source_evidence_closure") or {}
    )

    entities: dict[str, dict[str, Any]] = {}
    activities: dict[str, dict[str, Any]] = {}
    agents: dict[str, dict[str, Any]] = {
        "docling:agent/docling-system": {
            "prov:type": "prov:SoftwareAgent",
            "prov:label": "Docling System",
        },
        "docling:agent/technical-report-gate": {
            "prov:type": "prov:SoftwareAgent",
            "prov:label": "Technical report verification gate",
        },
        "docling:agent/context-pack-gate": {
            "prov:type": "prov:SoftwareAgent",
            "prov:label": "Document generation context-pack gate",
        },
    }
    was_generated_by: dict[str, dict[str, Any]] = {}
    used: dict[str, dict[str, Any]] = {}
    was_derived_from: dict[str, dict[str, Any]] = {}
    was_associated_with: dict[str, dict[str, Any]] = {}
    was_attributed_to: dict[str, dict[str, Any]] = {}

    manifest_entity_id = _prov_identifier(
        "evidence_manifests",
        manifest.get("evidence_manifest_id"),
    )
    _prov_entity(
        entities,
        manifest_entity_id,
        label="Technical report evidence manifest",
        entity_type="docling:TechnicalReportEvidenceManifest",
        **{
            "docling:manifest_sha256": manifest.get("manifest_sha256"),
            "docling:trace_sha256": manifest.get("trace_sha256"),
            "docling:manifest_kind": manifest.get("manifest_kind"),
        },
    )
    trace_entity_id = _prov_identifier("evidence_traces", manifest.get("evidence_manifest_id"))
    _prov_entity(
        entities,
        trace_entity_id,
        label="Technical report evidence trace",
        entity_type="docling:TechnicalReportEvidenceTrace",
        **{"docling:trace_sha256": trace.get("trace_sha256")},
    )

    for task_key in ("task", "draft_task", "verification_task"):
        task = manifest.get(task_key) or {}
        task_id_value = task.get("task_id")
        activity_id = _prov_identifier("agent_tasks", task_id_value)
        _prov_activity(
            activities,
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
        _prov_relation(
            was_associated_with,
            "was-associated-with",
            sequence=len(was_associated_with) + 1,
            **{"prov:activity": activity_id, "prov:agent": "docling:agent/docling-system"},
        )

    report_trace = manifest.get("report_trace") or {}
    context_pack_audit = report_trace.get("context_pack_audit") or {}
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
    release_readiness_db_gate_entity_id = _prov_identifier(
        release_readiness_db_gate_table,
        release_readiness_db_gate_id,
    )
    harness_activity_id = _prov_identifier(
        "agent_tasks",
        context_pack_audit.get("harness_task_id"),
    )
    if harness_activity_id:
        _prov_activity(
            activities,
            harness_activity_id,
            label="prepare_report_agent_harness",
            activity_type="docling:AgentTask",
            **{"docling:task_type": "prepare_report_agent_harness"},
        )
        _prov_relation(
            was_associated_with,
            "was-associated-with",
            sequence=len(was_associated_with) + 1,
            **{"prov:activity": harness_activity_id, "prov:agent": "docling:agent/docling-system"},
        )
    for eval_task_id in context_pack_audit.get("evaluation_task_ids") or []:
        activity_id = _prov_identifier("agent_tasks", eval_task_id)
        _prov_activity(
            activities,
            activity_id,
            label="evaluate_document_generation_context_pack",
            activity_type="docling:ContextPackEvaluationTask",
            **{"docling:task_type": "evaluate_document_generation_context_pack"},
        )
        _prov_relation(
            was_associated_with,
            "was-associated-with",
            sequence=len(was_associated_with) + 1,
            **{"prov:activity": activity_id, "prov:agent": "docling:agent/context-pack-gate"},
        )
    for artifact in context_pack_audit.get("context_pack_artifacts") or []:
        entity_id = _prov_identifier("agent_task_artifacts", artifact.get("artifact_id"))
        _prov_entity(
            entities,
            entity_id,
            label="Document generation context pack",
            entity_type="docling:DocumentGenerationContextPack",
            **{
                "docling:artifact_kind": artifact.get("artifact_kind"),
                "docling:payload_sha256": artifact.get("payload_sha256"),
                "docling:context_pack_sha256": (
                    context_pack_audit.get("context_pack_sha256s") or [None]
                )[0],
            },
        )
        _prov_relation(
            was_generated_by,
            "was-generated-by",
            sequence=len(was_generated_by) + 1,
            **{"prov:entity": entity_id, "prov:activity": harness_activity_id},
        )
    for artifact in context_pack_audit.get("evaluation_artifacts") or []:
        entity_id = _prov_identifier("agent_task_artifacts", artifact.get("artifact_id"))
        eval_activity_id = _prov_identifier("agent_tasks", artifact.get("task_id"))
        _prov_entity(
            entities,
            entity_id,
            label="Document generation context-pack evaluation",
            entity_type="docling:DocumentGenerationContextPackEvaluation",
            **{
                "docling:artifact_kind": artifact.get("artifact_kind"),
                "docling:payload_sha256": artifact.get("payload_sha256"),
            },
        )
        _prov_relation(
            was_generated_by,
            "was-generated-by",
            sequence=len(was_generated_by) + 1,
            **{"prov:entity": entity_id, "prov:activity": eval_activity_id},
        )
    for verification in context_pack_audit.get("verifications") or []:
        entity_id = _prov_identifier(
            "agent_task_verifications",
            verification.get("verification_id"),
        )
        eval_activity_id = _prov_identifier("agent_tasks", verification.get("verification_task_id"))
        _prov_entity(
            entities,
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
        _prov_relation(
            was_generated_by,
            "was-generated-by",
            sequence=len(was_generated_by) + 1,
            **{"prov:entity": entity_id, "prov:activity": eval_activity_id},
        )
        for artifact in context_pack_audit.get("context_pack_artifacts") or []:
            context_entity_id = _prov_identifier(
                "agent_task_artifacts",
                artifact.get("artifact_id"),
            )
            _prov_relation(
                used,
                "used",
                sequence=len(used) + 1,
                **{"prov:activity": eval_activity_id, "prov:entity": context_entity_id},
            )
    if release_readiness_db_gate_entity_id:
        db_gate_verification_id = release_readiness_db_gate.get("verification_id")
        db_gate_eval_activity_id = _prov_identifier(
            "agent_tasks",
            release_readiness_db_gate.get("verification_task_id")
            or release_readiness_db_gate_record.get("source_verification_task_id"),
        )
        _prov_entity(
            entities,
            release_readiness_db_gate_entity_id,
            label="Release readiness DB gate summary",
            entity_type="docling:ReleaseReadinessDbGate",
            **{
                "docling:check_key": release_readiness_db_gate.get("check_key"),
                "docling:passed": release_readiness_db_gate.get("passed"),
                "docling:required": release_readiness_db_gate.get("required"),
                "docling:complete": release_readiness_db_gate.get("complete"),
                "docling:failure_count": release_readiness_db_gate.get("failure_count"),
                "docling:source_search_request_count": release_readiness_db_gate.get(
                    "source_search_request_count"
                ),
                "docling:verified_request_count": release_readiness_db_gate.get(
                    "verified_request_count"
                ),
                "docling:gate_id": release_readiness_db_gate_record.get("gate_id"),
                "docling:source_verification_id": release_readiness_db_gate_record.get(
                    "source_verification_id"
                )
                or db_gate_verification_id,
                "docling:gate_payload_sha256": (
                    release_readiness_db_gate_record.get("gate_payload_sha256")
                    or release_readiness_db_gate.get("gate_payload_sha256")
                ),
                "docling:evidence_manifest_id": release_readiness_db_gate_record.get(
                    "evidence_manifest_id"
                ),
                "docling:prov_export_artifact_id": release_readiness_db_gate_record.get(
                    "prov_export_artifact_id"
                ),
                "docling:semantic_governance_event_id": release_readiness_db_gate_record.get(
                    "semantic_governance_event_id"
                ),
            },
        )
        if db_gate_eval_activity_id:
            _prov_relation(
                was_generated_by,
                "was-generated-by",
                sequence=len(was_generated_by) + 1,
                **{
                    "prov:entity": release_readiness_db_gate_entity_id,
                    "prov:activity": db_gate_eval_activity_id,
                },
            )
        for verification in context_pack_audit.get("verifications") or []:
            verification_id = verification.get("verification_id")
            if str(verification_id) != str(db_gate_verification_id):
                continue
            verification_entity_id = _prov_identifier(
                "agent_task_verifications",
                verification_id,
            )
            if verification_entity_id:
                _prov_relation(
                    was_derived_from,
                    "was-derived-from",
                    sequence=len(was_derived_from) + 1,
                    **{
                        "prov:generatedEntity": release_readiness_db_gate_entity_id,
                        "prov:usedEntity": verification_entity_id,
                        "docling:edge_type": (
                            "context_pack_verifier_record_to_release_readiness_db_gate"
                        ),
                    },
                )
    for readiness_ref in context_pack_audit.get("release_readiness_assessments") or []:
        entity_id = _prov_identifier(
            "search_harness_release_readiness_assessments",
            readiness_ref.get("assessment_id"),
        )
        if entity_id is None:
            continue
        _prov_entity(
            entities,
            entity_id,
            label="Search harness release readiness assessment",
            entity_type="docling:SearchHarnessReleaseReadinessAssessment",
            **{
                "docling:search_harness_release_id": readiness_ref.get("search_harness_release_id"),
                "docling:harness_name": readiness_ref.get("harness_name"),
                "docling:readiness_status": readiness_ref.get("readiness_status"),
                "docling:ready": readiness_ref.get("ready"),
                "docling:selection_status": readiness_ref.get("selection_status"),
                "docling:assessment_payload_sha256": readiness_ref.get("assessment_payload_sha256"),
            },
        )
        if harness_activity_id:
            _prov_relation(
                used,
                "used",
                sequence=len(used) + 1,
                **{"prov:activity": harness_activity_id, "prov:entity": entity_id},
            )
        for eval_task_id in context_pack_audit.get("evaluation_task_ids") or []:
            eval_activity_id = _prov_identifier("agent_tasks", eval_task_id)
            _prov_relation(
                used,
                "used",
                sequence=len(used) + 1,
                **{"prov:activity": eval_activity_id, "prov:entity": entity_id},
            )
        if release_readiness_db_gate_entity_id:
            _prov_relation(
                was_derived_from,
                "was-derived-from",
                sequence=len(was_derived_from) + 1,
                **{
                    "prov:generatedEntity": release_readiness_db_gate_entity_id,
                    "prov:usedEntity": entity_id,
                    "docling:edge_type": (
                        "release_readiness_assessment_to_release_readiness_db_gate"
                    ),
                },
            )

    verification_activity_id = _prov_identifier(
        "agent_tasks",
        (manifest.get("verification_task") or {}).get("task_id"),
    )
    if verification_activity_id and release_readiness_db_gate_entity_id:
        _prov_relation(
            used,
            "used",
            sequence=len(used) + 1,
            **{
                "prov:activity": verification_activity_id,
                "prov:entity": release_readiness_db_gate_entity_id,
            },
        )
    _prov_relation(
        was_generated_by,
        "was-generated-by",
        sequence=len(was_generated_by) + 1,
        **{"prov:entity": manifest_entity_id, "prov:activity": verification_activity_id},
    )
    _prov_relation(
        was_generated_by,
        "was-generated-by",
        sequence=len(was_generated_by) + 1,
        **{"prov:entity": trace_entity_id, "prov:activity": verification_activity_id},
    )
    _prov_relation(
        was_associated_with,
        "was-associated-with",
        sequence=len(was_associated_with) + 1,
        **{
            "prov:activity": verification_activity_id,
            "prov:agent": "docling:agent/technical-report-gate",
        },
    )

    for document in manifest.get("source_documents") or []:
        entity_id = _prov_identifier("documents", document.get("id"))
        _prov_entity(
            entities,
            entity_id,
            label=str(document.get("source_filename") or "source document"),
            entity_type="docling:SourceDocument",
            **{
                "docling:sha256": document.get("sha256"),
                "docling:source_filename": document.get("source_filename"),
                "docling:title": document.get("title"),
            },
        )
        _prov_relation(
            was_attributed_to,
            "was-attributed-to",
            sequence=len(was_attributed_to) + 1,
            **{"prov:entity": entity_id, "prov:agent": "docling:agent/docling-system"},
        )

    for run in manifest.get("document_runs") or []:
        entity_id = _prov_identifier("document_runs", run.get("id"))
        _prov_entity(
            entities,
            entity_id,
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

    for source_record in manifest.get("source_records") or []:
        entity_id = _prov_identifier(source_record.get("source_table"), source_record.get("id"))
        _prov_entity(
            entities,
            entity_id,
            label=str(source_record.get("source_type") or source_record.get("source_table")),
            entity_type="docling:SourceRecord",
            **{
                "docling:document_id": source_record.get("document_id"),
                "docling:run_id": source_record.get("run_id"),
                "docling:source_type": source_record.get("source_type"),
                "docling:source_snapshot_sha256": source_record.get("source_snapshot_sha256"),
            },
        )

    report_trace = manifest.get("report_trace") or {}
    for export in report_trace.get("evidence_package_exports") or []:
        entity_id = _prov_identifier(
            "evidence_package_exports",
            export.get("evidence_package_export_id"),
        )
        _prov_entity(
            entities,
            entity_id,
            label=str(export.get("package_kind") or "evidence package export"),
            entity_type="docling:EvidencePackageExport",
            **{
                "docling:package_kind": export.get("package_kind"),
                "docling:package_sha256": export.get("package_sha256"),
                "docling:trace_sha256": export.get("trace_sha256"),
                "docling:search_request_id": export.get("search_request_id"),
            },
        )
        if export.get("search_request_id"):
            search_activity_id = _prov_identifier(
                "search_requests",
                export.get("search_request_id"),
            )
            _prov_activity(
                activities,
                search_activity_id,
                label="Search request",
                activity_type="docling:SearchRequest",
            )
            _prov_relation(
                was_generated_by,
                "was-generated-by",
                sequence=len(was_generated_by) + 1,
                **{"prov:entity": entity_id, "prov:activity": search_activity_id},
            )

    for card in report_trace.get("evidence_cards") or []:
        entity_id = _prov_identifier(
            "technical_report_evidence_cards",
            card.get("evidence_card_id"),
        )
        _prov_entity(
            entities,
            entity_id,
            label=str(card.get("evidence_card_id") or "evidence card"),
            entity_type="docling:TechnicalReportEvidenceCard",
            **{
                "docling:evidence_kind": card.get("evidence_kind"),
                "docling:source_type": card.get("source_type"),
                "docling:source_evidence_match_status": card.get("source_evidence_match_status"),
            },
        )

    for claim in report_trace.get("claims") or []:
        entity_id = _prov_identifier("technical_report_claims", claim.get("claim_id"))
        _prov_entity(
            entities,
            entity_id,
            label=str(claim.get("claim_id") or "technical report claim"),
            entity_type="docling:TechnicalReportClaim",
            **{
                "docling:claim_text": claim.get("rendered_text"),
                "docling:source_evidence_match_status": claim.get("source_evidence_match_status"),
            },
        )

    for feedback in report_trace.get("claim_retrieval_feedback") or []:
        entity_id = _prov_identifier(
            TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
            feedback.get("feedback_id"),
        )
        _prov_entity(
            entities,
            entity_id,
            label=str(feedback.get("claim_id") or "claim retrieval feedback"),
            entity_type="docling:ClaimRetrievalFeedback",
            **{
                "docling:claim_id": feedback.get("claim_id"),
                "docling:support_verdict": feedback.get("support_verdict"),
                "docling:support_score": feedback.get("support_score"),
                "docling:feedback_status": feedback.get("feedback_status"),
                "docling:learning_label": feedback.get("learning_label"),
                "docling:hard_negative_kind": feedback.get("hard_negative_kind"),
                "docling:feedback_payload_sha256": feedback.get("feedback_payload_sha256"),
                "docling:source_payload_sha256": feedback.get("source_payload_sha256"),
                "docling:evidence_manifest_id": feedback.get("evidence_manifest_id"),
                "docling:prov_export_artifact_id": feedback.get("prov_export_artifact_id"),
                "docling:release_readiness_db_gate_id": (
                    feedback.get("release_readiness_db_gate_id")
                ),
                "docling:semantic_governance_event_id": (
                    feedback.get("semantic_governance_event_id")
                ),
            },
        )
        if verification_activity_id:
            _prov_relation(
                was_generated_by,
                "was-generated-by",
                sequence=len(was_generated_by) + 1,
                **{"prov:entity": entity_id, "prov:activity": verification_activity_id},
            )
            _prov_relation(
                used,
                "used",
                sequence=len(used) + 1,
                **{"prov:activity": verification_activity_id, "prov:entity": entity_id},
            )
        claim_entity_id = _prov_identifier(
            "technical_report_claims",
            feedback.get("claim_id"),
        )
        if claim_entity_id:
            _prov_relation(
                was_derived_from,
                "was-derived-from",
                sequence=len(was_derived_from) + 1,
                **{
                    "prov:generatedEntity": entity_id,
                    "prov:usedEntity": claim_entity_id,
                    "docling:edge_type": "claim_to_retrieval_feedback",
                },
            )
        for result_id in feedback.get("source_search_request_result_ids") or []:
            result_entity_id = _prov_identifier("search_request_results", result_id)
            if result_entity_id:
                _prov_relation(
                    was_derived_from,
                    "was-derived-from",
                    sequence=len(was_derived_from) + 1,
                    **{
                        "prov:generatedEntity": entity_id,
                        "prov:usedEntity": result_entity_id,
                        "docling:edge_type": "search_result_to_claim_retrieval_feedback",
                    },
                )

    for derivation in report_trace.get("claim_derivations") or []:
        entity_id = _prov_identifier(
            "claim_evidence_derivations",
            derivation.get("claim_evidence_derivation_id"),
        )
        _prov_entity(
            entities,
            entity_id,
            label=str(derivation.get("claim_id") or "claim derivation"),
            entity_type="docling:ClaimEvidenceDerivation",
            **{"docling:derivation_sha256": derivation.get("derivation_sha256")},
        )

    for operator_run in report_trace.get("operator_runs") or []:
        activity_id = _prov_identifier(
            "knowledge_operator_runs",
            operator_run.get("operator_run_id"),
        )
        _prov_activity(
            activities,
            activity_id,
            label=str(operator_run.get("operator_name") or operator_run.get("operator_kind")),
            activity_type="docling:KnowledgeOperatorRun",
            started_at=operator_run.get("created_at"),
            **{
                "docling:operator_kind": operator_run.get("operator_kind"),
                "docling:operator_name": operator_run.get("operator_name"),
                "docling:operator_version": operator_run.get("operator_version"),
                "docling:status": operator_run.get("status"),
                "docling:config_sha256": operator_run.get("config_sha256"),
                "docling:input_sha256": operator_run.get("input_sha256"),
                "docling:output_sha256": operator_run.get("output_sha256"),
            },
        )
        _prov_relation(
            was_associated_with,
            "was-associated-with",
            sequence=len(was_associated_with) + 1,
            **{"prov:activity": activity_id, "prov:agent": "docling:agent/docling-system"},
        )

    for edge in manifest.get("provenance_edges") or []:
        from_ref = edge.get("from") or {}
        to_ref = edge.get("to") or {}
        from_id = _prov_identifier(
            from_ref.get("table"),
            from_ref.get("id") or from_ref.get("sha256"),
        )
        to_id = _prov_identifier(to_ref.get("table"), to_ref.get("id") or to_ref.get("sha256"))
        if from_id not in entities:
            _prov_entity(
                entities,
                from_id,
                label=str(from_ref.get("table") or "provenance source"),
                entity_type="docling:ProvenanceEndpoint",
                **{"docling:table": from_ref.get("table")},
            )
        if to_id not in entities:
            _prov_entity(
                entities,
                to_id,
                label=str(to_ref.get("table") or "provenance target"),
                entity_type="docling:ProvenanceEndpoint",
                **{"docling:table": to_ref.get("table")},
            )
        _prov_relation(
            was_derived_from,
            "was-derived-from",
            sequence=len(was_derived_from) + 1,
            **{
                "prov:generatedEntity": to_id,
                "prov:usedEntity": from_id,
                "docling:edge_type": edge.get("edge_type"),
            },
        )
        if verification_activity_id and from_id:
            _prov_relation(
                used,
                "used",
                sequence=len(used) + 1,
                **{"prov:activity": verification_activity_id, "prov:entity": from_id},
            )

    retrieval_complete = bool(retrieval_evaluation.get("complete"))
    relation_count = (
        len(was_generated_by)
        + len(used)
        + len(was_derived_from)
        + len(was_associated_with)
        + len(was_attributed_to)
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
        "entity": entities,
        "activity": activities,
        "agent": agents,
        "wasGeneratedBy": was_generated_by,
        "used": used,
        "wasDerivedFrom": was_derived_from,
        "wasAssociatedWith": was_associated_with,
        "wasAttributedTo": was_attributed_to,
        "retrieval_evaluation": retrieval_evaluation,
        "source_evidence_closure": retrieval_evaluation,
        "audit": {
            "manifest_sha256": manifest.get("manifest_sha256"),
            "trace_sha256": trace.get("trace_sha256"),
            "manifest_integrity": manifest.get("manifest_integrity"),
            "trace_integrity": trace.get("trace_integrity"),
            "audit_checklist": manifest.get("audit_checklist"),
            "release_readiness_db_gate": release_readiness_db_gate,
            "claim_retrieval_feedback_integrity": report_trace.get(
                "claim_retrieval_feedback_integrity"
            ),
        },
        "prov_summary": {
            "entity_count": len(entities),
            "activity_count": len(activities),
            "agent_count": len(agents),
            "was_generated_by_count": len(was_generated_by),
            "used_count": len(used),
            "was_derived_from_count": len(was_derived_from),
            "was_associated_with_count": len(was_associated_with),
            "was_attributed_to_count": len(was_attributed_to),
            "relation_count": relation_count,
            "retrieval_evaluation_complete": retrieval_complete,
            "source_record_recall": retrieval_evaluation.get("source_record_recall"),
            "release_readiness_db_gate_complete": release_readiness_db_gate.get("complete") is True,
            "release_readiness_db_gate_failure_count": release_readiness_db_gate.get(
                "failure_count"
            ),
            "release_readiness_db_verified_request_count": release_readiness_db_gate.get(
                "verified_request_count"
            ),
            "release_readiness_db_source_search_request_count": release_readiness_db_gate.get(
                "source_search_request_count"
            ),
            "claim_retrieval_feedback_count": len(
                report_trace.get("claim_retrieval_feedback") or []
            ),
            "claim_retrieval_feedback_integrity_complete": bool(
                (report_trace.get("claim_retrieval_feedback_integrity") or {}).get("complete")
            ),
        },
    }
    prov_export["prov_integrity"] = _prov_export_integrity_payload(prov_export)
    return _json_payload(prov_export)


def _existing_prov_export_artifact(
    session: Session,
    task_id: UUID,
) -> AgentTaskArtifact | None:
    return session.scalar(
        select(AgentTaskArtifact)
        .where(
            AgentTaskArtifact.task_id == task_id,
            AgentTaskArtifact.artifact_kind == TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        )
        .order_by(AgentTaskArtifact.created_at.asc())
        .limit(1)
    )


def _prov_export_receipt_signature(receipt_sha256: str) -> dict[str, Any]:
    return _evidence_provenance.prov_export_receipt_signature(
        receipt_sha256,
        settings_provider=get_settings,
    )


def _prov_export_receipt(
    prov_export: dict[str, Any],
    *,
    artifact_id: UUID,
    task_id: UUID,
    created_at: Any,
    storage_path: str | None,
    export_payload_sha256: str | None,
    prov_hash_basis_sha256: str | None,
) -> dict[str, Any]:
    return _evidence_provenance.prov_export_receipt(
        prov_export,
        artifact_id=artifact_id,
        task_id=task_id,
        created_at=created_at,
        storage_path=storage_path,
        export_payload_sha256=export_payload_sha256,
        prov_hash_basis_sha256=prov_hash_basis_sha256,
        settings_provider=get_settings,
    )


def _frozen_prov_export_payload(
    prov_export: dict[str, Any],
    *,
    artifact_id: UUID,
    task_id: UUID,
    created_at: Any,
    storage_path: str | None,
) -> dict[str, Any]:
    return _evidence_provenance.frozen_prov_export_payload(
        prov_export,
        artifact_id=artifact_id,
        task_id=task_id,
        created_at=created_at,
        storage_path=storage_path,
        settings_provider=get_settings,
    )


def _prov_export_receipt_integrity(payload: dict[str, Any] | None) -> dict[str, Any]:
    return _evidence_provenance.prov_export_receipt_integrity(
        payload,
        settings_provider=get_settings,
    )


def _record_prov_export_supersession_attempt(
    session: Session,
    *,
    existing: AgentTaskArtifact,
    attempted_prov_export: dict[str, Any],
) -> AgentTaskArtifactImmutabilityEvent | None:
    existing_payload = _json_payload(existing.payload_json or {})
    existing_sha256 = _frozen_export_sha256(existing_payload)
    attempted_sha256 = payload_sha256(attempted_prov_export)
    if existing_sha256 == attempted_sha256:
        return None

    duplicate = session.scalar(
        select(AgentTaskArtifactImmutabilityEvent)
        .where(
            AgentTaskArtifactImmutabilityEvent.artifact_id == existing.id,
            AgentTaskArtifactImmutabilityEvent.event_kind == "supersession_attempt",
            AgentTaskArtifactImmutabilityEvent.frozen_payload_sha256 == existing_sha256,
            AgentTaskArtifactImmutabilityEvent.attempted_payload_sha256 == attempted_sha256,
        )
        .limit(1)
    )
    if duplicate is not None:
        return duplicate

    existing_receipt = _frozen_export_receipt(existing_payload)
    event = AgentTaskArtifactImmutabilityEvent(
        artifact_id=existing.id,
        task_id=existing.task_id,
        event_kind="supersession_attempt",
        mutation_operation="FREEZE_REUSE",
        frozen_artifact_kind=existing.artifact_kind,
        attempted_artifact_kind=TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        frozen_storage_path=existing.storage_path,
        attempted_storage_path=existing.storage_path,
        frozen_payload_sha256=existing_sha256,
        attempted_payload_sha256=attempted_sha256,
        details_json={
            "reason": "A new PROV export was computed after the frozen artifact already existed.",
            "action": "kept_existing_frozen_artifact",
            "existing_receipt_sha256": existing_receipt.get("receipt_sha256"),
            "attempted_prov_hash_basis_sha256": (
                attempted_prov_export.get("prov_integrity") or {}
            ).get("prov_sha256"),
        },
        created_at=utcnow(),
    )
    session.add(event)
    session.flush()
    return event


def _technical_report_change_impact_for_governance(
    session: Session,
    verification_task_id: UUID,
) -> dict[str, Any]:
    verification_task = session.get(AgentTask, verification_task_id)
    if verification_task is None:
        return {
            "impacted": True,
            "impact_count": 1,
            "impacts": [
                {
                    "impact_type": "verification_task_missing",
                    "verification_task_id": str(verification_task_id),
                }
            ],
        }
    draft_task_id = _draft_task_id_for_audit(verification_task)
    draft_task = session.get(AgentTask, draft_task_id)
    draft_payload = (
        ((draft_task.result_json or {}).get("payload") or {}).get("draft") or {}
        if draft_task is not None
        else {}
    )
    related_task_ids = [
        draft_task_id,
        *_technical_report_upstream_task_ids(session, draft_payload),
        verification_task_id,
    ]
    related_task_ids = list(dict.fromkeys(related_task_ids))
    exports = list(
        session.scalars(
            select(EvidencePackageExport)
            .where(EvidencePackageExport.agent_task_id.in_(related_task_ids))
            .order_by(EvidencePackageExport.created_at.asc())
        )
    )
    return _change_impact_payload(session, exports)


def persist_agent_task_provenance_export(
    session: Session,
    *,
    task_id: UUID,
    storage_service: StorageService | None = None,
) -> AgentTaskArtifact:
    task = session.get(AgentTask, task_id)
    if task is None:
        raise ValueError(f"Agent task '{task_id}' was not found.")
    verification_task_id = _verification_task_id_for_manifest(session, task)
    governance_change_impact = _technical_report_change_impact_for_governance(
        session,
        verification_task_id,
    )
    existing = _existing_prov_export_artifact(session, verification_task_id)
    if existing is not None:
        attempted_prov_export = _build_agent_task_provenance_export(session, verification_task_id)
        _record_prov_export_supersession_attempt(
            session,
            existing=existing,
            attempted_prov_export=attempted_prov_export,
        )
        existing_manifest = _existing_evidence_manifest(session, verification_task_id)
        persist_technical_report_release_readiness_db_gate(
            session,
            verification_task_id=verification_task_id,
            evidence_manifest=existing_manifest,
            prov_export_artifact=existing,
        )
        persist_technical_report_claim_retrieval_feedback_ledger(
            session,
            verification_task_id=verification_task_id,
            evidence_manifest=existing_manifest,
            prov_export_artifact=existing,
            ensure_governance=True,
        )
        record_technical_report_prov_export_governance_event(
            session,
            artifact=existing,
            evidence_manifest=existing_manifest,
            change_impact=governance_change_impact,
        )
        return existing

    artifact_id = uuid.uuid4()
    created_at = utcnow()
    artifact_path = (
        storage_service.get_agent_task_dir(verification_task_id)
        / TECHNICAL_REPORT_PROV_EXPORT_FILENAME
        if storage_service is not None
        else None
    )
    storage_path = str(artifact_path) if artifact_path is not None else None
    prov_export = _build_agent_task_provenance_export(session, verification_task_id)
    frozen_payload = _frozen_prov_export_payload(
        prov_export,
        artifact_id=artifact_id,
        task_id=verification_task_id,
        created_at=created_at,
        storage_path=storage_path,
    )
    if artifact_path is not None:
        artifact_path.write_text(json.dumps(frozen_payload, indent=2, sort_keys=True))

    row = AgentTaskArtifact(
        id=artifact_id,
        task_id=verification_task_id,
        artifact_kind=TECHNICAL_REPORT_PROV_EXPORT_ARTIFACT_KIND,
        storage_path=storage_path,
        payload_json=frozen_payload,
        created_at=created_at,
    )
    session.add(row)
    session.flush()
    existing_manifest = _existing_evidence_manifest(session, verification_task_id)
    persist_technical_report_release_readiness_db_gate(
        session,
        verification_task_id=verification_task_id,
        evidence_manifest=existing_manifest,
        prov_export_artifact=row,
    )
    persist_technical_report_claim_retrieval_feedback_ledger(
        session,
        verification_task_id=verification_task_id,
        evidence_manifest=existing_manifest,
        prov_export_artifact=row,
        ensure_governance=True,
    )
    record_technical_report_prov_export_governance_event(
        session,
        artifact=row,
        evidence_manifest=existing_manifest,
        change_impact=governance_change_impact,
    )
    return row


def get_agent_task_provenance_export(
    session: Session,
    task_id: UUID,
    *,
    storage_service: StorageService | None = None,
) -> dict[str, Any]:
    artifact = persist_agent_task_provenance_export(
        session,
        task_id=task_id,
        storage_service=storage_service,
    )
    return _json_payload(artifact.payload_json or {})
