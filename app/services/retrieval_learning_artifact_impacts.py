from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.coercion import maybe_uuid as _maybe_uuid
from app.core.json_utils import canonical_json_value as _json_payload
from app.db.public.audit_and_evidence import (
    ClaimEvidenceDerivation,
    EvidenceTraceEdge,
    EvidenceTraceNode,
)
from app.db.public.retrieval import RetrievalTrainingRun, SearchHarnessRelease
from app.schemas.search import SearchHarnessEvaluationResponse, SearchHarnessReleaseResponse
from app.services.semantic_governance import (
    search_harness_release_semantic_governance_context,
)


def _training_reference_set(training_run: RetrievalTrainingRun) -> dict[str, Any]:
    payload = training_run.training_payload_json or {}
    judgments = payload.get("judgments") if isinstance(payload, dict) else []
    hard_negatives = payload.get("hard_negatives") if isinstance(payload, dict) else []
    uuid_refs: set[UUID] = set()
    content_hashes: set[str] = set()
    source_payload_hashes: set[str] = set()
    result_type_counts: Counter[str] = Counter()
    source_type_counts: Counter[str] = Counter()
    for row in [*judgments, *hard_negatives]:
        if not isinstance(row, dict):
            continue
        if source_hash := row.get("source_payload_sha256"):
            source_payload_hashes.add(str(source_hash))
            content_hashes.add(str(source_hash))
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        query = row.get("query") if isinstance(row.get("query"), dict) else {}
        for key in (
            "source_ref_id",
            "search_feedback_id",
            "search_replay_query_id",
            "search_replay_run_id",
            "evaluation_query_id",
            "source_search_request_id",
            "search_request_id",
            "search_request_result_id",
        ):
            if value := _maybe_uuid(source.get(key)):
                uuid_refs.add(value)
        for key in ("result_id", "document_id", "run_id"):
            if value := _maybe_uuid(result.get(key)):
                uuid_refs.add(value)
        if result_type := result.get("result_type"):
            result_type_counts[str(result_type)] += 1
        if source_type := source.get("source_type"):
            source_type_counts[str(source_type)] += 1
        if query_hash := query.get("query_sha256"):
            content_hashes.add(str(query_hash))
        for evidence_ref in result.get("evidence_refs") or []:
            if not isinstance(evidence_ref, dict):
                continue
            for key in (
                "search_request_result_span_id",
                "retrieval_evidence_span_id",
                "source_id",
            ):
                if value := _maybe_uuid(evidence_ref.get(key)):
                    uuid_refs.add(value)
            for key in ("content_sha256", "source_snapshot_sha256"):
                if value := evidence_ref.get(key):
                    content_hashes.add(str(value))
    return {
        "uuid_refs": uuid_refs,
        "content_hashes": content_hashes,
        "source_payload_hashes": source_payload_hashes,
        "result_type_counts": dict(sorted(result_type_counts.items())),
        "source_type_counts": dict(sorted(source_type_counts.items())),
    }


def _trace_owner_predicates(rows: list[EvidenceTraceNode]):
    manifest_ids = {row.evidence_manifest_id for row in rows if row.evidence_manifest_id}
    export_ids = {
        row.evidence_package_export_id for row in rows if row.evidence_package_export_id
    }
    predicates = []
    if manifest_ids:
        predicates.append(EvidenceTraceNode.evidence_manifest_id.in_(manifest_ids))
    if export_ids:
        predicates.append(EvidenceTraceNode.evidence_package_export_id.in_(export_ids))
    return predicates, manifest_ids, export_ids


