from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.coercion import maybe_uuid as _maybe_uuid
from app.core.hashes import payload_sha256 as _payload_sha256
from app.core.json_utils import canonical_json_value as _json_payload
from app.core.time import utcnow
from app.db.models import (
    ClaimEvidenceDerivation,
    EvidenceTraceEdge,
    EvidenceTraceNode,
    RetrievalJudgmentKind,
    RetrievalLearningCandidateEvaluation,
    RetrievalRerankerArtifact,
    RetrievalTrainingRun,
    SearchHarnessRelease,
    SemanticGovernanceEventKind,
)
from app.schemas.search import (
    RetrievalLearningCandidateEvaluationRequest,
    RetrievalRerankerArtifactRequest,
    RetrievalRerankerArtifactResponse,
    RetrievalRerankerArtifactSummaryResponse,
    SearchHarnessEvaluationRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessReleaseGateRequest,
    SearchHarnessReleaseResponse,
)
from app.services.retrieval_learning_candidates import (
    candidate_not_found_error,
    create_candidate_evaluation_row,
    learning_candidate_package,
    resolve_training_run,
    thresholds_from_candidate_request,
    to_candidate_response,
)
from app.services.semantic_governance import (
    record_semantic_governance_event,
    search_harness_release_semantic_governance_context,
)

RETRIEVAL_RERANKER_ARTIFACT_SCHEMA = "retrieval_reranker_artifact"
RETRIEVAL_RERANKER_ARTIFACT_SCHEMA_VERSION = "1.0"
RETRIEVAL_RERANKER_ARTIFACT_KIND = "linear_feature_weight_candidate"


def reranker_artifact_not_found_error(artifact_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "retrieval_reranker_artifact_not_found",
        "Retrieval reranker artifact not found.",
        artifact_id=str(artifact_id),
    )


def candidate_request_from_artifact_request(
    request: RetrievalRerankerArtifactRequest,
) -> RetrievalLearningCandidateEvaluationRequest:
    return RetrievalLearningCandidateEvaluationRequest(
        retrieval_training_run_id=request.retrieval_training_run_id,
        candidate_harness_name=request.candidate_harness_name,
        baseline_harness_name=request.baseline_harness_name,
        source_types=list(request.source_types),
        limit=request.limit,
        max_total_regressed_count=request.max_total_regressed_count,
        max_mrr_drop=request.max_mrr_drop,
        max_zero_result_count_increase=request.max_zero_result_count_increase,
        max_foreign_top_result_count_increase=(
            request.max_foreign_top_result_count_increase
        ),
        min_total_shared_query_count=request.min_total_shared_query_count,
        requested_by=request.requested_by,
        review_note=request.review_note,
    )


def _bounded_float(value: float, *, lower: float, upper: float) -> float:
    return round(max(lower, min(upper, value)), 6)


def _rows_from_training_payload(
    training_run: RetrievalTrainingRun,
) -> tuple[list[dict], list[dict]]:
    payload = training_run.training_payload_json or {}
    judgments = payload.get("judgments") if isinstance(payload, dict) else []
    hard_negatives = payload.get("hard_negatives") if isinstance(payload, dict) else []
    return (
        [row for row in judgments or [] if isinstance(row, dict)],
        [row for row in hard_negatives or [] if isinstance(row, dict)],
    )


def _numeric_feature_average(rows: list[dict], feature_name: str) -> float:
    values: list[float] = []
    for row in rows:
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        features = result.get("rerank_features") if isinstance(result, dict) else {}
        value = features.get(feature_name) if isinstance(features, dict) else None
        if isinstance(value, int | float):
            values.append(float(value))
    if not values:
        return 0.0
    return sum(values) / len(values)


def _result_type_rate(rows: list[dict], result_type: str) -> float:
    typed = [
        row
        for row in rows
        if isinstance(row.get("result"), dict) and row["result"].get("result_type")
    ]
    if not typed:
        return 0.0
    return sum(1 for row in typed if row["result"].get("result_type") == result_type) / len(
        typed
    )


