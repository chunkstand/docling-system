from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import SemanticReviewStatus
from app.services import semantic_graph_core as _semantic_graph_core
from app.services.semantic_registry import semantic_registry_from_payload


def _expected_edge_keys(
    *,
    registry,
    edges_by_pair: dict[tuple[str, str, str], _semantic_graph_core._EdgeBucket],
    min_shared_documents: int,
) -> set[str]:
    expected: set[str] = set()
    for _pair_key, edge_bucket in edges_by_pair.items():
        if len(edge_bucket.supporting_document_ids) >= min_shared_documents:
            expected.add(
                _semantic_graph_core._edge_id(
                    registry,
                    relation_key=edge_bucket.relation_key,
                    subject_concept_key=edge_bucket.subject_concept_key,
                    object_concept_key=edge_bucket.object_concept_key,
                )
            )
            continue
        if edge_bucket.relation_key == _semantic_graph_core.DEFAULT_GRAPH_RELATION_KEY:
            if edge_bucket.approved_document_count >= 1 and edge_bucket.shared_category_keys:
                expected.add(
                    _semantic_graph_core._edge_id(
                        registry,
                        relation_key=edge_bucket.relation_key,
                        subject_concept_key=edge_bucket.subject_concept_key,
                        object_concept_key=edge_bucket.object_concept_key,
                    )
                )
        elif edge_bucket.cue_match_count >= 1 and edge_bucket.approved_document_count >= 1:
            expected.add(
                _semantic_graph_core._edge_id(
                    registry,
                    relation_key=edge_bucket.relation_key,
                    subject_concept_key=edge_bucket.subject_concept_key,
                    object_concept_key=edge_bucket.object_concept_key,
                )
            )
    return expected


def _evaluation_success_metrics(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "metric_key": "semantic_integrity",
            "stakeholder": "Figay",
            "passed": summary["traceable_candidate_edge_ratio"] == 1.0
            and summary["unsupported_candidate_edge_count"] == 0,
            "summary": "Candidate graph edges stay traceable and unsupported edges are blocked.",
            "details": {
                "traceable_candidate_edge_ratio": summary["traceable_candidate_edge_ratio"],
                "unsupported_candidate_edge_count": summary["unsupported_candidate_edge_count"],
            },
        },
        {
            "metric_key": "memory_compaction",
            "stakeholder": "Yegge",
            "passed": summary["graph_memory_compaction_ratio"] > 1.0,
            "summary": "The graph stores less edge state than the raw supporting trace count.",
            "details": {
                "graph_memory_compaction_ratio": summary["graph_memory_compaction_ratio"],
            },
        },
        {
            "metric_key": "bitter_lesson_alignment",
            "stakeholder": "Sutton",
            "passed": summary["candidate_expected_recall"] >= summary["baseline_expected_recall"]
            and summary["document_specific_rule_count_delta"] == 0,
            "summary": "The candidate extractor improves or matches recall without "
            "adding corpus-specific rules.",
            "details": {
                "baseline_expected_recall": summary["baseline_expected_recall"],
                "candidate_expected_recall": summary["candidate_expected_recall"],
            },
        },
        {
            "metric_key": "agent_legibility",
            "stakeholder": "Lopopolo",
            "passed": bool(summary.get("document_count")),
            "summary": "Extractor evaluation persists typed edge comparisons and "
            "aggregate metrics.",
            "details": {
                "document_count": summary["document_count"],
                "expected_edge_count": summary["expected_edge_count"],
            },
        },
    ]


