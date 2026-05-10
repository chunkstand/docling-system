from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import uuid_or_none as _uuid_or_none
from app.core.json_utils import json_object_payload as _json_payload
from app.core.time import utcnow
from app.db.models import (
    AuditBundleExport,
    AuditBundleValidationReceipt,
    ClaimEvidenceDerivation,
    EvidencePackageExport,
    RetrievalRerankerArtifact,
    SearchHarnessRelease,
    SearchRequestRecord,
    SemanticFact,
    SemanticGraphSnapshot,
)
from app.services.evidence_common import (
    clean_mapping as _clean_mapping,
)
from app.services.evidence_common import (
    id_str_values as _id_str_values,
)
from app.services.evidence_common import (
    payload_sha256,
)
from app.services.evidence_common import (
    string_values as _string_values,
)
from app.services.evidence_common import (
    uuid_values as _uuid_values,
)

_DERIVATION_MUTABLE_FIELDS = {
    "derivation_rule",
    "evidence_package_export_id",
    "evidence_package_sha256",
    "derivation_sha256",
    "source_snapshot_sha256s",
}

_CLAIM_PROVENANCE_LOCK_LIST_FIELDS = (
    "source_search_request_ids",
    "source_search_request_result_ids",
    "source_evidence_package_export_ids",
    "source_evidence_package_sha256s",
    "source_evidence_trace_sha256s",
    "semantic_ontology_snapshot_ids",
    "semantic_graph_snapshot_ids",
    "retrieval_reranker_artifact_ids",
    "search_harness_release_ids",
    "release_audit_bundle_ids",
    "release_validation_receipt_ids",
)


def _latest_passed_release_bindings_by_request(
    session: Session,
    request_rows_by_id: dict[str, SearchRequestRecord],
) -> tuple[dict[str, dict[str, Any]], dict[str, SearchHarnessRelease]]:
    harness_names = _string_values(row.harness_name for row in request_rows_by_id.values())
    if not harness_names:
        return {}, {}
    release_rows = list(
        session.scalars(
            select(SearchHarnessRelease)
            .where(
                SearchHarnessRelease.candidate_harness_name.in_(harness_names),
                SearchHarnessRelease.outcome == "passed",
            )
            .order_by(
                SearchHarnessRelease.candidate_harness_name.asc(),
                SearchHarnessRelease.created_at.desc(),
                SearchHarnessRelease.id.asc(),
            )
        )
    )
    release_rows_by_harness: dict[str, list[SearchHarnessRelease]] = {
        harness_name: [] for harness_name in harness_names
    }
    for row in release_rows:
        release_rows_by_harness.setdefault(row.candidate_harness_name, []).append(row)

    bindings_by_request_id: dict[str, dict[str, Any]] = {}
    releases_by_id: dict[str, SearchHarnessRelease] = {}
    for request_id, request_row in request_rows_by_id.items():
        selected_release = next(
            (
                row
                for row in release_rows_by_harness.get(request_row.harness_name, [])
                if row.created_at <= request_row.created_at
            ),
            None,
        )
        binding = {
            "search_request_id": request_id,
            "harness_name": request_row.harness_name,
            "search_request_created_at": request_row.created_at,
            "search_harness_release_id": (
                str(selected_release.id) if selected_release is not None else None
            ),
            "search_harness_release_created_at": (
                selected_release.created_at if selected_release is not None else None
            ),
            "selection_rule": "latest_passed_release_at_or_before_search_request",
            "selection_status": (
                "release_found_before_request"
                if selected_release is not None
                else "no_passed_release_before_request"
            ),
        }
        bindings_by_request_id[request_id] = _json_payload(binding)
        if selected_release is not None:
            releases_by_id[str(selected_release.id)] = selected_release
    return bindings_by_request_id, releases_by_id


def _latest_release_audit_bundles_by_release(
    session: Session,
    release_ids: Iterable[UUID],
) -> dict[UUID, AuditBundleExport]:
    ids = _uuid_values(release_ids)
    if not ids:
        return {}
    rows = list(
        session.scalars(
            select(AuditBundleExport)
            .where(
                AuditBundleExport.search_harness_release_id.in_(ids),
                AuditBundleExport.bundle_kind == "search_harness_release_provenance",
                AuditBundleExport.export_status == "completed",
            )
            .order_by(
                AuditBundleExport.search_harness_release_id.asc(),
                AuditBundleExport.created_at.desc(),
                AuditBundleExport.id.asc(),
            )
        )
    )
    latest_by_release: dict[UUID, AuditBundleExport] = {}
    for row in rows:
        if row.search_harness_release_id is not None:
            latest_by_release.setdefault(row.search_harness_release_id, row)
    return latest_by_release


