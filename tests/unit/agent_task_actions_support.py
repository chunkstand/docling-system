from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.semantics import DocumentSemanticPassResponse


def _draft_output_payload(*, draft_task_id, draft_harness_name="wide_v2_review") -> dict:
    return {
        "draft": {
            "draft_harness_name": draft_harness_name,
            "base_harness_name": "wide_v2",
            "source_task_id": None,
            "source_task_type": None,
            "rationale": "publish review harness",
            "override_spec": {
                "base_harness_name": "wide_v2",
                "retrieval_profile_overrides": {"keyword_candidate_multiplier": 9},
                "reranker_overrides": {"result_type_priority_bonus": 0.009},
                "override_type": "draft_harness_config_update",
                "override_source": "task_draft",
                "draft_task_id": str(draft_task_id),
                "source_task_id": None,
                "rationale": "publish review harness",
            },
            "effective_harness_config": {"base_harness_name": "wide_v2"},
        },
        "artifact_id": str(uuid4()),
        "artifact_kind": "harness_config_draft",
        "artifact_path": "/tmp/harness_config_draft.json",
    }

def _verification_output_payload(
    *,
    verification_task_id,
    draft_task_id,
    draft_harness_name="wide_v2_review",
    outcome="passed",
) -> dict:
    return {
        "draft": _draft_output_payload(
            draft_task_id=draft_task_id,
            draft_harness_name=draft_harness_name,
        )["draft"],
        "evaluation": {
            "baseline_harness_name": "wide_v2",
            "total_regressed_count": 0,
            "total_improved_count": 1,
        },
        "verification": {
            "verification_id": str(uuid4()),
            "target_task_id": str(draft_task_id),
            "verification_task_id": str(verification_task_id),
            "verifier_type": "draft_harness_config_gate",
            "outcome": outcome,
            "metrics": {"total_shared_query_count": 10},
            "reasons": [],
            "details": {"draft_harness_name": draft_harness_name},
            "created_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        },
        "artifact_id": str(uuid4()),
        "artifact_kind": "harness_config_draft_verification",
        "artifact_path": "/tmp/harness_config_draft_verification.json",
    }

def _resolve_payload_by_expected_type(
    resolver_payloads: dict[str, SimpleNamespace],
    expected_task_type: str | tuple[str, ...],
) -> SimpleNamespace:
    if isinstance(expected_task_type, tuple):
        for task_type in expected_task_type:
            if task_type in resolver_payloads:
                return resolver_payloads[task_type]
    return resolver_payloads[expected_task_type]

def _semantic_pass_response() -> DocumentSemanticPassResponse:
    now = datetime.now(UTC)
    return DocumentSemanticPassResponse(
        semantic_pass_id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        status="completed",
        registry_version="semantics-layer-foundation-alpha.2",
        registry_sha256="registry-sha",
        extractor_version="semantics_sidecar_v2_1",
        artifact_schema_version="2.1",
        baseline_run_id=None,
        baseline_semantic_pass_id=None,
        has_json_artifact=True,
        has_yaml_artifact=True,
        artifact_json_sha256="json-sha",
        artifact_yaml_sha256="yaml-sha",
        assertion_count=0,
        evidence_count=0,
        summary={"concept_keys": []},
        evaluation_status="completed",
        evaluation_fixture_name="semantic_fixture",
        evaluation_version=2,
        evaluation_summary={"all_expectations_passed": True, "expectations": []},
        continuity_summary={"reason": "no_prior_active_run", "change_count": 0},
        error_message=None,
        created_at=now,
        completed_at=now,
        concept_category_bindings=[],
        assertions=[],
    )

def _graph_support_ref(*, document_id) -> dict:
    return {
        "support_ref_id": f"graph-support:{document_id}",
        "document_id": str(document_id),
        "run_id": str(uuid4()),
        "semantic_pass_id": str(uuid4()),
        "assertion_ids": [str(uuid4()), str(uuid4())],
        "evidence_ids": [str(uuid4())],
        "concept_keys": ["integration_threshold", "integration_owner"],
        "source_types": ["chunk", "table"],
        "shared_category_keys": ["integration_governance"],
        "score": 0.72,
    }

def _shadow_graph_output_payload(*, document_ids, artifact_id=None) -> dict:
    ontology_snapshot_id = uuid4()
    support_refs = [_graph_support_ref(document_id=document_id) for document_id in document_ids]
    return {
        "shadow_graph": {
            "graph_name": "workspace_semantic_graph",
            "graph_version": "shadow:portable-upper-ontology-v1:relation_ranker_v1:2",
            "ontology_snapshot_id": str(ontology_snapshot_id),
            "ontology_version": "portable-upper-ontology-v1",
            "ontology_sha256": "ontology-sha",
            "upper_ontology_version": "portable-upper-ontology-v1",
            "extractor": {
                "extractor_name": "relation_ranker_v1",
                "backing_model": "hashing_embedding_v1",
                "match_strategy": "relation_ranker_v1",
                "shadow_mode": True,
                "provider_name": "local_hashing",
            },
            "shadow_mode": True,
            "minimum_review_status": "approved",
            "document_ids": [str(document_id) for document_id in document_ids],
            "document_count": len(document_ids),
            "document_refs": [
                {
                    "document_id": str(document_id),
                    "run_id": str(uuid4()),
                    "semantic_pass_id": str(uuid4()),
                    "registry_version": "portable-upper-ontology-v1.1",
                    "registry_sha256": "registry-sha",
                    "ontology_snapshot_id": str(ontology_snapshot_id),
                }
                for document_id in document_ids
            ],
            "node_count": 2,
            "edge_count": 1,
            "nodes": [
                {
                    "entity_key": "concept:integration_owner",
                    "concept_key": "integration_owner",
                    "preferred_label": "Integration Owner",
                    "category_keys": ["integration_governance"],
                    "document_ids": [str(document_id) for document_id in document_ids],
                    "document_count": len(document_ids),
                    "source_types": ["chunk"],
                    "review_status_counts": {"approved": len(document_ids)},
                    "assertion_count": len(document_ids),
                    "evidence_count": len(document_ids),
                },
                {
                    "entity_key": "concept:integration_threshold",
                    "concept_key": "integration_threshold",
                    "preferred_label": "Integration Threshold",
                    "category_keys": ["integration_governance"],
                    "document_ids": [str(document_id) for document_id in document_ids],
                    "document_count": len(document_ids),
                    "source_types": ["chunk", "table"],
                    "review_status_counts": {"approved": len(document_ids)},
                    "assertion_count": len(document_ids),
                    "evidence_count": len(document_ids),
                },
            ],
            "edges": [
                {
                    "edge_id": (
                        "graph_edge:concept_related_to_concept:"
                        "concept:integration_owner:concept:integration_threshold"
                    ),
                    "relation_key": "concept_related_to_concept",
                    "relation_label": "Concept Related To Concept",
                    "subject_entity_key": "concept:integration_owner",
                    "subject_label": "Integration Owner",
                    "object_entity_key": "concept:integration_threshold",
                    "object_label": "Integration Threshold",
                    "epistemic_status": "shadow_candidate",
                    "review_status": "candidate",
                    "support_level": "supported",
                    "extractor_name": "relation_ranker_v1",
                    "extractor_score": 0.72,
                    "supporting_document_ids": [str(document_id) for document_id in document_ids],
                    "supporting_document_count": len(document_ids),
                    "supporting_assertion_count": 4,
                    "supporting_evidence_count": len(document_ids),
                    "shared_category_keys": ["integration_governance"],
                    "source_types": ["chunk", "table"],
                    "support_refs": support_refs,
                    "details": {"approved_document_count": len(document_ids)},
                }
            ],
            "summary": {
                "relation_key_counts": {"concept_related_to_concept": 1},
                "traceable_edge_count": 1,
                "support_ref_count": len(document_ids),
            },
            "success_metrics": [
                {
                    "metric_key": "semantic_integrity",
                    "stakeholder": "Figay",
                    "passed": True,
                    "summary": (
                        "Every graph edge stays evidence-backed and explicitly status-stamped."
                    ),
                    "details": {"traceable_edge_ratio": 1.0, "edge_count": 1},
                }
            ],
        },
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "shadow_semantic_graph",
        "artifact_path": "/tmp/shadow_semantic_graph.json",
    }

def _semantic_relation_evaluation_output_payload(*, document_ids, artifact_id=None) -> dict:
    edge = _shadow_graph_output_payload(document_ids=document_ids)["shadow_graph"]["edges"][0]
    return {
        "baseline_extractor": {
            "extractor_name": "cooccurrence_v1",
            "backing_model": "none",
            "match_strategy": "cooccurrence_min_shared_documents_v1",
            "shadow_mode": True,
            "provider_name": None,
        },
        "candidate_extractor": {
            "extractor_name": "relation_ranker_v1",
            "backing_model": "hashing_embedding_v1",
            "match_strategy": "relation_ranker_v1",
            "shadow_mode": True,
            "provider_name": "local_hashing",
        },
        "ontology_snapshot_id": str(uuid4()),
        "ontology_version": "portable-upper-ontology-v1.1",
        "document_refs": [
            {
                "document_id": str(document_id),
                "run_id": str(uuid4()),
                "semantic_pass_id": str(uuid4()),
                "registry_version": "portable-upper-ontology-v1.1",
                "registry_sha256": "registry-sha",
                "ontology_snapshot_id": str(uuid4()),
            }
            for document_id in document_ids
        ],
        "edge_reports": [
            {
                "edge_id": edge["edge_id"],
                "relation_key": edge["relation_key"],
                "subject_entity_key": edge["subject_entity_key"],
                "subject_label": edge["subject_label"],
                "object_entity_key": edge["object_entity_key"],
                "object_label": edge["object_label"],
                "expected_edge": True,
                "in_live_graph": False,
                "baseline_found": False,
                "candidate_found": True,
                "baseline_score": 0.0,
                "candidate_score": 0.72,
                "supporting_document_ids": edge["supporting_document_ids"],
                "support_refs": edge["support_refs"],
            }
        ],
        "summary": {
            "document_count": len(document_ids),
            "expected_edge_count": 1,
            "baseline_edge_count": 0,
            "candidate_edge_count": 1,
            "baseline_expected_recall": 0.0,
            "candidate_expected_recall": 1.0,
            "candidate_only_edge_count": 1,
            "regressed_expected_edge_count": 0,
            "traceable_candidate_edge_ratio": 1.0,
            "unsupported_candidate_edge_count": 0,
            "graph_memory_compaction_ratio": 2.0,
            "document_specific_rule_count_delta": 0,
        },
        "success_metrics": [
            {
                "metric_key": "bitter_lesson_alignment",
                "stakeholder": "Sutton",
                "passed": True,
                "summary": (
                    "The candidate extractor improves or matches recall without "
                    "adding corpus-specific rules."
                ),
                "details": {"baseline_expected_recall": 0.0, "candidate_expected_recall": 1.0},
            }
        ],
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "semantic_relation_evaluation",
        "artifact_path": "/tmp/semantic_relation_evaluation.json",
    }

def _graph_triage_output_payload(
    *, evaluation_task_id, verification_task_id, artifact_id=None
) -> dict:
    document_ids = [uuid4(), uuid4()]
    evaluation = _semantic_relation_evaluation_output_payload(document_ids=document_ids)
    edge = evaluation["edge_reports"][0]
    return {
        "evaluation_task_id": str(evaluation_task_id),
        "disagreement_report": {
            "issue_count": 1,
            "issues": [
                {
                    "issue_id": f"graph_issue:{edge['edge_id']}",
                    "edge_id": edge["edge_id"],
                    "relation_key": edge["relation_key"],
                    "subject_entity_key": edge["subject_entity_key"],
                    "subject_label": edge["subject_label"],
                    "object_entity_key": edge["object_entity_key"],
                    "object_label": edge["object_label"],
                    "severity": "high",
                    "expected_edge": True,
                    "in_live_graph": False,
                    "baseline_found": False,
                    "candidate_found": True,
                    "candidate_score": 0.72,
                    "supporting_document_ids": edge["supporting_document_ids"],
                    "support_refs": edge["support_refs"],
                    "summary": (
                        "Integration Owner and Integration Threshold should be promoted "
                        "into graph memory."
                    ),
                    "details": {"baseline_score": 0.0},
                }
            ],
            "recommended_followups": [
                {
                    "followup_kind": "draft_graph_promotions",
                    "reason": "candidate_expected_edge_missing_from_live_graph",
                    "edge_id": edge["edge_id"],
                }
            ],
            "success_metrics": [
                {
                    "metric_key": "agent_legibility",
                    "stakeholder": "Lopopolo",
                    "passed": True,
                    "summary": (
                        "Graph disagreement triage emits typed issues and bounded next actions."
                    ),
                    "details": {"issue_count": 1},
                }
            ],
        },
        "verification": {
            "verification_id": str(uuid4()),
            "target_task_id": str(verification_task_id),
            "verification_task_id": str(verification_task_id),
            "verifier_type": "semantic_graph_shadow_gate",
            "outcome": "passed",
            "metrics": {"issue_count": 1},
            "reasons": [],
            "details": {"evaluation_task_id": str(evaluation_task_id), "issue_count": 1},
            "created_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        },
        "recommendation": {"next_action": "draft_graph_promotions", "priority": "high"},
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "semantic_graph_disagreement_report",
        "artifact_path": "/tmp/semantic_graph_disagreement_report.json",
    }

def _draft_graph_output_payload(*, source_task_id, source_task_type, artifact_id=None) -> dict:
    document_ids = [uuid4(), uuid4()]
    shadow_graph = _shadow_graph_output_payload(document_ids=document_ids)["shadow_graph"]
    promoted_edge = {
        **shadow_graph["edges"][0],
        "epistemic_status": "approved_graph",
        "review_status": "approved",
    }
    effective_graph = {
        **shadow_graph,
        "graph_version": "portable-upper-ontology-v1.1.graph.1",
        "shadow_mode": False,
        "extractor": {
            "extractor_name": "approved_graph_memory",
            "backing_model": "none",
            "match_strategy": "approved_promotion",
            "shadow_mode": False,
            "provider_name": None,
        },
        "edges": [promoted_edge],
    }
    return {
        "draft": {
            "base_snapshot_id": None,
            "base_graph_version": None,
            "proposed_graph_version": "portable-upper-ontology-v1.1.graph.1",
            "ontology_snapshot_id": shadow_graph["ontology_snapshot_id"],
            "ontology_version": shadow_graph["ontology_version"],
            "ontology_sha256": shadow_graph["ontology_sha256"],
            "source_task_id": str(source_task_id),
            "source_task_type": source_task_type,
            "rationale": "Promote approved cross-document graph memory.",
            "promoted_edges": [promoted_edge],
            "effective_graph": effective_graph,
            "success_metrics": [
                {
                    "metric_key": "semantic_integrity",
                    "stakeholder": "Figay",
                    "passed": True,
                    "summary": "Draft promotions only contain traceable graph edges.",
                    "details": {"promoted_edge_count": 1},
                }
            ],
        },
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "semantic_graph_promotion_draft",
        "artifact_path": "/tmp/semantic_graph_promotion_draft.json",
    }

def _verify_graph_output_payload(*, draft_task_id, verification_task_id, artifact_id=None) -> dict:
    draft_output = _draft_graph_output_payload(
        source_task_id=uuid4(),
        source_task_type="triage_semantic_graph_disagreements",
    )["draft"]
    return {
        "draft": draft_output,
        "summary": {
            "promoted_edge_count": 1,
            "supported_edge_count": 1,
            "stale_edge_count": 0,
            "unsupported_edge_count": 0,
            "ontology_mismatch_count": 0,
            "conflict_count": 0,
            "traceable_edge_ratio": 1.0,
        },
        "success_metrics": [
            {
                "metric_key": "semantic_integrity",
                "stakeholder": "Figay",
                "passed": True,
                "summary": "Only fully traceable, supported graph edges pass verification.",
                "details": {"traceable_edge_ratio": 1.0, "unsupported_edge_count": 0},
            }
        ],
        "verification": {
            "verification_id": str(uuid4()),
            "target_task_id": str(draft_task_id),
            "verification_task_id": str(verification_task_id),
            "verifier_type": "semantic_graph_promotion_gate",
            "outcome": "passed",
            "metrics": {
                "promoted_edge_count": 1,
                "supported_edge_count": 1,
                "stale_edge_count": 0,
                "unsupported_edge_count": 0,
                "ontology_mismatch_count": 0,
                "conflict_count": 0,
            },
            "reasons": [],
            "details": {"supported_edge_count": 1},
            "created_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        },
        "artifact_id": str(artifact_id or uuid4()),
        "artifact_kind": "semantic_graph_promotion_verification",
        "artifact_path": "/tmp/semantic_graph_promotion_verification.json",
    }

def _semantic_generation_brief_output_payload(*, task_id, document_id) -> dict:
    return {
        "brief": {
            "document_kind": "knowledge_brief",
            "title": "Integration Governance Brief",
            "goal": "Summarize the knowledge base guidance on integration governance.",
            "audience": "Operators",
            "review_policy": "allow_candidate_with_disclosure",
            "target_length": "medium",
            "document_refs": [
                {
                    "document_id": str(document_id),
                    "run_id": str(uuid4()),
                    "semantic_pass_id": str(uuid4()),
                    "source_filename": "integration-one.pdf",
                    "title": "Integration One",
                    "registry_version": "semantics-layer-foundation-alpha.3",
                    "registry_sha256": "registry-sha",
                    "evaluation_fixture_name": "integration_fixture",
                    "evaluation_status": "completed",
                    "assertion_count": 1,
                    "evidence_count": 2,
                    "all_expectations_passed": True,
                }
            ],
            "selected_concept_keys": ["integration_threshold"],
            "selected_category_keys": ["integration_governance"],
            "semantic_dossier": [
                {
                    "concept_key": "integration_threshold",
                    "preferred_label": "Integration Threshold",
                    "category_keys": ["integration_governance"],
                    "category_labels": {"integration_governance": "Integration Governance"},
                    "document_ids": [str(document_id)],
                    "document_count": 1,
                    "evidence_count": 2,
                    "source_types": ["chunk", "table"],
                    "support_level": "supported",
                    "review_policy_status": "candidate_disclosed",
                    "disclosure_note": "Candidate-backed support requires review.",
                    "assertions": [
                        {
                            "document_id": str(document_id),
                            "run_id": str(uuid4()),
                            "semantic_pass_id": str(uuid4()),
                            "assertion_id": str(uuid4()),
                            "concept_key": "integration_threshold",
                            "preferred_label": "Integration Threshold",
                            "review_status": "candidate",
                            "support_level": "supported",
                            "source_types": ["chunk", "table"],
                            "evidence_count": 2,
                            "category_keys": ["integration_governance"],
                            "category_labels": ["Integration Governance"],
                        }
                    ],
                    "evidence_refs": [
                        {
                            "citation_label": "E1",
                            "document_id": str(document_id),
                            "run_id": str(uuid4()),
                            "semantic_pass_id": str(uuid4()),
                            "assertion_id": str(uuid4()),
                            "evidence_id": str(uuid4()),
                            "concept_key": "integration_threshold",
                            "preferred_label": "Integration Threshold",
                            "review_status": "candidate",
                            "source_filename": "integration-one.pdf",
                            "source_type": "chunk",
                            "page_from": 1,
                            "page_to": 1,
                            "excerpt": "Integration threshold guidance remains in force.",
                            "source_artifact_api_path": "/documents/example/chunks/1",
                            "matched_terms": ["integration threshold"],
                        }
                    ],
                }
            ],
            "sections": [
                {
                    "section_id": "section:integration_governance",
                    "title": "Integration Governance",
                    "summary": (
                        "This section covers one semantic concept from the selected corpus scope."
                    ),
                    "focus_concept_keys": ["integration_threshold"],
                    "focus_category_keys": ["integration_governance"],
                    "claim_ids": ["claim:integration_threshold"],
                }
            ],
            "claim_candidates": [
                {
                    "claim_id": "claim:integration_threshold",
                    "section_id": "section:integration_governance",
                    "summary": (
                        "Integration Threshold appears in Integration One with "
                        "2 evidence items across chunk and table sources."
                    ),
                    "concept_keys": ["integration_threshold"],
                    "assertion_ids": [str(uuid4())],
                    "evidence_labels": ["E1"],
                    "source_document_ids": [str(document_id)],
                    "support_level": "supported",
                    "review_policy_status": "candidate_disclosed",
                    "disclosure_note": "Candidate-backed support requires review.",
                }
            ],
            "evidence_pack": [
                {
                    "citation_label": "E1",
                    "document_id": str(document_id),
                    "run_id": str(uuid4()),
                    "semantic_pass_id": str(uuid4()),
                    "assertion_id": str(uuid4()),
                    "evidence_id": str(uuid4()),
                    "concept_key": "integration_threshold",
                    "preferred_label": "Integration Threshold",
                    "review_status": "candidate",
                    "source_filename": "integration-one.pdf",
                    "source_type": "chunk",
                    "page_from": 1,
                    "page_to": 1,
                    "excerpt": "Integration threshold guidance remains in force.",
                    "source_artifact_api_path": "/documents/example/chunks/1",
                    "matched_terms": ["integration threshold"],
                }
            ],
            "warnings": [],
            "success_metrics": [
                {
                    "metric_key": "agent_legibility",
                    "stakeholder": "Lopopolo",
                    "passed": True,
                    "summary": "Typed brief ready",
                    "details": {},
                }
            ],
        },
        "artifact_id": str(uuid4()),
        "artifact_kind": "semantic_generation_brief",
        "artifact_path": "/tmp/semantic_generation_brief.json",
    }

def _semantic_candidate_evaluation_output_payload(*, document_id: str | None = None) -> dict:
    document_id = document_id or str(uuid4())
    return {
        "baseline_extractor": {
            "extractor_name": "registry_lexical_v1",
            "backing_model": "none",
            "match_strategy": "normalized_phrase_contains",
            "shadow_mode": True,
            "provider_name": None,
        },
        "candidate_extractor": {
            "extractor_name": "concept_ranker_v1",
            "backing_model": "hashing_embedding_v1",
            "match_strategy": "token_set_ranker_v1",
            "shadow_mode": True,
            "provider_name": "local_hashing",
        },
        "document_reports": [
            {
                "document_id": document_id,
                "run_id": str(uuid4()),
                "semantic_pass_id": str(uuid4()),
                "registry_version": "semantics-layer-foundation-alpha.4",
                "registry_sha256": "registry-sha",
                "evaluation_fixture_name": "integration-fixture",
                "expected_concept_keys": ["integration_threshold", "integration_owner"],
                "live_concept_keys": ["integration_threshold"],
                "baseline_predicted_concept_keys": ["integration_threshold"],
                "candidate_predicted_concept_keys": [
                    "integration_owner",
                    "integration_threshold",
                ],
                "improved_expected_concept_keys": ["integration_owner"],
                "regressed_expected_concept_keys": [],
                "candidate_only_concept_keys": ["integration_owner"],
                "shadow_candidates": [
                    {
                        "concept_key": "integration_owner",
                        "preferred_label": "Integration Owner",
                        "max_score": 0.71,
                        "source_count": 1,
                        "source_types": ["chunk"],
                        "category_keys": ["integration_governance"],
                        "expected_by_evaluation": True,
                        "evidence_refs": [
                            {
                                "source_type": "chunk",
                                "source_locator": "chunk-1",
                                "page_from": 1,
                                "page_to": 1,
                                "excerpt": "Owners for integration approve changes.",
                                "source_artifact_api_path": None,
                                "source_artifact_sha256": "chunk-sha",
                                "score": 0.71,
                            }
                        ],
                        "note": "Shadow candidate aligns with a semantic evaluation expectation.",
                    }
                ],
                "source_predictions": [
                    {
                        "source_key": "chunk:chunk-1",
                        "source_type": "chunk",
                        "source_locator": "chunk-1",
                        "page_from": 1,
                        "page_to": 1,
                        "excerpt": "Owners for integration approve changes.",
                        "source_artifact_api_path": None,
                        "source_artifact_sha256": "chunk-sha",
                        "candidates": [
                            {
                                "concept_key": "integration_owner",
                                "preferred_label": "Integration Owner",
                                "score": 0.71,
                                "matched_terms": ["Integration Owner"],
                                "category_keys": ["integration_governance"],
                            }
                        ],
                    }
                ],
                "summary": {
                    "baseline_expected_recall": 0.5,
                    "candidate_expected_recall": 1.0,
                    "expected_concept_count": 2,
                    "candidate_source_prediction_count": 1,
                    "baseline_source_prediction_count": 1,
                    "improved_expected_concept_count": 1,
                    "regressed_expected_concept_count": 0,
                },
            }
        ],
        "summary": {
            "document_count": 1,
            "expected_concept_count": 2,
            "baseline_expected_recall": 0.5,
            "candidate_expected_recall": 1.0,
            "improved_expected_concept_count": 1,
            "regressed_expected_concept_count": 0,
            "candidate_only_concept_count": 1,
            "live_mutation_performed": False,
            "score_threshold": 0.34,
            "max_candidates_per_source": 3,
        },
        "success_metrics": [
            {
                "metric_key": "bitter_lesson_alignment",
                "stakeholder": "Sutton",
                "passed": True,
                "summary": "Recall improved.",
                "details": {},
            }
        ],
        "artifact_id": str(uuid4()),
        "artifact_kind": "semantic_candidate_evaluation",
        "artifact_path": "/tmp/semantic_candidate_evaluation.json",
    }