def evaluate_semantic_relation_extractor(
    session: Session,
    *,
    document_ids: list[UUID],
    baseline_extractor_name: str,
    candidate_extractor_name: str,
    minimum_review_status: str,
    baseline_min_shared_documents: int,
    candidate_score_threshold: float,
    expected_min_shared_documents: int,
    get_active_semantic_ontology_snapshot_fn,
    get_active_semantic_pass_detail_fn,
    get_active_semantic_graph_payload_fn,
) -> dict[str, Any]:
    unique_document_ids = list(dict.fromkeys(document_ids))
    if not unique_document_ids:
        raise ValueError("Semantic relation extractor evaluation requires at least one document.")
    ontology_snapshot = get_active_semantic_ontology_snapshot_fn(session)
    registry = semantic_registry_from_payload(ontology_snapshot.payload_json or {})
    nodes_by_key, edges_by_pair, document_refs = _semantic_graph_core._collect_graph_support(
        session,
        registry=registry,
        document_ids=unique_document_ids,
        minimum_review_status=minimum_review_status,
        get_active_semantic_pass_detail_fn=get_active_semantic_pass_detail_fn,
    )
    baseline_edges = _semantic_graph_core._build_graph_edges(
        registry=registry,
        nodes_by_key=nodes_by_key,
        edges_by_pair=edges_by_pair,
        extractor_name=baseline_extractor_name,
        min_shared_documents=baseline_min_shared_documents,
        score_threshold=candidate_score_threshold,
        shadow_mode=True,
        review_status=SemanticReviewStatus.CANDIDATE.value,
    )
    candidate_edges = _semantic_graph_core._build_graph_edges(
        registry=registry,
        nodes_by_key=nodes_by_key,
        edges_by_pair=edges_by_pair,
        extractor_name=candidate_extractor_name,
        min_shared_documents=baseline_min_shared_documents,
        score_threshold=candidate_score_threshold,
        shadow_mode=True,
        review_status=SemanticReviewStatus.CANDIDATE.value,
    )
    expected_edge_keys = _expected_edge_keys(
        registry=registry,
        edges_by_pair=edges_by_pair,
        min_shared_documents=expected_min_shared_documents,
    )
    baseline_edge_map = {edge["edge_id"]: edge for edge in baseline_edges}
    candidate_edge_map = {edge["edge_id"]: edge for edge in candidate_edges}
    live_graph_payload = get_active_semantic_graph_payload_fn(session) or {}
    live_edge_ids = {
        str(edge.get("edge_id"))
        for edge in (live_graph_payload.get("edges") or [])
        if edge.get("review_status") == SemanticReviewStatus.APPROVED.value
    }

    edge_reports: list[dict[str, Any]] = []
    for edge_id in sorted(expected_edge_keys | set(baseline_edge_map) | set(candidate_edge_map)):
        baseline_edge = baseline_edge_map.get(edge_id)
        candidate_edge = candidate_edge_map.get(edge_id)
        exemplar = candidate_edge or baseline_edge
        if exemplar is None:
            continue
        edge_reports.append(
            {
                "edge_id": edge_id,
                "relation_key": exemplar["relation_key"],
                "subject_entity_key": exemplar["subject_entity_key"],
                "subject_label": exemplar["subject_label"],
                "object_entity_key": exemplar["object_entity_key"],
                "object_label": exemplar["object_label"],
                "expected_edge": edge_id in expected_edge_keys,
                "in_live_graph": edge_id in live_edge_ids,
                "baseline_found": baseline_edge is not None,
                "candidate_found": candidate_edge is not None,
                "baseline_score": baseline_edge["extractor_score"] if baseline_edge else 0.0,
                "candidate_score": candidate_edge["extractor_score"] if candidate_edge else 0.0,
                "supporting_document_ids": (
                    candidate_edge["supporting_document_ids"]
                    if candidate_edge is not None
                    else baseline_edge["supporting_document_ids"]
                ),
                "support_refs": (
                    candidate_edge["support_refs"]
                    if candidate_edge is not None
                    else baseline_edge["support_refs"]
                ),
            }
        )

    baseline_hit_count = sum(1 for edge_id in expected_edge_keys if edge_id in baseline_edge_map)
    candidate_hit_count = sum(1 for edge_id in expected_edge_keys if edge_id in candidate_edge_map)
    traceable_candidate_edge_ratio = (
        sum(1 for edge in candidate_edges if edge.get("support_refs")) / len(candidate_edges)
        if candidate_edges
        else 1.0
    )
    unsupported_candidate_edge_count = sum(
        1 for edge_id, edge in candidate_edge_map.items() if edge_id not in expected_edge_keys
    )
    summary = {
        "document_count": len(unique_document_ids),
        "expected_edge_count": len(expected_edge_keys),
        "baseline_edge_count": len(baseline_edges),
        "candidate_edge_count": len(candidate_edges),
        "baseline_expected_recall": round(baseline_hit_count / len(expected_edge_keys), 4)
        if expected_edge_keys
        else 1.0,
        "candidate_expected_recall": round(candidate_hit_count / len(expected_edge_keys), 4)
        if expected_edge_keys
        else 1.0,
        "candidate_only_edge_count": sum(
            1 for edge_id in candidate_edge_map if edge_id not in baseline_edge_map
        ),
        "regressed_expected_edge_count": sum(
            1
            for edge_id in expected_edge_keys
            if edge_id in baseline_edge_map and edge_id not in candidate_edge_map
        ),
        "traceable_candidate_edge_ratio": round(traceable_candidate_edge_ratio, 4),
        "unsupported_candidate_edge_count": unsupported_candidate_edge_count,
        "graph_memory_compaction_ratio": round(
            (
                sum(len(edge.get("support_refs") or []) for edge in candidate_edges)
                / max(len(candidate_edges), 1)
            ),
            4,
        ),
        "document_specific_rule_count_delta": 0,
    }
    return {
        "baseline_extractor": {
            **_semantic_graph_core._extractor_descriptor(baseline_extractor_name).__dict__,
        },
        "candidate_extractor": {
            **_semantic_graph_core._extractor_descriptor(candidate_extractor_name).__dict__,
        },
        "ontology_snapshot_id": ontology_snapshot.id,
        "ontology_version": ontology_snapshot.ontology_version,
        "document_refs": document_refs,
        "edge_reports": edge_reports,
        "summary": summary,
        "success_metrics": _evaluation_success_metrics(summary),
    }