def _latest_passed_receipts_by_bundle(
    session: Session,
    bundle_ids: Iterable[UUID],
) -> dict[UUID, AuditBundleValidationReceipt]:
    ids = _uuid_values(bundle_ids)
    if not ids:
        return {}
    rows = list(
        session.scalars(
            select(AuditBundleValidationReceipt)
            .where(
                AuditBundleValidationReceipt.audit_bundle_export_id.in_(ids),
                AuditBundleValidationReceipt.validation_status == "passed",
            )
            .order_by(
                AuditBundleValidationReceipt.audit_bundle_export_id.asc(),
                AuditBundleValidationReceipt.created_at.desc(),
                AuditBundleValidationReceipt.id.asc(),
            )
        )
    )
    latest_by_bundle: dict[UUID, AuditBundleValidationReceipt] = {}
    for row in rows:
        latest_by_bundle.setdefault(row.audit_bundle_export_id, row)
    return latest_by_bundle


def _claim_source_values(
    claim: dict[str, Any],
    *,
    cards_by_id: dict[str, dict[str, Any]],
    field_name: str,
) -> list[str]:
    return _string_values(
        [
            *(claim.get(field_name) or []),
            *[
                value
                for card_id in claim.get("evidence_card_ids") or []
                for value in (cards_by_id.get(str(card_id), {}).get(field_name) or [])
            ],
        ]
    )


def _claim_derivation_provenance_lock_contract_mismatches(
    row: ClaimEvidenceDerivation,
) -> list[str]:
    lock = dict(row.provenance_lock_json or {})
    if not lock:
        return ["provenance_lock"]
    mismatches: list[str] = []
    if lock.get("schema_name") != "technical_report_claim_provenance_lock":
        mismatches.append("schema_name")
    if lock.get("schema_version") != "1.0":
        mismatches.append("schema_version")
    if str(lock.get("claim_id") or "") != str(row.claim_id):
        mismatches.append("claim_id")
    row_values = {
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
    }
    for field_name in _CLAIM_PROVENANCE_LOCK_LIST_FIELDS:
        if _string_values(lock.get(field_name) or []) != _string_values(row_values[field_name]):
            mismatches.append(field_name)
    coverage = dict(lock.get("coverage") or {})
    coverage_fields = {
        "source_search_request_count": "source_search_request_ids",
        "source_search_request_result_count": "source_search_request_result_ids",
        "source_evidence_package_export_count": "source_evidence_package_export_ids",
        "semantic_ontology_snapshot_count": "semantic_ontology_snapshot_ids",
        "semantic_graph_snapshot_count": "semantic_graph_snapshot_ids",
        "retrieval_reranker_artifact_count": "retrieval_reranker_artifact_ids",
        "search_harness_release_count": "search_harness_release_ids",
        "release_audit_bundle_count": "release_audit_bundle_ids",
        "release_validation_receipt_count": "release_validation_receipt_ids",
    }
    for coverage_key, field_name in coverage_fields.items():
        if coverage.get(coverage_key) != len(_string_values(lock.get(field_name) or [])):
            mismatches.append(f"coverage.{coverage_key}")
    return mismatches