def change_impact_report(
    session: Session,
    *,
    artifact_id: UUID,
    artifact_payload: dict[str, Any],
    artifact_sha256: str,
    training_run: RetrievalTrainingRun,
    evaluation: SearchHarnessEvaluationResponse,
    release: SearchHarnessReleaseResponse,
) -> dict[str, Any]:
    refs = _training_reference_set(training_run)
    uuid_refs = refs["uuid_refs"]
    content_hashes = refs["content_hashes"]
    matching_trace_nodes: list[EvidenceTraceNode] = []
    if uuid_refs or content_hashes:
        predicates = []
        if uuid_refs:
            predicates.append(EvidenceTraceNode.source_id.in_(uuid_refs))
        if content_hashes:
            predicates.append(EvidenceTraceNode.content_sha256.in_(content_hashes))
        matching_trace_nodes = (
            session.execute(select(EvidenceTraceNode).where(or_(*predicates)).limit(200))
            .scalars()
            .all()
        )
    owner_predicates, manifest_ids, export_ids = _trace_owner_predicates(matching_trace_nodes)
    owner_nodes: list[EvidenceTraceNode] = []
    owner_edges: list[EvidenceTraceEdge] = []
    if owner_predicates:
        owner_nodes = (
            session.execute(select(EvidenceTraceNode).where(or_(*owner_predicates)).limit(500))
            .scalars()
            .all()
        )
        edge_predicates = []
        if manifest_ids:
            edge_predicates.append(EvidenceTraceEdge.evidence_manifest_id.in_(manifest_ids))
        if export_ids:
            edge_predicates.append(EvidenceTraceEdge.evidence_package_export_id.in_(export_ids))
        owner_edges = (
            session.execute(select(EvidenceTraceEdge).where(or_(*edge_predicates)).limit(500))
            .scalars()
            .all()
            if edge_predicates
            else []
        )
    claim_nodes = [
        row
        for row in owner_nodes
        if row.node_kind in {"technical_report_claim", "claim_derivation"}
    ][:50]
    derivations = (
        session.execute(
            select(ClaimEvidenceDerivation)
            .where(ClaimEvidenceDerivation.evidence_package_export_id.in_(export_ids))
            .limit(100)
        )
        .scalars()
        .all()
        if export_ids
        else []
    )
    release_row = session.get(SearchHarnessRelease, release.release_id)
    semantic_policy = (
        search_harness_release_semantic_governance_context(session, release_row)["policy"]
        if release_row is not None
        else {}
    )
    return _json_payload(
        {
            "schema_name": "retrieval_reranker_change_impact_report",
            "schema_version": "1.0",
            "artifact": {
                "artifact_id": artifact_id,
                "artifact_sha256": artifact_sha256,
                "artifact_name": artifact_payload["artifact_name"],
                "artifact_version": artifact_payload["artifact_version"],
                "candidate_harness_name": artifact_payload["candidate_harness_name"],
                "base_harness_name": artifact_payload["base_harness_name"],
            },
            "changed_state_refs": {
                "retrieval_training_run_id": training_run.id,
                "judgment_set_id": training_run.judgment_set_id,
                "training_dataset_sha256": training_run.training_dataset_sha256,
                "search_harness_evaluation_id": evaluation.evaluation_id,
                "search_harness_release_id": release.release_id,
                "semantic_policy": semantic_policy,
            },
            "source_reference_summary": {
                "uuid_ref_count": len(uuid_refs),
                "content_hash_count": len(content_hashes),
                "source_payload_hash_count": len(refs["source_payload_hashes"]),
                "result_type_counts": refs["result_type_counts"],
                "source_type_counts": refs["source_type_counts"],
            },
            "affected_trace_summary": {
                "matching_trace_node_count": len(matching_trace_nodes),
                "owner_trace_node_count": len(owner_nodes),
                "owner_trace_edge_count": len(owner_edges),
                "affected_claim_count": len(claim_nodes),
                "affected_derivation_count": len(derivations),
            },
            "affected_claims": [
                {
                    "node_id": row.id,
                    "node_key": row.node_key,
                    "node_kind": row.node_kind,
                    "source_table": row.source_table,
                    "source_id": row.source_id,
                    "content_sha256": row.content_sha256,
                }
                for row in claim_nodes
            ],
            "affected_derivations": [
                {
                    "derivation_id": row.id,
                    "claim_id": row.claim_id,
                    "derivation_rule": row.derivation_rule,
                    "derivation_sha256": row.derivation_sha256,
                }
                for row in derivations
            ],
            "impact_policy": {
                "scope": "ranking_artifact_to_training_sources_and_trace_owners",
                "requires_release_gate": True,
                "requires_semantic_governance_context": True,
                "requires_trace_recheck_when_affected_claim_count_gt_zero": True,
            },
        }
    )
