from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.json_utils import json_object_payload as _json_payload
from app.db.public.audit_and_evidence import AuditBundleExport, AuditBundleValidationReceipt
from app.db.public.retrieval import (
    RetrievalRerankerArtifact,
    SearchHarnessRelease,
    SearchRequestRecord,
)
from app.db.public.semantic_memory import SemanticFact, SemanticGraphSnapshot
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
            "source_search_request_release_bindings": source_search_request_release_bindings,
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


latest_passed_release_bindings_by_request = _latest_passed_release_bindings_by_request
apply_technical_report_claim_provenance_locks = _apply_technical_report_claim_provenance_locks