def _claim_derivation_support_judgment_contract_mismatches(
    row: ClaimEvidenceDerivation,
) -> list[str]:
    judgment = dict(row.support_judgment_json or {})
    if not judgment:
        return ["support_judgment"]
    mismatches: list[str] = []
    if judgment.get("schema_name") != "technical_report_claim_support_judgment":
        mismatches.append("schema_name")
    if judgment.get("schema_version") != "1.0":
        mismatches.append("schema_version")
    if judgment.get("judge_kind") != "deterministic_claim_support_v1":
        mismatches.append("judge_kind")
    if str(judgment.get("claim_id") or "") != str(row.claim_id):
        mismatches.append("claim_id")
    if judgment.get("verdict") != row.support_verdict:
        mismatches.append("verdict")
    try:
        judgment_score = float(judgment.get("support_score"))
    except (TypeError, ValueError):
        mismatches.append("support_score")
    else:
        if row.support_score is None or abs(judgment_score - row.support_score) > 0.0001:
            mismatches.append("support_score")
    if _string_values(judgment.get("source_search_request_result_ids") or []) != (
        row.source_search_request_result_ids_json or []
    ):
        mismatches.append("source_search_request_result_ids")
    if sorted(_string_values(judgment.get("evidence_card_ids") or [])) != sorted(
        row.evidence_card_ids_json or []
    ):
        mismatches.append("evidence_card_ids")
    if sorted(_string_values(judgment.get("graph_edge_ids") or [])) != sorted(
        row.graph_edge_ids_json or []
    ):
        mismatches.append("graph_edge_ids")
    return mismatches


