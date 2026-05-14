# ruff: noqa: E501, F401, I001
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import uuid_or_none as _uuid_or_none
from app.db.models import (
    ClaimEvidenceDerivation,
    DocumentChunk,
    DocumentFigure,
    DocumentTable,
    DocumentTableSegment,
    EvidencePackageExport,
    SemanticAssertion,
    SemanticAssertionEvidence,
    SemanticFact,
    SemanticFactEvidence,
)
from app.services.evidence_common import payload_sha256
from app.services.evidence_common import uuid_values as _uuid_values
from app.services.evidence_constants import (
    TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
    TECHNICAL_REPORT_RELEASE_READINESS_DB_GATES_TABLE,
)
from app.services.evidence_records import (
    chunk_payload as _chunk_payload,
    figure_payload as _figure_payload,
    select_by_ids as _select_by_ids,
    table_payload as _table_payload,
)
from app.services.evidence_release_readiness import (
    release_readiness_db_gate_trace_ref as _release_readiness_db_gate_trace_ref
)
from app.services.evidence_technical_report_exports import (
    claim_derivation_provenance_lock_contract_mismatches as _claim_derivation_provenance_lock_contract_mismatches,
    claim_derivation_support_judgment_contract_mismatches as _claim_derivation_support_judgment_contract_mismatches,
    evidence_card_snapshot as _evidence_card_snapshot,
    build_technical_report_derivation_package,
)

def _semantic_assertion_payload(row: SemanticAssertion) -> dict:
    return {
        "assertion_id": row.id,
        "semantic_pass_id": row.semantic_pass_id,
        "concept_id": row.concept_id,
        "assertion_kind": row.assertion_kind,
        "epistemic_status": row.epistemic_status,
        "context_scope": row.context_scope,
        "review_status": row.review_status,
        "matched_terms": row.matched_terms_json or [],
        "source_types": row.source_types_json or [],
        "evidence_count": row.evidence_count,
        "confidence": row.confidence,
        "details": row.details_json or {},
        "created_at": row.created_at,
    }


def _semantic_assertion_evidence_payload(row: SemanticAssertionEvidence) -> dict:
    return {
        "evidence_id": row.id,
        "assertion_id": row.assertion_id,
        "document_id": row.document_id,
        "run_id": row.run_id,
        "source_type": row.source_type,
        "source_locator": row.source_locator,
        "chunk_id": row.chunk_id,
        "table_id": row.table_id,
        "figure_id": row.figure_id,
        "page_from": row.page_from,
        "page_to": row.page_to,
        "matched_terms": row.matched_terms_json or [],
        "excerpt": row.excerpt,
        "source_label": row.source_label,
        "source_artifact_path": row.source_artifact_path,
        "source_artifact_sha256": row.source_artifact_sha256,
        "details": row.details_json or {},
        "created_at": row.created_at,
    }


def _semantic_fact_payload(row: SemanticFact) -> dict:
    return {
        "fact_id": row.id,
        "document_id": row.document_id,
        "run_id": row.run_id,
        "semantic_pass_id": row.semantic_pass_id,
        "ontology_snapshot_id": row.ontology_snapshot_id,
        "subject_entity_id": row.subject_entity_id,
        "relation_key": row.relation_key,
        "relation_label": row.relation_label,
        "object_entity_id": row.object_entity_id,
        "object_value_text": row.object_value_text,
        "source_assertion_id": row.source_assertion_id,
        "review_status": row.review_status,
        "confidence": row.confidence,
        "details": row.details_json or {},
        "created_at": row.created_at,
    }


def _semantic_fact_evidence_payload(row: SemanticFactEvidence) -> dict:
    return {
        "fact_evidence_id": row.id,
        "fact_id": row.fact_id,
        "assertion_id": row.assertion_id,
        "assertion_evidence_id": row.assertion_evidence_id,
        "created_at": row.created_at,
    }

