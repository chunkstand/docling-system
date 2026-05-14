from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.evidence_constants import TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE
from app.services.evidence_provenance import prov_identifier as _prov_identifier

if TYPE_CHECKING:
    from app.services.evidence_provenance_export_graph_core import (
        ProvenanceGraphContext,
        ProvenanceGraphState,
    )


def populate_report_graph(
    state: ProvenanceGraphState,
    context: ProvenanceGraphContext,
) -> None:
    _populate_evidence_package_exports(state, context)
    _populate_manifest_provenance_edges(state, context)
    _populate_report_entities(state, context)
    _populate_claim_feedback_lineage(state, context)
    _populate_operator_runs(state, context)


def _populate_evidence_package_exports(
    state: ProvenanceGraphState,
    context: ProvenanceGraphContext,
) -> None:
    for export in context.report_trace.get("evidence_package_exports") or []:
        entity_id = _prov_identifier(
            "evidence_package_exports",
            export.get("evidence_package_export_id"),
        )
        state.add_entity(
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
            state.add_activity(
                search_activity_id,
                label="Search request",
                activity_type="docling:SearchRequest",
            )
            state.add_generated(entity=entity_id, activity=search_activity_id)


def _populate_manifest_provenance_edges(
    state: ProvenanceGraphState,
    context: ProvenanceGraphContext,
) -> None:
    for edge in context.manifest.get("provenance_edges") or []:
        from_ref = edge.get("from") or {}
        to_ref = edge.get("to") or {}
        from_id = _prov_identifier(
            from_ref.get("table"),
            from_ref.get("id") or from_ref.get("sha256"),
        )
        to_id = _prov_identifier(
            to_ref.get("table"),
            to_ref.get("id") or to_ref.get("sha256"),
        )
        if from_id not in state.entities:
            state.add_entity(
                from_id,
                label=str(from_ref.get("table") or "provenance source"),
                entity_type="docling:ProvenanceEndpoint",
                **{"docling:table": from_ref.get("table")},
            )
        if to_id not in state.entities:
            state.add_entity(
                to_id,
                label=str(to_ref.get("table") or "provenance target"),
                entity_type="docling:ProvenanceEndpoint",
                **{"docling:table": to_ref.get("table")},
            )
        state.add_derived(
            generated_entity=to_id,
            used_entity=from_id,
            **{"docling:edge_type": edge.get("edge_type")},
        )
        state.add_used(activity=context.verification_activity_id, entity=from_id)


def _populate_report_entities(
    state: ProvenanceGraphState,
    context: ProvenanceGraphContext,
) -> None:
    for card in context.report_trace.get("evidence_cards") or []:
        state.add_entity(
            _prov_identifier("technical_report_evidence_cards", card.get("evidence_card_id")),
            label=str(card.get("evidence_card_id") or "evidence card"),
            entity_type="docling:TechnicalReportEvidenceCard",
            **{
                "docling:evidence_kind": card.get("evidence_kind"),
                "docling:source_type": card.get("source_type"),
                "docling:source_evidence_match_status": card.get(
                    "source_evidence_match_status"
                ),
            },
        )

    for claim in context.report_trace.get("claims") or []:
        state.add_entity(
            _prov_identifier("technical_report_claims", claim.get("claim_id")),
            label=str(claim.get("claim_id") or "technical report claim"),
            entity_type="docling:TechnicalReportClaim",
            **{
                "docling:claim_text": claim.get("rendered_text"),
                "docling:source_evidence_match_status": claim.get(
                    "source_evidence_match_status"
                ),
            },
        )

    for derivation in context.report_trace.get("claim_derivations") or []:
        state.add_entity(
            _prov_identifier(
                "claim_evidence_derivations",
                derivation.get("claim_evidence_derivation_id"),
            ),
            label=str(derivation.get("claim_id") or "claim derivation"),
            entity_type="docling:ClaimEvidenceDerivation",
            **{"docling:derivation_sha256": derivation.get("derivation_sha256")},
        )


def _populate_claim_feedback_lineage(
    state: ProvenanceGraphState,
    context: ProvenanceGraphContext,
) -> None:
    for feedback in context.report_trace.get("claim_retrieval_feedback") or []:
        entity_id = _prov_identifier(
            TECHNICAL_REPORT_CLAIM_RETRIEVAL_FEEDBACK_TABLE,
            feedback.get("feedback_id"),
        )
        state.add_entity(
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
                "docling:release_readiness_db_gate_id": feedback.get(
                    "release_readiness_db_gate_id"
                ),
                "docling:semantic_governance_event_id": feedback.get(
                    "semantic_governance_event_id"
                ),
            },
        )
        if context.verification_activity_id:
            state.add_generated(entity=entity_id, activity=context.verification_activity_id)
            state.add_used(activity=context.verification_activity_id, entity=entity_id)
        claim_entity_id = _prov_identifier("technical_report_claims", feedback.get("claim_id"))
        if claim_entity_id:
            state.add_derived(
                generated_entity=entity_id,
                used_entity=claim_entity_id,
                **{"docling:edge_type": "claim_to_retrieval_feedback"},
            )
        for result_id in feedback.get("source_search_request_result_ids") or []:
            result_entity_id = _prov_identifier("search_request_results", result_id)
            if result_entity_id:
                state.add_derived(
                    generated_entity=entity_id,
                    used_entity=result_entity_id,
                    **{"docling:edge_type": "search_result_to_claim_retrieval_feedback"},
                )


def _populate_operator_runs(
    state: ProvenanceGraphState,
    context: ProvenanceGraphContext,
) -> None:
    for operator_run in context.report_trace.get("operator_runs") or []:
        activity_id = _prov_identifier(
            "knowledge_operator_runs",
            operator_run.get("operator_run_id"),
        )
        state.add_activity(
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
        state.add_associated(
            activity=activity_id,
            agent="docling:agent/docling-system",
        )