def _apply_technical_report_claim_provenance_locks(
    session: Session,
    draft_payload: dict[str, Any],
) -> None:
    cards_by_id = {
        str(card.get("evidence_card_id")): dict(card)
        for card in draft_payload.get("evidence_cards", [])
        if card.get("evidence_card_id")
    }
    graph_snapshot_by_edge_id = {
        str(edge.get("edge_id")): edge.get("graph_snapshot_id")
        for edge in draft_payload.get("graph_context") or []
        if edge.get("edge_id") and edge.get("graph_snapshot_id")
    }
    all_fact_ids = _uuid_values(
        fact_id
        for claim in draft_payload.get("claims") or []
        for fact_id in (claim.get("fact_ids") or [])
    )
    fact_ontology_by_id: dict[str, str] = {}
    if all_fact_ids:
        facts = session.scalars(select(SemanticFact).where(SemanticFact.id.in_(all_fact_ids)))
        fact_ontology_by_id = {
            str(row.id): str(row.ontology_snapshot_id)
            for row in facts
            if row.ontology_snapshot_id is not None
        }

    all_graph_snapshot_ids = _uuid_values(graph_snapshot_by_edge_id.values())
    graph_snapshot_ontology_by_id: dict[str, str] = {}
    if all_graph_snapshot_ids:
        graph_snapshots = session.scalars(
            select(SemanticGraphSnapshot).where(
                SemanticGraphSnapshot.id.in_(all_graph_snapshot_ids)
            )
        )
        graph_snapshot_ontology_by_id = {
            str(row.id): str(row.ontology_snapshot_id)
            for row in graph_snapshots
            if row.ontology_snapshot_id is not None
        }

    all_search_request_ids = _uuid_values(
        request_id
        for claim in draft_payload.get("claims") or []
        for request_id in _claim_source_values(
            claim,
            cards_by_id=cards_by_id,
            field_name="source_search_request_ids",
        )
    )
    request_rows_by_id: dict[str, SearchRequestRecord] = {}
    if all_search_request_ids:
        requests = session.scalars(
            select(SearchRequestRecord).where(SearchRequestRecord.id.in_(all_search_request_ids))
        )
        request_rows_by_id = {str(row.id): row for row in requests}

    release_bindings_by_request_id, releases_by_id = _latest_passed_release_bindings_by_request(
        session,
        request_rows_by_id,
    )
    release_ids = _uuid_values(row.id for row in releases_by_id.values())
    reranker_artifacts_by_release: dict[str, list[RetrievalRerankerArtifact]] = {
        str(release_id): [] for release_id in release_ids
    }
    if release_ids:
        reranker_rows = session.scalars(
            select(RetrievalRerankerArtifact)
            .where(RetrievalRerankerArtifact.search_harness_release_id.in_(release_ids))
            .order_by(
                RetrievalRerankerArtifact.search_harness_release_id.asc(),
                RetrievalRerankerArtifact.created_at.desc(),
                RetrievalRerankerArtifact.id.asc(),
            )
        )
        for row in reranker_rows:
            if row.search_harness_release_id is not None:
                reranker_artifacts_by_release.setdefault(
                    str(row.search_harness_release_id), []
                ).append(row)
    audit_bundles_by_release = _latest_release_audit_bundles_by_release(session, release_ids)
    receipts_by_bundle = _latest_passed_receipts_by_bundle(
        session,
        (row.id for row in audit_bundles_by_release.values()),
    )

    all_lock_sha256s: list[str] = []
    all_ontology_snapshot_ids: list[str] = []
    all_graph_snapshot_ids_for_claims: list[str] = []
    all_reranker_artifact_ids: list[str] = []
    all_release_ids: list[str] = []
    all_audit_bundle_ids: list[str] = []
    all_receipt_ids: list[str] = []

    for claim in draft_payload.get("claims") or []:
        source_search_request_ids = _id_str_values(
            _claim_source_values(
                claim,
                cards_by_id=cards_by_id,
                field_name="source_search_request_ids",
            )
        )
        source_search_request_result_ids = _id_str_values(
            _claim_source_values(
                claim,
                cards_by_id=cards_by_id,
                field_name="source_search_request_result_ids",
            )
        )
        source_evidence_package_export_ids = _id_str_values(
            _claim_source_values(
                claim,
                cards_by_id=cards_by_id,
                field_name="source_evidence_package_export_ids",
            )
        )
        source_evidence_package_sha256s = _string_values(
            _claim_source_values(
                claim,
                cards_by_id=cards_by_id,
                field_name="source_evidence_package_sha256s",
            )
        )
        source_evidence_trace_sha256s = _string_values(
            _claim_source_values(
                claim,
                cards_by_id=cards_by_id,
                field_name="source_evidence_trace_sha256s",
            )
        )
        semantic_graph_snapshot_ids = _id_str_values(
            graph_snapshot_by_edge_id.get(str(edge_id))
            for edge_id in claim.get("graph_edge_ids") or []
        )
        semantic_ontology_snapshot_ids = _id_str_values(
            [
                *[fact_ontology_by_id.get(str(fact_id)) for fact_id in claim.get("fact_ids") or []],
                *[
                    graph_snapshot_ontology_by_id.get(str(snapshot_id))
                    for snapshot_id in semantic_graph_snapshot_ids
                ],
            ]
        )
        source_search_request_release_bindings = [
            release_bindings_by_request_id[request_id]
            for request_id in source_search_request_ids
            if request_id in release_bindings_by_request_id
        ]
        claim_release_ids = _id_str_values(
            binding.get("search_harness_release_id")
            for binding in source_search_request_release_bindings
        )
        retrieval_reranker_artifact_ids = _id_str_values(
            row.id
            for release_id in claim_release_ids
            for row in reranker_artifacts_by_release.get(str(release_id), [])
        )
        release_audit_bundle_ids = _id_str_values(
            audit_bundles_by_release[UUID(str(release_id))].id
            for release_id in claim_release_ids
            if UUID(str(release_id)) in audit_bundles_by_release
        )
        release_validation_receipt_ids = _id_str_values(
            receipts_by_bundle[UUID(str(bundle_id))].id
            for bundle_id in release_audit_bundle_ids
            if UUID(str(bundle_id)) in receipts_by_bundle
        )
        provenance_lock = {
            "schema_name": "technical_report_claim_provenance_lock",
            "schema_version": "1.0",
            "claim_id": str(claim.get("claim_id") or ""),
            "source_search_request_ids": source_search_request_ids,
            "source_search_request_result_ids": source_search_request_result_ids,
            "source_evidence_package_export_ids": source_evidence_package_export_ids,
            "source_evidence_package_sha256s": source_evidence_package_sha256s,
            "source_evidence_trace_sha256s": source_evidence_trace_sha256s,
            "semantic_ontology_snapshot_ids": semantic_ontology_snapshot_ids,
            "semantic_graph_snapshot_ids": semantic_graph_snapshot_ids,
            "retrieval_reranker_artifact_ids": retrieval_reranker_artifact_ids,
            "search_harness_release_ids": claim_release_ids,
            "source_search_request_release_bindings": (source_search_request_release_bindings),
            "release_audit_bundle_ids": release_audit_bundle_ids,
            "release_validation_receipt_ids": release_validation_receipt_ids,
            "coverage": {
                "source_search_request_count": len(source_search_request_ids),
                "source_search_request_result_count": len(source_search_request_result_ids),
                "source_evidence_package_export_count": len(source_evidence_package_export_ids),
                "semantic_ontology_snapshot_count": len(semantic_ontology_snapshot_ids),
                "semantic_graph_snapshot_count": len(semantic_graph_snapshot_ids),
                "retrieval_reranker_artifact_count": len(retrieval_reranker_artifact_ids),
                "search_harness_release_count": len(claim_release_ids),
                "release_audit_bundle_count": len(release_audit_bundle_ids),
                "release_validation_receipt_count": len(release_validation_receipt_ids),
            },
        }
        provenance_lock_sha256 = str(payload_sha256(provenance_lock) or "")
        claim["source_search_request_ids"] = source_search_request_ids
        claim["source_search_request_result_ids"] = source_search_request_result_ids
        claim["source_evidence_package_export_ids"] = source_evidence_package_export_ids
        claim["source_evidence_package_sha256s"] = source_evidence_package_sha256s
        claim["source_evidence_trace_sha256s"] = source_evidence_trace_sha256s
        claim["semantic_ontology_snapshot_ids"] = semantic_ontology_snapshot_ids
        claim["semantic_graph_snapshot_ids"] = semantic_graph_snapshot_ids
        claim["retrieval_reranker_artifact_ids"] = retrieval_reranker_artifact_ids
        claim["search_harness_release_ids"] = claim_release_ids
        claim["release_audit_bundle_ids"] = release_audit_bundle_ids
        claim["release_validation_receipt_ids"] = release_validation_receipt_ids
        claim["provenance_lock"] = provenance_lock
        claim["provenance_lock_sha256"] = provenance_lock_sha256

        all_lock_sha256s.append(provenance_lock_sha256)
        all_ontology_snapshot_ids.extend(semantic_ontology_snapshot_ids)
        all_graph_snapshot_ids_for_claims.extend(semantic_graph_snapshot_ids)
        all_reranker_artifact_ids.extend(retrieval_reranker_artifact_ids)
        all_release_ids.extend(claim_release_ids)
        all_audit_bundle_ids.extend(release_audit_bundle_ids)
        all_receipt_ids.extend(release_validation_receipt_ids)

    draft_payload["semantic_ontology_snapshot_ids"] = _id_str_values(all_ontology_snapshot_ids)
    draft_payload["semantic_graph_snapshot_ids"] = _id_str_values(all_graph_snapshot_ids_for_claims)
    draft_payload["retrieval_reranker_artifact_ids"] = _id_str_values(all_reranker_artifact_ids)
    draft_payload["search_harness_release_ids"] = _id_str_values(all_release_ids)
    draft_payload["release_audit_bundle_ids"] = _id_str_values(all_audit_bundle_ids)
    draft_payload["release_validation_receipt_ids"] = _id_str_values(all_receipt_ids)
    draft_payload["provenance_lock_sha256s"] = _string_values(all_lock_sha256s)
    claim_count = len(draft_payload.get("claims") or [])
    draft_payload["provenance_lock_summary"] = {
        "schema_name": "technical_report_provenance_lock_summary",
        "schema_version": "1.0",
        "claim_count": claim_count,
        "claims_with_provenance_lock_count": len(
            [
                claim
                for claim in draft_payload.get("claims") or []
                if claim.get("provenance_lock_sha256")
            ]
        ),
        "source_search_request_result_id_count": len(
            _id_str_values(
                result_id
                for claim in draft_payload.get("claims") or []
                for result_id in (claim.get("source_search_request_result_ids") or [])
            )
        ),
        "semantic_ontology_snapshot_id_count": len(draft_payload["semantic_ontology_snapshot_ids"]),
        "semantic_graph_snapshot_id_count": len(draft_payload["semantic_graph_snapshot_ids"]),
        "retrieval_reranker_artifact_id_count": len(
            draft_payload["retrieval_reranker_artifact_ids"]
        ),
        "search_harness_release_id_count": len(draft_payload["search_harness_release_ids"]),
        "release_audit_bundle_id_count": len(draft_payload["release_audit_bundle_ids"]),
        "release_validation_receipt_id_count": len(draft_payload["release_validation_receipt_ids"]),
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


def persist_technical_report_evidence_export(
    session: Session,
    *,
    draft_payload: dict[str, Any],
    agent_task_id: UUID,
    agent_task_artifact_id: UUID | None = None,
) -> EvidencePackageExport:
    _apply_technical_report_claim_provenance_locks(session, draft_payload)
    package = apply_technical_report_derivation_links(draft_payload)
    now = utcnow()
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


def _claim_derivation_payload(row: ClaimEvidenceDerivation) -> dict:
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