def _technical_report_integrity_payload(
    draft_payload: dict[str, Any],
    exports: list[EvidencePackageExport],
    derivations: list[ClaimEvidenceDerivation],
) -> dict:
    from app.schemas.agent_task_reports import TechnicalReportDraftPayload

    canonical_draft_payload = (
        TechnicalReportDraftPayload.model_validate(draft_payload).model_dump(mode="json")
        if draft_payload
        else {}
    )
    recomputed_package = build_technical_report_derivation_package(canonical_draft_payload)
    expected_package_sha256 = str(recomputed_package.get("package_sha256") or "")
    expected_derivations_by_claim_id = {
        str(row.get("claim_id")): row
        for row in recomputed_package.get("claim_derivations", [])
        if row.get("claim_id")
    }
    draft_package_sha256 = draft_payload.get("evidence_package_sha256")
    draft_package_hash_matches = bool(draft_package_sha256) and (
        draft_package_sha256 == expected_package_sha256
    )
    export_package_hash_mismatch_count = sum(
        1 for row in exports if row.package_sha256 != expected_package_sha256
    )
    export_package_hash_matches = bool(exports) and export_package_hash_mismatch_count == 0
    stored_claim_ids = {row.claim_id for row in derivations}
    missing_claim_derivation_ids = sorted(
        claim_id
        for claim_id in expected_derivations_by_claim_id
        if claim_id not in stored_claim_ids
    )
    mismatched_claim_ids: list[str] = []
    package_mismatched_claim_ids: list[str] = []
    provenance_lock_mismatched_claim_ids: list[str] = []
    provenance_lock_contract_mismatched_claim_ids: list[str] = []
    missing_provenance_lock_claim_ids: list[str] = []
    support_judgment_mismatched_claim_ids: list[str] = []
    support_judgment_contract_mismatched_claim_ids: list[str] = []
    missing_support_judgment_claim_ids: list[str] = []
    failed_support_judgment_claim_ids: list[str] = []
    for row in derivations:
        expected_derivation = expected_derivations_by_claim_id.get(str(row.claim_id))
        expected_derivation_sha256 = (
            str(expected_derivation.get("derivation_sha256") or "")
            if expected_derivation is not None
            else ""
        )
        if row.derivation_sha256 != expected_derivation_sha256:
            mismatched_claim_ids.append(str(row.claim_id))
        if row.evidence_package_sha256 != expected_package_sha256:
            package_mismatched_claim_ids.append(str(row.claim_id))
        expected_provenance_lock_sha256 = (
            str(expected_derivation.get("provenance_lock_sha256") or "")
            if expected_derivation is not None
            else ""
        )
        if not row.provenance_lock_json or not row.provenance_lock_sha256:
            missing_provenance_lock_claim_ids.append(str(row.claim_id))
        elif (
            row.provenance_lock_sha256 != payload_sha256(row.provenance_lock_json)
            or row.provenance_lock_sha256 != expected_provenance_lock_sha256
        ):
            provenance_lock_mismatched_claim_ids.append(str(row.claim_id))
        if _claim_derivation_provenance_lock_contract_mismatches(row):
            provenance_lock_contract_mismatched_claim_ids.append(str(row.claim_id))
        expected_support_judgment_sha256 = (
            str(expected_derivation.get("support_judgment_sha256") or "")
            if expected_derivation is not None
            else ""
        )
        if (
            not row.support_verdict
            or row.support_score is None
            or not row.support_judge_run_id
            or not row.support_judgment_json
            or not row.support_judgment_sha256
        ):
            missing_support_judgment_claim_ids.append(str(row.claim_id))
        elif (
            row.support_judgment_sha256 != payload_sha256(row.support_judgment_json)
            or row.support_judgment_sha256 != expected_support_judgment_sha256
        ):
            support_judgment_mismatched_claim_ids.append(str(row.claim_id))
        if _claim_derivation_support_judgment_contract_mismatches(row):
            support_judgment_contract_mismatched_claim_ids.append(str(row.claim_id))
        if row.support_verdict != "supported":
            failed_support_judgment_claim_ids.append(str(row.claim_id))

    return {
        "expected_evidence_package_sha256": expected_package_sha256,
        "draft_evidence_package_sha256": draft_package_sha256,
        "draft_package_hash_matches": draft_package_hash_matches,
        "export_package_hash_matches": export_package_hash_matches,
        "export_package_hash_mismatch_count": export_package_hash_mismatch_count,
        "expected_claim_derivation_count": len(expected_derivations_by_claim_id),
        "stored_claim_derivation_count": len(derivations),
        "claim_derivation_count_matches": len(derivations) == len(expected_derivations_by_claim_id),
        "claim_derivation_hash_mismatch_count": len(mismatched_claim_ids),
        "claim_package_hash_mismatch_count": len(package_mismatched_claim_ids),
        "claim_provenance_lock_mismatch_count": len(provenance_lock_mismatched_claim_ids),
        "claim_provenance_lock_contract_mismatch_count": len(
            provenance_lock_contract_mismatched_claim_ids
        ),
        "missing_claim_provenance_lock_count": len(missing_provenance_lock_claim_ids),
        "claim_support_judgment_mismatch_count": len(support_judgment_mismatched_claim_ids),
        "claim_support_judgment_contract_mismatch_count": len(
            support_judgment_contract_mismatched_claim_ids
        ),
        "missing_claim_support_judgment_count": len(missing_support_judgment_claim_ids),
        "failed_claim_support_judgment_count": len(failed_support_judgment_claim_ids),
        "missing_claim_derivation_count": len(missing_claim_derivation_ids),
        "mismatched_claim_ids": sorted(mismatched_claim_ids),
        "package_mismatched_claim_ids": sorted(package_mismatched_claim_ids),
        "provenance_lock_mismatched_claim_ids": sorted(provenance_lock_mismatched_claim_ids),
        "provenance_lock_contract_mismatched_claim_ids": sorted(
            provenance_lock_contract_mismatched_claim_ids
        ),
        "missing_provenance_lock_claim_ids": sorted(missing_provenance_lock_claim_ids),
        "support_judgment_mismatched_claim_ids": sorted(support_judgment_mismatched_claim_ids),
        "support_judgment_contract_mismatched_claim_ids": sorted(
            support_judgment_contract_mismatched_claim_ids
        ),
        "missing_support_judgment_claim_ids": sorted(missing_support_judgment_claim_ids),
        "failed_support_judgment_claim_ids": sorted(failed_support_judgment_claim_ids),
        "missing_claim_derivation_ids": missing_claim_derivation_ids,
    }

