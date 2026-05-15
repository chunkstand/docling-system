from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db.models import ClaimEvidenceDerivation
from app.services.evidence_common import (
    clean_mapping as _clean_mapping,
)
from app.services.evidence_common import (
    payload_sha256,
)
from app.services.evidence_common import (
    string_values as _string_values,
)

_DERIVATION_MUTABLE_FIELDS = {
    "derivation_rule",
    "evidence_package_export_id",
    "evidence_package_sha256",
    "derivation_sha256",
    "source_snapshot_sha256s",
}


def _evidence_card_snapshot(card: dict[str, Any]) -> dict[str, Any]:
    clean_card = _clean_mapping(
        card,
        drop_fields={
            "evidence_package_export_id",
            "evidence_package_sha256",
            "source_snapshot_sha256s",
        },
    )
    return {
        **clean_card,
        "evidence_card_sha256": payload_sha256(clean_card),
    }


def build_technical_report_derivation_package(draft_payload: dict[str, Any]) -> dict[str, Any]:
    evidence_cards = [
        _evidence_card_snapshot(dict(card)) for card in draft_payload.get("evidence_cards", [])
    ]
    cards_by_id = {
        str(card.get("evidence_card_id")): card
        for card in evidence_cards
        if card.get("evidence_card_id")
    }
    graph_context = list(draft_payload.get("graph_context") or [])
    document_refs = list(draft_payload.get("document_refs") or [])
    package_claims: list[dict[str, Any]] = []

    for raw_claim in draft_payload.get("claims", []):
        claim = _clean_mapping(dict(raw_claim), drop_fields=_DERIVATION_MUTABLE_FIELDS)
        evidence_card_ids = _string_values(claim.get("evidence_card_ids") or [])
        graph_edge_ids = _string_values(claim.get("graph_edge_ids") or [])
        source_snapshot_sha256s = _string_values(
            cards_by_id[card_id].get("evidence_card_sha256")
            for card_id in evidence_card_ids
            if card_id in cards_by_id
        )
        if not source_snapshot_sha256s and graph_edge_ids:
            source_snapshot_sha256s = _string_values(
                [
                    payload_sha256(
                        {
                            "graph_edge_ids": graph_edge_ids,
                            "claim_id": claim.get("claim_id"),
                        }
                    )
                ]
            )
        package_claims.append(
            {
                "claim_id": claim.get("claim_id"),
                "section_id": claim.get("section_id"),
                "rendered_text": claim.get("rendered_text"),
                "concept_keys": _string_values(claim.get("concept_keys") or []),
                "evidence_card_ids": evidence_card_ids,
                "graph_edge_ids": graph_edge_ids,
                "fact_ids": _string_values(claim.get("fact_ids") or []),
                "assertion_ids": _string_values(claim.get("assertion_ids") or []),
                "source_document_ids": _string_values(claim.get("source_document_ids") or []),
                "source_snapshot_sha256s": source_snapshot_sha256s,
                "source_search_request_ids": _string_values(
                    claim.get("source_search_request_ids") or []
                ),
                "source_search_request_result_ids": _string_values(
                    claim.get("source_search_request_result_ids") or []
                ),
                "source_evidence_package_export_ids": _string_values(
                    claim.get("source_evidence_package_export_ids") or []
                ),
                "source_evidence_package_sha256s": _string_values(
                    claim.get("source_evidence_package_sha256s") or []
                ),
                "source_evidence_trace_sha256s": _string_values(
                    claim.get("source_evidence_trace_sha256s") or []
                ),
                "semantic_ontology_snapshot_ids": _string_values(
                    claim.get("semantic_ontology_snapshot_ids") or []
                ),
                "semantic_graph_snapshot_ids": _string_values(
                    claim.get("semantic_graph_snapshot_ids") or []
                ),
                "retrieval_reranker_artifact_ids": _string_values(
                    claim.get("retrieval_reranker_artifact_ids") or []
                ),
                "search_harness_release_ids": _string_values(
                    claim.get("search_harness_release_ids") or []
                ),
                "release_audit_bundle_ids": _string_values(
                    claim.get("release_audit_bundle_ids") or []
                ),
                "release_validation_receipt_ids": _string_values(
                    claim.get("release_validation_receipt_ids") or []
                ),
                "provenance_lock": dict(claim.get("provenance_lock") or {}),
                "provenance_lock_sha256": claim.get("provenance_lock_sha256"),
                "support_verdict": claim.get("support_verdict"),
                "support_score": claim.get("support_score"),
                "support_judge_run_id": str(claim.get("support_judge_run_id") or "") or None,
                "support_judgment": dict(claim.get("support_judgment") or {}),
                "support_judgment_sha256": claim.get("support_judgment_sha256"),
                "derivation_rule": "technical_report_claim_contract_v1",
            }
        )

    package_core = {
        "schema_name": "technical_report_claim_derivation_package",
        "schema_version": "1.0",
        "title": draft_payload.get("title"),
        "harness_task_id": str(draft_payload.get("harness_task_id") or ""),
        "generator_mode": draft_payload.get("generator_mode"),
        "generator_model": draft_payload.get("generator_model"),
        "document_refs": document_refs,
        "evidence_cards": evidence_cards,
        "graph_context": graph_context,
        "claims": package_claims,
    }
    package_sha256 = payload_sha256(package_core)
    claim_derivations: list[dict[str, Any]] = []
    for claim in package_claims:
        derivation_seed = {
            **claim,
            "evidence_package_sha256": package_sha256,
        }
        claim_derivations.append(
            {
                **claim,
                "evidence_package_sha256": package_sha256,
                "derivation_sha256": payload_sha256(derivation_seed),
            }
        )
    return {
        **package_core,
        "package_sha256": package_sha256,
        "claim_derivations": claim_derivations,
        "source_snapshot_sha256s": _string_values(
            value
            for claim in claim_derivations
            for value in claim.get("source_snapshot_sha256s", [])
        ),
        "document_ids": _string_values(
            [
                *[row.get("document_id") for row in document_refs if isinstance(row, dict)],
                *[
                    row.get("document_id")
                    for row in evidence_cards
                    if isinstance(row, dict) and row.get("document_id")
                ],
            ]
        ),
        "run_ids": _string_values(
            row.get("run_id")
            for row in evidence_cards
            if isinstance(row, dict) and row.get("run_id")
        ),
        "claim_ids": _string_values(claim.get("claim_id") for claim in claim_derivations),
    }


