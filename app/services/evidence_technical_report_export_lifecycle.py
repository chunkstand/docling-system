from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.coercion import uuid_or_none as _uuid_or_none
from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow as _utcnow
from app.db.public.audit_and_evidence import ClaimEvidenceDerivation, EvidencePackageExport
from app.services.evidence_common import (
    string_values as _string_values,
)
from app.services.evidence_technical_report_export_payloads import (
    apply_technical_report_derivation_links,
)
from app.services.evidence_technical_report_export_provenance_locks import (
    apply_technical_report_claim_provenance_locks as _apply_technical_report_claim_provenance_locks,
)


def persist_technical_report_evidence_export(
    session: Session,
    *,
    draft_payload: dict,
    agent_task_id: UUID,
    agent_task_artifact_id: UUID | None = None,
) -> EvidencePackageExport:
    _apply_technical_report_claim_provenance_locks(session, draft_payload)
    package = apply_technical_report_derivation_links(draft_payload)
    now = _utcnow()
    export = EvidencePackageExport(
        id=uuid.uuid4(),
        package_kind="technical_report_claims",
        agent_task_id=agent_task_id,
        agent_task_artifact_id=agent_task_artifact_id,
        package_sha256=package["package_sha256"],
        package_payload_json=_json_payload(package),
        source_snapshot_sha256s_json=list(package["source_snapshot_sha256s"]),
        operator_run_ids_json=[],
        document_ids_json=list(package["document_ids"]),
        run_ids_json=list(package["run_ids"]),
        claim_ids_json=list(package["claim_ids"]),
        export_status="completed",
        created_at=now,
    )
    session.add(export)
    session.flush()
    apply_technical_report_derivation_links(
        draft_payload,
        evidence_package_export_id=export.id,
    )
    for derivation in package["claim_derivations"]:
        session.add(
            ClaimEvidenceDerivation(
                id=uuid.uuid4(),
                evidence_package_export_id=export.id,
                agent_task_id=agent_task_id,
                claim_id=str(derivation["claim_id"]),
                claim_text=derivation.get("rendered_text"),
                derivation_rule=str(derivation["derivation_rule"]),
                evidence_card_ids_json=list(derivation["evidence_card_ids"]),
                graph_edge_ids_json=list(derivation["graph_edge_ids"]),
                fact_ids_json=list(derivation["fact_ids"]),
                assertion_ids_json=list(derivation["assertion_ids"]),
                source_document_ids_json=list(derivation["source_document_ids"]),
                source_snapshot_sha256s_json=list(derivation["source_snapshot_sha256s"]),
                source_search_request_ids_json=list(derivation["source_search_request_ids"]),
                source_search_request_result_ids_json=list(
                    derivation["source_search_request_result_ids"]
                ),
                source_evidence_package_export_ids_json=list(
                    derivation["source_evidence_package_export_ids"]
                ),
                source_evidence_package_sha256s_json=list(
                    derivation["source_evidence_package_sha256s"]
                ),
                source_evidence_trace_sha256s_json=list(
                    derivation["source_evidence_trace_sha256s"]
                ),
                semantic_ontology_snapshot_ids_json=list(
                    derivation["semantic_ontology_snapshot_ids"]
                ),
                semantic_graph_snapshot_ids_json=list(derivation["semantic_graph_snapshot_ids"]),
                retrieval_reranker_artifact_ids_json=list(
                    derivation["retrieval_reranker_artifact_ids"]
                ),
                search_harness_release_ids_json=list(derivation["search_harness_release_ids"]),
                release_audit_bundle_ids_json=list(derivation["release_audit_bundle_ids"]),
                release_validation_receipt_ids_json=list(
                    derivation["release_validation_receipt_ids"]
                ),
                provenance_lock_json=dict(derivation["provenance_lock"]),
                provenance_lock_sha256=derivation.get("provenance_lock_sha256"),
                support_verdict=derivation.get("support_verdict"),
                support_score=derivation.get("support_score"),
                support_judge_run_id=_uuid_or_none(derivation.get("support_judge_run_id")),
                support_judgment_json=dict(derivation.get("support_judgment") or {}),
                support_judgment_sha256=derivation.get("support_judgment_sha256"),
                evidence_package_sha256=str(derivation["evidence_package_sha256"]),
                derivation_sha256=str(derivation["derivation_sha256"]),
                created_at=now,
            )
        )
    session.flush()
    return export


def attach_artifact_to_evidence_export(
    session: Session,
    *,
    evidence_package_export_id: UUID,
    agent_task_artifact_id: UUID,
) -> None:
    export = session.get(EvidencePackageExport, evidence_package_export_id)
    if export is None:
        return
    export.agent_task_artifact_id = agent_task_artifact_id
    session.flush()


def attach_operator_run_to_evidence_export(
    session: Session,
    *,
    evidence_package_export_id: UUID,
    operator_run_id: UUID,
) -> None:
    export = session.get(EvidencePackageExport, evidence_package_export_id)
    if export is None:
        return
    export.operator_run_ids_json = _string_values(
        [*(export.operator_run_ids_json or []), operator_run_id]
    )
    session.flush()