def _semantic_trace_payload(
    session: Session,
    *,
    assertion_ids: list[UUID],
    fact_ids: list[UUID],
    evidence_ids: list[UUID],
) -> dict[str, Any]:
    assertions_by_id = _select_by_ids(session, SemanticAssertion, assertion_ids)
    facts_by_id = _select_by_ids(session, SemanticFact, fact_ids)
    assertion_evidence_by_id: dict[UUID, SemanticAssertionEvidence] = {}
    if evidence_ids:
        assertion_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticAssertionEvidence)
                    .where(SemanticAssertionEvidence.id.in_(evidence_ids))
                    .order_by(SemanticAssertionEvidence.created_at, SemanticAssertionEvidence.id)
                )
            }
        )
    if assertion_ids:
        assertion_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticAssertionEvidence)
                    .where(SemanticAssertionEvidence.assertion_id.in_(assertion_ids))
                    .order_by(SemanticAssertionEvidence.created_at, SemanticAssertionEvidence.id)
                )
            }
        )

    fact_evidence_by_id: dict[UUID, SemanticFactEvidence] = {}
    if fact_ids:
        fact_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticFactEvidence)
                    .where(SemanticFactEvidence.fact_id.in_(fact_ids))
                    .order_by(SemanticFactEvidence.created_at, SemanticFactEvidence.id)
                )
            }
        )
    if assertion_ids:
        fact_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticFactEvidence)
                    .where(SemanticFactEvidence.assertion_id.in_(assertion_ids))
                    .order_by(SemanticFactEvidence.created_at, SemanticFactEvidence.id)
                )
            }
        )
    if evidence_ids:
        fact_evidence_by_id.update(
            {
                row.id: row
                for row in session.scalars(
                    select(SemanticFactEvidence)
                    .where(SemanticFactEvidence.assertion_evidence_id.in_(evidence_ids))
                    .order_by(SemanticFactEvidence.created_at, SemanticFactEvidence.id)
                )
            }
        )

    return {
        "assertions": [
            _semantic_assertion_payload(row)
            for row in sorted(assertions_by_id.values(), key=lambda item: str(item.id))
        ],
        "facts": [
            _semantic_fact_payload(row)
            for row in sorted(facts_by_id.values(), key=lambda item: str(item.id))
        ],
        "assertion_evidence": [
            _semantic_assertion_evidence_payload(row)
            for row in sorted(assertion_evidence_by_id.values(), key=lambda item: str(item.id))
        ],
        "fact_evidence": [
            _semantic_fact_evidence_payload(row)
            for row in sorted(fact_evidence_by_id.values(), key=lambda item: str(item.id))
        ],
    }