def apply_technical_report_derivation_links(
    draft_payload: dict[str, Any],
    *,
    evidence_package_export_id: UUID | None = None,
) -> dict[str, Any]:
    package = build_technical_report_derivation_package(draft_payload)
    package_sha256 = package["package_sha256"]
    source_snapshot_sha256s = list(package["source_snapshot_sha256s"])
    derivations_by_claim_id = {
        str(row["claim_id"]): row for row in package["claim_derivations"] if row.get("claim_id")
    }
    for card in draft_payload.get("evidence_cards", []):
        if evidence_package_export_id is not None:
            card["evidence_package_export_id"] = str(evidence_package_export_id)
        card["evidence_package_sha256"] = package_sha256
        snapshot = _evidence_card_snapshot(dict(card))
        card["source_snapshot_sha256s"] = _string_values([snapshot.get("evidence_card_sha256")])
    for claim in draft_payload.get("claims", []):
        derivation = derivations_by_claim_id.get(str(claim.get("claim_id")))
        if not derivation:
            continue
        claim["derivation_rule"] = derivation["derivation_rule"]
        if evidence_package_export_id is not None:
            claim["evidence_package_export_id"] = str(evidence_package_export_id)
        claim["evidence_package_sha256"] = package_sha256
        claim["derivation_sha256"] = derivation["derivation_sha256"]
        claim["source_snapshot_sha256s"] = list(derivation["source_snapshot_sha256s"])
    if evidence_package_export_id is not None:
        draft_payload["evidence_package_export_id"] = str(evidence_package_export_id)
    draft_payload["evidence_package_sha256"] = package_sha256
    draft_payload["source_snapshot_sha256s"] = source_snapshot_sha256s
    draft_payload["claim_derivations"] = package["claim_derivations"]
    return package


def _claim_derivation_payload(row: ClaimEvidenceDerivation) -> dict[str, Any]:
    return {
        "claim_evidence_derivation_id": row.id,
        "evidence_package_export_id": row.evidence_package_export_id,
        "agent_task_id": row.agent_task_id,
        "claim_id": row.claim_id,
        "claim_text": row.claim_text,
        "derivation_rule": row.derivation_rule,
        "evidence_card_ids": row.evidence_card_ids_json or [],
        "graph_edge_ids": row.graph_edge_ids_json or [],
        "fact_ids": row.fact_ids_json or [],
        "assertion_ids": row.assertion_ids_json or [],
        "source_document_ids": row.source_document_ids_json or [],
        "source_snapshot_sha256s": row.source_snapshot_sha256s_json or [],
        "source_search_request_ids": row.source_search_request_ids_json or [],
        "source_search_request_result_ids": row.source_search_request_result_ids_json or [],
        "source_evidence_package_export_ids": (row.source_evidence_package_export_ids_json or []),
        "source_evidence_package_sha256s": row.source_evidence_package_sha256s_json or [],
        "source_evidence_trace_sha256s": row.source_evidence_trace_sha256s_json or [],
        "semantic_ontology_snapshot_ids": row.semantic_ontology_snapshot_ids_json or [],
        "semantic_graph_snapshot_ids": row.semantic_graph_snapshot_ids_json or [],
        "retrieval_reranker_artifact_ids": row.retrieval_reranker_artifact_ids_json or [],
        "search_harness_release_ids": row.search_harness_release_ids_json or [],
        "release_audit_bundle_ids": row.release_audit_bundle_ids_json or [],
        "release_validation_receipt_ids": row.release_validation_receipt_ids_json or [],
        "provenance_lock": row.provenance_lock_json or {},
        "provenance_lock_sha256": row.provenance_lock_sha256,
        "support_verdict": row.support_verdict,
        "support_score": row.support_score,
        "support_judge_run_id": row.support_judge_run_id,
        "support_judgment": row.support_judgment_json or {},
        "support_judgment_sha256": row.support_judgment_sha256,
        "evidence_package_sha256": row.evidence_package_sha256,
        "derivation_sha256": row.derivation_sha256,
        "created_at": row.created_at,
    }


evidence_card_snapshot = _evidence_card_snapshot
claim_derivation_payload = _claim_derivation_payload