def feature_weight_candidate(
    *,
    training_run: RetrievalTrainingRun,
    base_harness_name: str,
    candidate_harness_name: str,
    artifact_name: str,
    get_search_harness_fn: Callable[[str], Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    base_harness = get_search_harness_fn(base_harness_name)
    base_reranker = base_harness.reranker_config.snapshot()
    judgments, hard_negatives = _rows_from_training_payload(training_run)
    positive_judgments = [
        row for row in judgments if row.get("judgment_kind") == RetrievalJudgmentKind.POSITIVE.value
    ]
    pressure = {
        "positive_table_rate": _result_type_rate(positive_judgments, "table"),
        "hard_negative_table_rate": _result_type_rate(hard_negatives, "table"),
        "positive_chunk_rate": _result_type_rate(positive_judgments, "chunk"),
        "hard_negative_chunk_rate": _result_type_rate(hard_negatives, "chunk"),
    }
    feature_map = {
        "tabular_table_signal": "tabular_table_bonus",
        "title_token_coverage": "title_token_coverage_bonus",
        "source_filename_token_coverage": "source_filename_token_coverage_bonus",
        "document_title_token_coverage": "document_title_token_coverage_bonus",
        "document_cluster_strength": "prose_document_cluster_bonus",
        "heading_token_coverage": "heading_token_coverage_bonus",
        "phrase_overlap": "phrase_overlap_bonus",
        "rare_token_overlap": "rare_token_overlap_bonus",
        "adjacent_chunk_context_signal": "adjacent_chunk_context_bonus",
        "exact_filter_priority": "exact_filter_bonus",
    }
    deltas: dict[str, float] = {}
    observations: dict[str, Any] = {
        "feature_signal_count": len(positive_judgments) + len(hard_negatives),
        "result_type_pressure": pressure,
        "feature_deltas": {},
    }
    for feature_name, weight_name in feature_map.items():
        positive_avg = _numeric_feature_average(positive_judgments, feature_name)
        negative_avg = _numeric_feature_average(hard_negatives, feature_name)
        feature_delta = positive_avg - negative_avg
        observations["feature_deltas"][feature_name] = {
            "positive_average": round(positive_avg, 6),
            "hard_negative_average": round(negative_avg, 6),
            "delta": round(feature_delta, 6),
        }
        if feature_delta <= 0:
            continue
        base_value = float(base_reranker.get(weight_name) or 0.0)
        deltas[weight_name] = _bounded_float(feature_delta * 0.01, lower=0.0, upper=0.015)
        deltas[weight_name] = _bounded_float(
            deltas[weight_name],
            lower=0.0,
            upper=max(0.015, base_value),
        )

    type_pressure = max(
        abs(pressure["positive_table_rate"] - pressure["hard_negative_table_rate"]),
        abs(pressure["positive_chunk_rate"] - pressure["hard_negative_chunk_rate"]),
    )
    hard_negative_pressure = min(training_run.hard_negative_count, 10) / 10
    result_type_delta = max(0.001, (type_pressure + hard_negative_pressure) * 0.004)
    deltas["result_type_priority_bonus"] = _bounded_float(
        result_type_delta,
        lower=0.001,
        upper=0.012,
    )

    proposed_reranker_overrides = {
        key: _bounded_float(float(base_reranker.get(key) or 0.0) + delta, lower=0.0, upper=5.0)
        for key, delta in sorted(deltas.items())
    }
    feature_weights = {
        "schema_name": "retrieval_reranker_feature_weights",
        "schema_version": "1.0",
        "base_harness_name": base_harness_name,
        "base_reranker_name": base_harness.reranker_name,
        "base_reranker_version": base_harness.reranker_version,
        "candidate_harness_name": candidate_harness_name,
        "artifact_name": artifact_name,
        "training_dataset_sha256": training_run.training_dataset_sha256,
        "training_example_count": training_run.example_count,
        "positive_count": training_run.positive_count,
        "negative_count": training_run.negative_count,
        "missing_count": training_run.missing_count,
        "hard_negative_count": training_run.hard_negative_count,
        "observations": observations,
        "base_reranker_config": base_reranker,
        "proposed_reranker_overrides": proposed_reranker_overrides,
    }
    override_spec = {
        "base_harness_name": base_harness_name,
        "override_type": "retrieval_reranker_artifact",
        "override_source": "retrieval_learning",
        "rationale": (
            "Data-derived linear reranker candidate from persisted judgments and "
            "hard negatives."
        ),
        "reranker_overrides": proposed_reranker_overrides,
        "retrieval_profile_overrides": {},
    }
    harness_overrides = {candidate_harness_name: override_spec}
    return feature_weights, harness_overrides, override_spec


def _training_reference_set(training_run: RetrievalTrainingRun) -> dict[str, Any]:
    judgments, hard_negatives = _rows_from_training_payload(training_run)
    uuid_refs: set[UUID] = set()
    content_hashes: set[str] = set()
    source_payload_hashes: set[str] = set()
    result_type_counts: Counter[str] = Counter()
    source_type_counts: Counter[str] = Counter()
    for row in [*judgments, *hard_negatives]:
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


def _record_reranker_artifact_governance_event(
    session: Session,
    *,
    row: RetrievalRerankerArtifact,
    training_run: RetrievalTrainingRun,
) -> None:
    event = record_semantic_governance_event(
        session,
        event_kind=SemanticGovernanceEventKind.RETRIEVAL_RERANKER_ARTIFACT_MATERIALIZED.value,
        governance_scope=f"retrieval_reranker_artifact:{row.id}",
        subject_table="retrieval_reranker_artifacts",
        subject_id=row.id,
        search_harness_evaluation_id=row.search_harness_evaluation_id,
        search_harness_release_id=row.search_harness_release_id,
        event_payload={
            "retrieval_reranker_artifact": {
                "artifact_id": str(row.id),
                "artifact_kind": row.artifact_kind,
                "artifact_name": row.artifact_name,
                "artifact_version": row.artifact_version,
                "retrieval_training_run_id": str(training_run.id),
                "judgment_set_id": str(training_run.judgment_set_id),
                "candidate_evaluation_id": str(
                    row.retrieval_learning_candidate_evaluation_id
                ),
                "search_harness_evaluation_id": str(row.search_harness_evaluation_id),
                "search_harness_release_id": (
                    str(row.search_harness_release_id)
                    if row.search_harness_release_id is not None
                    else None
                ),
                "training_dataset_sha256": row.training_dataset_sha256,
                "artifact_sha256": row.artifact_sha256,
                "change_impact_sha256": row.change_impact_sha256,
                "gate_outcome": row.gate_outcome,
                "feature_weights": row.feature_weights_json or {},
                "harness_overrides": row.harness_overrides_json or {},
            }
        },
        deduplication_key=(
            f"retrieval_reranker_artifact_materialized:{row.id}:"
            f"{row.artifact_sha256}:{row.change_impact_sha256}"
        ),
        created_by=row.created_by,
    )
    row.semantic_governance_event_id = event.id
    session.flush()


def to_reranker_artifact_summary(
    row: RetrievalRerankerArtifact,
) -> RetrievalRerankerArtifactSummaryResponse:
    return RetrievalRerankerArtifactSummaryResponse(
        artifact_id=row.id,
        retrieval_training_run_id=row.retrieval_training_run_id,
        judgment_set_id=row.judgment_set_id,
        retrieval_learning_candidate_evaluation_id=(
            row.retrieval_learning_candidate_evaluation_id
        ),
        search_harness_evaluation_id=row.search_harness_evaluation_id,
        search_harness_release_id=row.search_harness_release_id,
        semantic_governance_event_id=row.semantic_governance_event_id,
        artifact_kind=row.artifact_kind,
        artifact_name=row.artifact_name,
        artifact_version=row.artifact_version,
        status=row.status,
        gate_outcome=row.gate_outcome,
        baseline_harness_name=row.baseline_harness_name,
        candidate_harness_name=row.candidate_harness_name,
        source_types=list(row.source_types_json or []),
        limit=row.limit,
        training_dataset_sha256=row.training_dataset_sha256,
        training_example_count=row.training_example_count,
        positive_count=row.positive_count,
        negative_count=row.negative_count,
        missing_count=row.missing_count,
        hard_negative_count=row.hard_negative_count,
        thresholds=row.thresholds_json or {},
        metrics=row.metrics_json or {},
        reasons=list(row.reasons_json or []),
        artifact_sha256=row.artifact_sha256,
        change_impact_sha256=row.change_impact_sha256,
        created_by=row.created_by,
        review_note=row.review_note,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )


def to_reranker_artifact_response(
    session: Session,
    row: RetrievalRerankerArtifact,
) -> RetrievalRerankerArtifactResponse:
    summary = to_reranker_artifact_summary(row)
    candidate = session.get(
        RetrievalLearningCandidateEvaluation,
        row.retrieval_learning_candidate_evaluation_id,
    )
    if candidate is None:
        raise candidate_not_found_error(row.retrieval_learning_candidate_evaluation_id)
    release = None
    if row.search_harness_release_id is not None and row.release_snapshot_json:
        release = SearchHarnessReleaseResponse.model_validate(row.release_snapshot_json)
    return RetrievalRerankerArtifactResponse(
        **summary.model_dump(),
        feature_weights=row.feature_weights_json or {},
        harness_overrides=row.harness_overrides_json or {},
        artifact=row.artifact_payload_json or {},
        change_impact_report=row.change_impact_report_json or {},
        evaluation=SearchHarnessEvaluationResponse.model_validate(
            row.evaluation_snapshot_json or {}
        ),
        release=release,
        candidate_evaluation=to_candidate_response(candidate),
    )


def create_retrieval_reranker_artifact(
    session: Session,
    request: RetrievalRerankerArtifactRequest,
    *,
    get_search_harness_fn: Callable[[str], Any],
    evaluate_search_harness_fn: Callable[..., SearchHarnessEvaluationResponse],
    record_search_harness_release_gate_fn: Callable[..., SearchHarnessReleaseResponse],
) -> RetrievalRerankerArtifactResponse:
    training_run = resolve_training_run(session, request.retrieval_training_run_id)
    created_at = utcnow()
    artifact_id = uuid.uuid4()
    artifact_name = request.artifact_name or (
        f"{request.candidate_harness_name}-reranker-{artifact_id.hex[:8]}"
    )
    try:
        feature_weights, harness_overrides, override_spec = feature_weight_candidate(
            training_run=training_run,
            base_harness_name=request.base_harness_name,
            candidate_harness_name=request.candidate_harness_name,
            artifact_name=artifact_name,
            get_search_harness_fn=get_search_harness_fn,
        )
    except ValueError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "search_harness_not_found",
            str(exc),
            base_harness_name=request.base_harness_name,
        ) from exc

    candidate_request = candidate_request_from_artifact_request(request)
    evaluation = evaluate_search_harness_fn(
        session,
        SearchHarnessEvaluationRequest(
            candidate_harness_name=request.candidate_harness_name,
            baseline_harness_name=request.baseline_harness_name,
            source_types=request.source_types,
            limit=request.limit,
        ),
        harness_overrides=harness_overrides,
    )
    if evaluation.evaluation_id is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "search_harness_evaluation_missing_id",
            "Reranker artifacts require a durable search harness evaluation.",
        )
    release = record_search_harness_release_gate_fn(
        session,
        evaluation,
        SearchHarnessReleaseGateRequest(
            evaluation_id=evaluation.evaluation_id,
            max_total_regressed_count=request.max_total_regressed_count,
            max_mrr_drop=request.max_mrr_drop,
            max_zero_result_count_increase=request.max_zero_result_count_increase,
            max_foreign_top_result_count_increase=(
                request.max_foreign_top_result_count_increase
            ),
            min_total_shared_query_count=request.min_total_shared_query_count,
            requested_by=request.requested_by,
            review_note=request.review_note,
        ),
        requested_by=request.requested_by,
        review_note=request.review_note,
    )
    candidate_package = learning_candidate_package(
        training_run=training_run,
        evaluation=evaluation,
        release=release,
        request=candidate_request,
    )
    candidate_row = create_candidate_evaluation_row(
        session,
        training_run=training_run,
        evaluation=evaluation,
        release=release,
        baseline_harness_name=request.baseline_harness_name,
        candidate_harness_name=request.candidate_harness_name,
        source_types=list(request.source_types),
        limit=request.limit,
        thresholds=thresholds_from_candidate_request(candidate_request),
        details={
            "schema_name": "retrieval_learning_candidate_evaluation_details",
            "schema_version": "1.0",
            "learning_loop_stage": "training_dataset_to_reranker_artifact_gate",
            "training_dataset_summary": training_run.summary_json or {},
            "reranker_artifact": {
                "artifact_id": str(artifact_id),
                "artifact_name": artifact_name,
                "artifact_kind": RETRIEVAL_RERANKER_ARTIFACT_KIND,
                "override_spec": override_spec,
            },
            "release_gate": {
                "outcome": release.outcome,
                "metrics": release.metrics,
                "reasons": release.reasons,
                "details": release.details,
            },
        },
        learning_package_sha256=_payload_sha256(candidate_package),
        created_by=request.requested_by,
        review_note=request.review_note,
        created_at=created_at,
    )

    artifact_version = (
        f"{request.candidate_harness_name}+{training_run.training_dataset_sha256[:12]}"
    )
    artifact_payload = _json_payload(
        {
            "schema_name": RETRIEVAL_RERANKER_ARTIFACT_SCHEMA,
            "schema_version": RETRIEVAL_RERANKER_ARTIFACT_SCHEMA_VERSION,
            "artifact_id": artifact_id,
            "artifact_kind": RETRIEVAL_RERANKER_ARTIFACT_KIND,
            "artifact_name": artifact_name,
            "artifact_version": artifact_version,
            "candidate_harness_name": request.candidate_harness_name,
            "base_harness_name": request.base_harness_name,
            "baseline_harness_name": request.baseline_harness_name,
            "retrieval_training_run": {
                "retrieval_training_run_id": training_run.id,
                "judgment_set_id": training_run.judgment_set_id,
                "training_dataset_sha256": training_run.training_dataset_sha256,
                "training_example_count": training_run.example_count,
            },
            "feature_weights": feature_weights,
            "harness_overrides": harness_overrides,
            "evaluation": evaluation.model_dump(mode="json"),
            "release": release.model_dump(mode="json"),
        }
    )
    artifact_sha256 = _payload_sha256(artifact_payload)
    impact_report = change_impact_report(
        session,
        artifact_id=artifact_id,
        artifact_payload=artifact_payload,
        artifact_sha256=artifact_sha256,
        training_run=training_run,
        evaluation=evaluation,
        release=release,
    )
    change_impact_sha256 = _payload_sha256(impact_report)
    row = RetrievalRerankerArtifact(
        id=artifact_id,
        retrieval_training_run_id=training_run.id,
        judgment_set_id=training_run.judgment_set_id,
        retrieval_learning_candidate_evaluation_id=candidate_row.id,
        search_harness_evaluation_id=evaluation.evaluation_id,
        search_harness_release_id=release.release_id,
        artifact_kind=RETRIEVAL_RERANKER_ARTIFACT_KIND,
        artifact_name=artifact_name,
        artifact_version=artifact_version,
        status="evaluated" if evaluation.status == "completed" else "failed",
        gate_outcome=release.outcome,
        baseline_harness_name=request.baseline_harness_name,
        candidate_harness_name=request.candidate_harness_name,
        source_types_json=list(request.source_types),
        limit=request.limit,
        training_dataset_sha256=training_run.training_dataset_sha256,
        training_example_count=training_run.example_count,
        positive_count=training_run.positive_count,
        negative_count=training_run.negative_count,
        missing_count=training_run.missing_count,
        hard_negative_count=training_run.hard_negative_count,
        thresholds_json=thresholds_from_candidate_request(candidate_request),
        metrics_json=release.metrics,
        reasons_json=list(release.reasons),
        feature_weights_json=feature_weights,
        harness_overrides_json=harness_overrides,
        artifact_payload_json=artifact_payload,
        evaluation_snapshot_json=evaluation.model_dump(mode="json"),
        release_snapshot_json=release.model_dump(mode="json"),
        change_impact_report_json=impact_report,
        artifact_sha256=artifact_sha256,
        change_impact_sha256=change_impact_sha256,
        created_by=request.requested_by,
        review_note=request.review_note,
        created_at=created_at,
        completed_at=created_at,
    )
    session.add(row)
    session.flush()
    _record_reranker_artifact_governance_event(
        session,
        row=row,
        training_run=training_run,
    )
    return to_reranker_artifact_response(session, row)


def list_retrieval_reranker_artifacts(
    session: Session,
    *,
    limit: int = 20,
    retrieval_training_run_id: UUID | None = None,
    candidate_harness_name: str | None = None,
) -> list[RetrievalRerankerArtifactSummaryResponse]:
    statement = select(RetrievalRerankerArtifact).order_by(
        RetrievalRerankerArtifact.created_at.desc()
    )
    if retrieval_training_run_id is not None:
        statement = statement.where(
            RetrievalRerankerArtifact.retrieval_training_run_id
            == retrieval_training_run_id
        )
    if candidate_harness_name:
        statement = statement.where(
            RetrievalRerankerArtifact.candidate_harness_name == candidate_harness_name
        )
    rows = session.execute(statement.limit(limit)).scalars().all()
    return [to_reranker_artifact_summary(row) for row in rows]


def get_retrieval_reranker_artifact_detail(
    session: Session,
    artifact_id: UUID,
) -> RetrievalRerankerArtifactResponse:
    row = session.get(RetrievalRerankerArtifact, artifact_id)
    if row is None:
        raise reranker_artifact_not_found_error(artifact_id)
    return to_reranker_artifact_response(session, row)