def _source_record_payloads_from_semantic_trace(
    session: Session,
    assertion_evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    chunk_ids = _uuid_values(row.get("chunk_id") for row in assertion_evidence)
    table_ids = _uuid_values(row.get("table_id") for row in assertion_evidence)
    figure_ids = _uuid_values(row.get("figure_id") for row in assertion_evidence)
    chunks_by_id = _select_by_ids(session, DocumentChunk, chunk_ids)
    tables_by_id = _select_by_ids(session, DocumentTable, table_ids)
    figures_by_id = _select_by_ids(session, DocumentFigure, figure_ids)
    segments_by_table_id: dict[UUID, list[DocumentTableSegment]] = {
        table_id: [] for table_id in tables_by_id
    }
    if table_ids:
        for segment in session.scalars(
            select(DocumentTableSegment)
            .where(DocumentTableSegment.table_id.in_(table_ids))
            .order_by(
                DocumentTableSegment.table_id.asc(),
                DocumentTableSegment.segment_order.asc(),
                DocumentTableSegment.segment_index.asc(),
            )
        ):
            segments_by_table_id.setdefault(segment.table_id, []).append(segment)

    records: list[dict[str, Any]] = []
    for evidence in assertion_evidence:
        chunk_id = _uuid_or_none(evidence.get("chunk_id"))
        table_id = _uuid_or_none(evidence.get("table_id"))
        figure_id = _uuid_or_none(evidence.get("figure_id"))
        table_payload = (
            _table_payload(
                tables_by_id.get(table_id),
                segments=segments_by_table_id.get(table_id, []),
            )
            if table_id is not None
            else None
        )
        records.append(
            {
                "record_kind": "semantic_assertion_source",
                "evidence_id": evidence.get("evidence_id"),
                "source_type": evidence.get("source_type"),
                "source_locator": evidence.get("source_locator"),
                "source_artifact_sha256": evidence.get("source_artifact_sha256"),
                "chunk": _chunk_payload(chunks_by_id.get(chunk_id)) if chunk_id else None,
                "table": table_payload,
                "figure": _figure_payload(figures_by_id.get(figure_id)) if figure_id else None,
            }
        )
    return records


def _report_evidence_card_source_records(evidence_cards: list[dict[str, Any]]) -> list[dict]:
    return [
        {
            "record_kind": "technical_report_evidence_card",
            "evidence_card_id": card.get("evidence_card_id"),
            "evidence_kind": card.get("evidence_kind"),
            "source_type": card.get("source_type"),
            "document_id": card.get("document_id"),
            "run_id": card.get("run_id"),
            "page_from": card.get("page_from"),
            "page_to": card.get("page_to"),
            "source_artifact_api_path": card.get("source_artifact_api_path"),
            "evidence_card_sha256": _evidence_card_snapshot(dict(card)).get("evidence_card_sha256"),
            "source_snapshot_sha256s": card.get("source_snapshot_sha256s") or [],
        }
        for card in evidence_cards
    ]


def _technical_report_provenance_edges(
    *,
    source_documents: list[dict],
    document_runs: list[dict],
    evidence_exports: list[dict],
    evidence_cards: list[dict],
    claims: list[dict],
    claim_derivations: list[dict],
    claim_retrieval_feedback: list[dict],
    semantic_trace: dict[str, Any],
    context_pack_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    harness_task_id = context_pack_audit.get("harness_task_id")
    context_pack_artifacts = list(context_pack_audit.get("context_pack_artifacts") or [])
    evaluation_artifacts = list(context_pack_audit.get("evaluation_artifacts") or [])
    context_pack_verifications = list(context_pack_audit.get("verifications") or [])
    context_pack_operator_runs = list(context_pack_audit.get("operator_runs") or [])
    release_readiness_assessments = list(
        context_pack_audit.get("release_readiness_assessments") or []
    )
    release_readiness_db_gate = dict(context_pack_audit.get("release_readiness_db_gate") or {})
    release_readiness_db_gate_ref = _release_readiness_db_gate_trace_ref(context_pack_audit)
    for artifact in context_pack_artifacts:
        artifact_id = artifact.get("artifact_id")
        if harness_task_id and artifact_id:
            edges.append(
                {
                    "edge_type": "harness_task_to_context_pack_artifact",
                    "from": {"table": "agent_tasks", "id": harness_task_id},
                    "to": {"table": "agent_task_artifacts", "id": artifact_id},
                }
            )
    for verification in context_pack_verifications:
        verification_id = verification.get("verification_id")
        verification_task_id = verification.get("verification_task_id")
        if verification_task_id and verification_id:
            edges.append(
                {
                    "edge_type": "context_pack_eval_task_to_verifier_record",
                    "from": {"table": "agent_tasks", "id": verification_task_id},
                    "to": {"table": "agent_task_verifications", "id": verification_id},
                }
            )
        for artifact in context_pack_artifacts:
            artifact_id = artifact.get("artifact_id")
            if artifact_id and verification_id:
                edges.append(
                    {
                        "edge_type": "context_pack_artifact_to_verifier_record",
                        "from": {"table": "agent_task_artifacts", "id": artifact_id},
                        "to": {"table": "agent_task_verifications", "id": verification_id},
                        "context_pack_sha256": verification.get("details", {}).get(
                            "context_pack_sha256"
                        ),
                    }
                )
        db_gate_verification_id = release_readiness_db_gate.get("verification_id")
        if (
            verification_id
            and db_gate_verification_id == str(verification_id)
            and release_readiness_db_gate_ref
        ):
            edges.append(
                {
                    "edge_type": "context_pack_verifier_record_to_release_readiness_db_gate",
                    "from": {"table": "agent_task_verifications", "id": verification_id},
                    "to": release_readiness_db_gate_ref,
                    "complete": release_readiness_db_gate.get("complete"),
                }
            )
    for artifact in evaluation_artifacts:
        artifact_id = artifact.get("artifact_id")
        task_id = artifact.get("task_id")
        if task_id and artifact_id:
            edges.append(
                {
                    "edge_type": "context_pack_eval_task_to_evaluation_artifact",
                    "from": {"table": "agent_tasks", "id": task_id},
                    "to": {"table": "agent_task_artifacts", "id": artifact_id},
                }
            )
        for verification in context_pack_verifications:
            verification_id = verification.get("verification_id")
            if verification_id and artifact_id:
                edges.append(
                    {
                        "edge_type": "context_pack_verifier_record_to_evaluation_artifact",
                        "from": {"table": "agent_task_verifications", "id": verification_id},
                        "to": {"table": "agent_task_artifacts", "id": artifact_id},
                    }
                )
    for operator_run in context_pack_operator_runs:
        operator_run_id = operator_run.get("operator_run_id")
        for verification in context_pack_verifications:
            verification_id = verification.get("verification_id")
            if operator_run_id and verification_id:
                edges.append(
                    {
                        "edge_type": "context_pack_eval_operator_to_verifier_record",
                        "from": {"table": "knowledge_operator_runs", "id": operator_run_id},
                        "to": {"table": "agent_task_verifications", "id": verification_id},
                    }
                )
    for readiness_ref in release_readiness_assessments:
        assessment_id = readiness_ref.get("assessment_id")
        release_id = readiness_ref.get("search_harness_release_id")
        if release_id and assessment_id:
            edges.append(
                {
                    "edge_type": "search_harness_release_to_readiness_assessment",
                    "from": {"table": "search_harness_releases", "id": release_id},
                    "to": {
                        "table": "search_harness_release_readiness_assessments",
                        "id": assessment_id,
                    },
                }
            )
        for artifact in context_pack_artifacts:
            artifact_id = artifact.get("artifact_id")
            if assessment_id and artifact_id:
                edges.append(
                    {
                        "edge_type": "release_readiness_assessment_to_context_pack_artifact",
                        "from": {
                            "table": "search_harness_release_readiness_assessments",
                            "id": assessment_id,
                        },
                        "to": {"table": "agent_task_artifacts", "id": artifact_id},
                        "assessment_payload_sha256": readiness_ref.get("assessment_payload_sha256"),
                    }
                )
        for verification in context_pack_verifications:
            verification_id = verification.get("verification_id")
            if assessment_id and verification_id:
                edges.append(
                    {
                        "edge_type": "release_readiness_assessment_to_context_pack_verifier_record",
                        "from": {
                            "table": "search_harness_release_readiness_assessments",
                            "id": assessment_id,
                        },
                        "to": {"table": "agent_task_verifications", "id": verification_id},
                    }
                )
        db_gate_verification_id = release_readiness_db_gate.get("verification_id")
        if assessment_id and db_gate_verification_id and release_readiness_db_gate_ref:
            edges.append(
                {
                    "edge_type": "release_readiness_assessment_to_release_readiness_db_gate",
                    "from": {
                        "table": "search_harness_release_readiness_assessments",
                        "id": assessment_id,
                    },
                    "to": release_readiness_db_gate_ref,
                    "assessment_payload_sha256": readiness_ref.get("assessment_payload_sha256"),
                }
            )
    for export in evidence_exports:
        if export.get("package_kind") == "search_request" and export.get("search_request_id"):
            edges.append(
                {
                    "edge_type": "search_request_to_evidence_package_export",
                    "from": {"table": "search_requests", "id": export.get("search_request_id")},
                    "to": {
                        "table": "evidence_package_exports",
                        "id": export.get("evidence_package_export_id"),
                    },
                }
            )
    for run in document_runs:
        if run.get("document_id"):
            edges.append(
                {
                    "edge_type": "source_document_to_document_run",
                    "from": {"table": "documents", "id": run.get("document_id")},
                    "to": {"table": "document_runs", "id": run.get("id")},
                }
            )
    for evidence in semantic_trace["assertion_evidence"]:
        target_id = evidence.get(f"{evidence.get('source_type')}_id")
        if target_id:
            edges.append(
                {
                    "edge_type": "document_run_to_source_record",
                    "from": {"table": "document_runs", "id": evidence.get("run_id")},
                    "to": {
                        "table": f"document_{evidence.get('source_type')}s",
                        "id": target_id,
                    },
                }
            )
    for card in evidence_cards:
        for export_id in card.get("source_evidence_package_export_ids") or []:
            edges.append(
                {
                    "edge_type": "search_evidence_export_to_report_card",
                    "from": {"table": "evidence_package_exports", "id": export_id},
                    "to": {
                        "table": "technical_report_evidence_cards",
                        "id": card.get("evidence_card_id"),
                    },
                }
            )
        for evidence_id in card.get("evidence_ids") or []:
            edges.append(
                {
                    "edge_type": "semantic_evidence_to_report_card",
                    "from": {"table": "semantic_assertion_evidence", "id": evidence_id},
                    "to": {
                        "table": "technical_report_evidence_cards",
                        "id": card.get("evidence_card_id"),
                    },
                }
            )
    for claim in claims:
        if claim.get("provenance_lock_sha256"):
            edges.append(
                {
                    "edge_type": "claim_to_provenance_lock",
                    "from": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                    "to": {
                        "table": "technical_report_claim_provenance_locks",
                        "id": claim.get("provenance_lock_sha256"),
                    },
                    "derivation_sha256": claim.get("derivation_sha256"),
                }
            )
        if claim.get("support_judgment_sha256"):
            edges.append(
                {
                    "edge_type": "claim_to_support_judgment",
                    "from": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                    "to": {
                        "table": "technical_report_claim_support_judgments",
                        "id": claim.get("support_judgment_sha256"),
                    },
                    "derivation_sha256": claim.get("derivation_sha256"),
                    "support_verdict": claim.get("support_verdict"),
                    "support_score": claim.get("support_score"),
                }
            )
        if claim.get("support_judge_run_id"):
            edges.append(
                {
                    "edge_type": "support_judge_run_to_claim",
                    "from": {
                        "table": "knowledge_operator_runs",
                        "id": claim.get("support_judge_run_id"),
                    },
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                    "support_judgment_sha256": claim.get("support_judgment_sha256"),
                }
            )
        for result_id in claim.get("source_search_request_result_ids") or []:
            edges.append(
                {
                    "edge_type": "search_result_to_claim",
                    "from": {"table": "search_request_results", "id": result_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for export_id in claim.get("source_evidence_package_export_ids") or []:
            edges.append(
                {
                    "edge_type": "search_evidence_export_to_claim",
                    "from": {"table": "evidence_package_exports", "id": export_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for snapshot_id in claim.get("semantic_ontology_snapshot_ids") or []:
            edges.append(
                {
                    "edge_type": "semantic_ontology_snapshot_to_claim",
                    "from": {"table": "semantic_ontology_snapshots", "id": snapshot_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for snapshot_id in claim.get("semantic_graph_snapshot_ids") or []:
            edges.append(
                {
                    "edge_type": "semantic_graph_snapshot_to_claim",
                    "from": {"table": "semantic_graph_snapshots", "id": snapshot_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for artifact_id in claim.get("retrieval_reranker_artifact_ids") or []:
            edges.append(
                {
                    "edge_type": "retrieval_reranker_artifact_to_claim",
                    "from": {"table": "retrieval_reranker_artifacts", "id": artifact_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for release_id in claim.get("search_harness_release_ids") or []:
            edges.append(
                {
                    "edge_type": "search_harness_release_to_claim",
                    "from": {"table": "search_harness_releases", "id": release_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for bundle_id in claim.get("release_audit_bundle_ids") or []:
            edges.append(
                {
                    "edge_type": "release_audit_bundle_to_claim",
                    "from": {"table": "audit_bundle_exports", "id": bundle_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for receipt_id in claim.get("release_validation_receipt_ids") or []:
            edges.append(
                {
                    "edge_type": "release_validation_receipt_to_claim",
                    "from": {"table": "audit_bundle_validation_receipts", "id": receipt_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
        for card_id in claim.get("evidence_card_ids") or []:
            edges.append(
                {
                    "edge_type": "report_card_to_claim",
                    "from": {"table": "technical_report_evidence_cards", "id": card_id},
                    "to": {"table": "technical_report_claims", "id": claim.get("claim_id")},
                }
            )
    for derivation in claim_derivations:
        edges.append(
            {
                "edge_type": "claim_to_derivation_hash",
                "from": {
                    "table": "technical_report_claims",
                    "id": derivation.get("claim_id"),
                },
                "to": {
                    "table": "claim_evidence_derivations",
                    "id": derivation.get("claim_evidence_derivation_id"),
                },
                "derivation_sha256": derivation.get("derivation_sha256"),
            }
        )
    for feedback in claim_retrieval_feedback:
        feedback_id = feedback.get("feedback_id")
        claim_id = feedback.get("claim_id")
        if feedback_id and claim_id:
            edges.append(
                {
                    "edge_type": "claim_to_retrieval_feedback",
                    "from": {"table": "technical_report_claims", "id": claim_id},
                    "to": {
                        "table": TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
                        "id": feedback_id,
                    },
                    "feedback_payload_sha256": feedback.get("feedback_payload_sha256"),
                    "source_payload_sha256": feedback.get("source_payload_sha256"),
                }
            )
        gate_id = feedback.get("release_readiness_db_gate_id")
        if feedback_id and gate_id:
            edges.append(
                {
                    "edge_type": "release_readiness_db_gate_to_claim_retrieval_feedback",
                    "from": {
                        "table": TECHNICAL_REPORT_RELEASE_READINESS_DB_GATES_TABLE,
                        "id": gate_id,
                    },
                    "to": {
                        "table": TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
                        "id": feedback_id,
                    },
                    "feedback_payload_sha256": feedback.get("feedback_payload_sha256"),
                }
            )
        for request_id in feedback.get("source_search_request_ids") or []:
            edges.append(
                {
                    "edge_type": "search_request_to_claim_retrieval_feedback",
                    "from": {"table": "search_requests", "id": request_id},
                    "to": {
                        "table": TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
                        "id": feedback_id,
                    },
                }
            )
        for result_id in feedback.get("source_search_request_result_ids") or []:
            edges.append(
                {
                    "edge_type": "search_result_to_claim_retrieval_feedback",
                    "from": {"table": "search_request_results", "id": result_id},
                    "to": {
                        "table": TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
                        "id": feedback_id,
                    },
                }
            )
        for span_id in feedback.get("search_request_result_span_ids") or []:
            edges.append(
                {
                    "edge_type": "selected_span_to_claim_retrieval_feedback",
                    "from": {"table": "search_request_result_spans", "id": span_id},
                    "to": {
                        "table": TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
                        "id": feedback_id,
                    },
                }
            )
        governance_event_id = feedback.get("semantic_governance_event_id")
        if feedback_id and governance_event_id:
            edges.append(
                {
                    "edge_type": "semantic_governance_event_to_claim_retrieval_feedback",
                    "from": {"table": "semantic_governance_events", "id": governance_event_id},
                    "to": {
                        "table": TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
                        "id": feedback_id,
                    },
                }
            )
    for document in source_documents:
        edges.append(
            {
                "edge_type": "source_pdf_checksum",
                "from": {"table": "source_pdf", "sha256": document.get("sha256")},
                "to": {"table": "documents", "id": document.get("id")},
            }
        )
    return edges


technical_report_integrity_payload = _technical_report_integrity_payload
semantic_trace_payload = _semantic_trace_payload
source_record_payloads_from_semantic_trace = _source_record_payloads_from_semantic_trace
report_evidence_card_source_records = _report_evidence_card_source_records
technical_report_provenance_edges = _technical_report_provenance_edges