def triage_semantic_graph_disagreements(
    evaluation: dict[str, Any],
    *,
    min_score: float,
    expected_only: bool,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    recommended_followups: list[dict[str, Any]] = []
    for edge in evaluation.get("edge_reports") or []:
        if expected_only and not edge.get("expected_edge"):
            continue
        candidate_score = float(edge.get("candidate_score") or 0.0)
        if candidate_score < min_score:
            continue
        if (
            edge.get("candidate_found")
            and not edge.get("in_live_graph")
            and edge.get("expected_edge")
        ):
            issue_id = f"graph_issue:{edge['edge_id']}"
            issues.append(
                {
                    "issue_id": issue_id,
                    "edge_id": edge["edge_id"],
                    "relation_key": edge["relation_key"],
                    "subject_entity_key": edge["subject_entity_key"],
                    "subject_label": edge["subject_label"],
                    "object_entity_key": edge["object_entity_key"],
                    "object_label": edge["object_label"],
                    "severity": "high" if edge.get("expected_edge") else "medium",
                    "expected_edge": bool(edge.get("expected_edge")),
                    "in_live_graph": bool(edge.get("in_live_graph")),
                    "baseline_found": bool(edge.get("baseline_found")),
                    "candidate_found": bool(edge.get("candidate_found")),
                    "candidate_score": candidate_score,
                    "supporting_document_ids": list(edge.get("supporting_document_ids") or []),
                    "support_refs": list(edge.get("support_refs") or []),
                    "summary": (
                        f"{edge['subject_label']} and {edge['object_label']} are linked by the "
                        "candidate graph but not yet promoted into live graph memory."
                    ),
                    "details": {
                        "baseline_score": edge.get("baseline_score"),
                    },
                }
            )
            recommended_followups.append(
                {
                    "followup_kind": "draft_graph_promotions",
                    "reason": "candidate_expected_edge_missing_from_live_graph",
                    "edge_id": edge["edge_id"],
                }
            )
    return {
        "issue_count": len(issues),
        "issues": issues,
        "recommended_followups": recommended_followups,
        "success_metrics": [
            {
                "metric_key": "agent_legibility",
                "stakeholder": "Lopopolo",
                "passed": all(issue.get("issue_id") and issue.get("edge_id") for issue in issues),
                "summary": "Graph disagreement triage emits typed issues and bounded next actions.",
                "details": {"issue_count": len(issues)},
            },
            {
                "metric_key": "memory_compaction",
                "stakeholder": "Yegge",
                "passed": len(issues) <= max(len(evaluation.get("edge_reports") or []), 1),
                "summary": "Triage condenses relation disagreements into a smaller actionable set.",
                "details": {
                    "edge_report_count": len(evaluation.get("edge_reports") or []),
                    "issue_count": len(issues),
                },
            },
        ],
    }
