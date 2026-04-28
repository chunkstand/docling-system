from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.db.models import AgentTask
from app.schemas.agent_tasks import (
    ApplyGraphPromotionsTaskInput,
    ApplyHarnessConfigUpdateTaskInput,
    ApplyOntologyExtensionTaskInput,
    ApplySemanticRegistryUpdateTaskInput,
    BuildDocumentFactGraphTaskInput,
    BuildShadowSemanticGraphTaskInput,
    DiscoverSemanticBootstrapCandidatesTaskInput,
    DraftGraphPromotionsTaskInput,
    DraftHarnessConfigFromOptimizationTaskInput,
    DraftHarnessConfigUpdateTaskInput,
    DraftOntologyExtensionTaskInput,
    DraftSemanticGroundedDocumentTaskInput,
    DraftSemanticRegistryUpdateTaskInput,
    EnqueueDocumentReprocessTaskInput,
    EvaluateClaimSupportJudgeTaskInput,
    EvaluateDocumentGenerationContextPackTaskInput,
    EvaluateSemanticCandidateExtractorTaskInput,
    EvaluateSemanticRelationExtractorTaskInput,
    ExportSemanticSupervisionCorpusTaskInput,
    GetActiveOntologySnapshotTaskInput,
    InitializeWorkspaceOntologyTaskInput,
    LatestSemanticPassTaskInput,
    OptimizeSearchHarnessFromCaseTaskInput,
    PrepareSemanticGenerationBriefTaskInput,
    TriageSemanticCandidateDisagreementsTaskInput,
    TriageSemanticGraphDisagreementsTaskInput,
    TriageSemanticPassTaskInput,
    VerifyDraftGraphPromotionsTaskInput,
    VerifyDraftHarnessConfigTaskInput,
    VerifyDraftOntologyExtensionTaskInput,
    VerifyDraftSemanticRegistryUpdateTaskInput,
    VerifySemanticGroundedDocumentTaskInput,
)
from app.schemas.documents import DocumentUploadResponse
from app.schemas.semantics import DocumentSemanticPassResponse
from app.services.agent_task_actions import (
    _apply_graph_promotions_executor,
    _apply_harness_config_update_executor,
    _apply_ontology_extension_executor,
    _apply_semantic_registry_update_executor,
    _build_document_fact_graph_executor,
    _build_shadow_semantic_graph_executor,
    _discover_semantic_bootstrap_candidates_executor,
    _draft_graph_promotions_executor,
    _draft_harness_config_from_optimization_executor,
    _draft_harness_config_update_executor,
    _draft_ontology_extension_executor,
    _draft_semantic_grounded_document_executor,
    _draft_semantic_registry_update_executor,
    _enqueue_document_reprocess_executor,
    _evaluate_semantic_candidate_extractor_executor,
    _evaluate_semantic_relation_extractor_executor,
    _export_semantic_supervision_corpus_executor,
    _get_active_ontology_snapshot_executor,
    _initialize_workspace_ontology_executor,
    _latest_semantic_pass_executor,
    _optimize_search_harness_from_case_executor,
    _prepare_semantic_generation_brief_executor,
    _triage_semantic_candidate_disagreements_executor,
    _triage_semantic_graph_disagreements_executor,
    _triage_semantic_pass_executor,
    _verify_draft_graph_promotions_executor,
    _verify_draft_harness_config_executor,
    _verify_draft_ontology_extension_executor,
    _verify_draft_semantic_registry_update_executor,
    _verify_semantic_grounded_document_executor,
    execute_agent_task_action,
    get_agent_task_action,
    validate_agent_task_output,
)


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


def test_enqueue_document_reprocess_executor_queues_reprocess(monkeypatch) -> None:
    document_id = uuid4()
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="enqueue_document_reprocess",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.reprocess_document",
        lambda session, requested_document_id: DocumentUploadResponse(
            document_id=requested_document_id,
            run_id=uuid4(),
            status="queued",
            duplicate=False,
        ),
    )

    result = _enqueue_document_reprocess_executor(
        session=object(),
        _task=task,
        payload=EnqueueDocumentReprocessTaskInput(
            document_id=document_id,
            source_task_id=source_task_id,
            reason="triage requested reprocess",
        ),
    )

    assert result["document_id"] == str(document_id)
    assert result["source_task_id"] == str(source_task_id)
    assert result["reason"] == "triage requested reprocess"
    assert result["reprocess"]["document_id"] == str(document_id)
    assert result["reprocess"]["status"] == "queued"


def test_latest_semantic_pass_executor_returns_typed_output(monkeypatch) -> None:
    semantic_pass = _semantic_pass_response()
    document_id = semantic_pass.document_id

    monkeypatch.setattr(
        "app.services.agent_task_actions.get_active_semantic_pass_detail",
        lambda session, requested_document_id: (
            semantic_pass if requested_document_id == document_id else None
        ),
    )

    result = _latest_semantic_pass_executor(
        session=object(),
        _task=AgentTask(
            id=uuid4(),
            task_type="get_latest_semantic_pass",
            status="processing",
            priority=100,
            side_effect_level="read_only",
            requires_approval=False,
            input_json={},
            result_json={},
            workflow_version="v1",
            model_settings_json={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        payload=LatestSemanticPassTaskInput(document_id=document_id),
    )

    assert result["document_id"] == str(document_id)
    assert result["semantic_pass"]["semantic_pass_id"] == str(semantic_pass.semantic_pass_id)
    assert result["success_metrics"]


def test_draft_harness_config_update_executor_writes_draft_artifact(
    monkeypatch,
    tmp_path,
) -> None:
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/harness_config_draft.json",
            },
        )(),
    )
    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )

    session = type(
        "FakeSession",
        (),
        {
            "get": lambda self, model, key: type(
                "SourceTask",
                (),
                {"id": key, "task_type": "triage_replay_regression"},
            )()
        },
    )()

    result = _draft_harness_config_update_executor(
        session=session,
        task=task,
        payload=DraftHarnessConfigUpdateTaskInput(
            draft_harness_name="wide_v2_review",
            base_harness_name="wide_v2",
            source_task_id=source_task_id,
            rationale="publish review harness",
            reranker_overrides={"result_type_priority_bonus": 0.009},
        ),
    )

    assert result["draft"]["draft_harness_name"] == "wide_v2_review"
    assert result["draft"]["base_harness_name"] == "wide_v2"
    assert result["draft"]["source_task_id"] == str(source_task_id)
    assert result["draft"]["effective_harness_config"]["base_harness_name"] == "wide_v2"
    assert result["artifact_kind"] == "harness_config_draft"


def test_triage_semantic_pass_executor_writes_gap_report_artifact(monkeypatch) -> None:
    target_task_id = uuid4()
    semantic_pass = _semantic_pass_response()
    task = AgentTask(
        id=uuid4(),
        task_type="triage_semantic_pass",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            task_id=target_task_id,
            task_type="get_latest_semantic_pass",
            output_schema_name="get_latest_semantic_pass_output",
            output_schema_version="1.0",
            task_updated_at=datetime.now(UTC),
            output={
                "document_id": str(semantic_pass.document_id),
                "semantic_pass": json.loads(semantic_pass.model_dump_json()),
                "success_metrics": [],
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.triage_semantic_pass",
        lambda semantic_pass, low_evidence_threshold: SimpleNamespace(
            gap_report={
                "document_id": semantic_pass.document_id,
                "run_id": semantic_pass.run_id,
                "semantic_pass_id": semantic_pass.semantic_pass_id,
                "registry_version": semantic_pass.registry_version,
                "registry_sha256": semantic_pass.registry_sha256,
                "evaluation_status": semantic_pass.evaluation_status,
                "evaluation_fixture_name": semantic_pass.evaluation_fixture_name,
                "evaluation_version": semantic_pass.evaluation_version,
                "continuity_summary": semantic_pass.continuity_summary,
                "issue_count": 1,
                "issues": [],
                "recommended_followups": [],
                "success_metrics": [],
            },
            recommendation={
                "next_action": "draft_registry_update",
                "confidence": "high",
                "summary": "draft an additive registry update",
            },
            verification_outcome="failed",
            verification_metrics={"issue_count": 1},
            verification_reasons=["Expected concept missing."],
            verification_details={"issue_types": ["missing_expected_concept"]},
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_verification_record",
        lambda session, **kwargs: SimpleNamespace(
            verification_id=uuid4(),
            target_task_id=kwargs["target_task_id"],
            verification_task_id=kwargs["verification_task_id"],
            verifier_type=kwargs["verifier_type"],
            outcome=kwargs["outcome"],
            metrics=kwargs["metrics"],
            reasons=kwargs["reasons"],
            details=kwargs["details"],
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            model_dump=lambda mode="json": {
                "verification_id": str(uuid4()),
                "target_task_id": str(kwargs["target_task_id"]),
                "verification_task_id": str(kwargs["verification_task_id"]),
                "verifier_type": kwargs["verifier_type"],
                "outcome": kwargs["outcome"],
                "metrics": kwargs["metrics"],
                "reasons": kwargs["reasons"],
                "details": kwargs["details"],
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_gap_report.json",
        ),
    )

    result = _triage_semantic_pass_executor(
        session=object(),
        task=task,
        payload=TriageSemanticPassTaskInput(
            target_task_id=target_task_id,
            low_evidence_threshold=2,
        ),
    )

    assert result["document_id"] == str(semantic_pass.document_id)
    assert result["recommendation"]["next_action"] == "draft_registry_update"
    assert result["artifact_kind"] == "semantic_gap_report"
    assert result["verification"]["verifier_type"] == "semantic_gap_gate"


def test_draft_semantic_registry_update_executor_writes_draft_artifact(monkeypatch) -> None:
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="draft_semantic_registry_update",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session = SimpleNamespace(
        get=lambda model, key: (
            AgentTask(
                id=source_task_id,
                task_type="triage_semantic_pass",
                status="completed",
                priority=100,
                side_effect_level="read_only",
                requires_approval=False,
                input_json={},
                result_json={},
                workflow_version="v1",
                model_settings_json={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )
            if model is AgentTask and key == source_task_id
            else None
        )
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            task_id=source_task_id,
            task_type="triage_semantic_pass",
            output={
                "document_id": str(uuid4()),
                "run_id": str(uuid4()),
                "semantic_pass_id": str(uuid4()),
                "registry_version": "semantics-layer-foundation-alpha.2",
                "evaluation_fixture_name": "semantic_fixture",
                "evaluation_status": "completed",
                "gap_report": {
                    "document_id": str(uuid4()),
                    "run_id": str(uuid4()),
                    "semantic_pass_id": str(uuid4()),
                    "registry_version": "semantics-layer-foundation-alpha.2",
                    "registry_sha256": "registry-sha",
                    "evaluation_status": "completed",
                    "evaluation_fixture_name": "semantic_fixture",
                    "evaluation_version": 2,
                    "continuity_summary": {"reason": "no_prior_active_run", "change_count": 0},
                    "issue_count": 1,
                    "issues": [
                        {
                            "issue_id": "missing_expected_concept:integration_threshold",
                            "issue_type": "missing_expected_concept",
                            "severity": "high",
                            "concept_key": "integration_threshold",
                            "category_key": None,
                            "assertion_id": None,
                            "binding_id": None,
                            "summary": "Expected concept missing.",
                            "details": {},
                            "evidence_refs": [],
                            "registry_update_hints": [
                                {
                                    "update_type": "add_alias",
                                    "concept_key": "integration_threshold",
                                    "alias_text": "integration guardrail",
                                    "category_key": None,
                                    "reason": "missing alias",
                                }
                            ],
                        }
                    ],
                    "recommended_followups": [],
                    "success_metrics": [],
                },
                "verification": {
                    "verification_id": str(uuid4()),
                    "target_task_id": str(source_task_id),
                    "verification_task_id": str(uuid4()),
                    "verifier_type": "semantic_gap_gate",
                    "outcome": "failed",
                    "metrics": {},
                    "reasons": [],
                    "details": {},
                    "created_at": datetime.now(UTC).isoformat(),
                    "completed_at": datetime.now(UTC).isoformat(),
                },
                "recommendation": {
                    "next_action": "draft_registry_update",
                    "confidence": "high",
                    "summary": "draft registry update",
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "semantic_gap_report",
                "artifact_path": "/tmp/semantic_gap_report.json",
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.draft_semantic_registry_update",
        lambda session, gap_report, **kwargs: {
            "base_registry_version": "semantics-layer-foundation-alpha.2",
            "proposed_registry_version": "semantics-layer-foundation-alpha.3",
            "source_task_id": kwargs["source_task_id"],
            "source_task_type": kwargs["source_task_type"],
            "rationale": kwargs["rationale"],
            "document_ids": [gap_report["document_id"]],
            "operations": [
                {
                    "operation_id": "add_alias:integration_threshold:integration_guardrail",
                    "operation_type": "add_alias",
                    "concept_key": "integration_threshold",
                    "alias_text": "integration guardrail",
                    "category_key": None,
                    "source_issue_ids": ["missing_expected_concept:integration_threshold"],
                    "rationale": "missing alias",
                }
            ],
            "effective_registry": {"registry_version": "semantics-layer-foundation-alpha.3"},
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_registry_draft.json",
        ),
    )

    result = _draft_semantic_registry_update_executor(
        session=session,
        task=task,
        payload=DraftSemanticRegistryUpdateTaskInput(
            source_task_id=source_task_id,
            rationale="add the missing alias",
        ),
    )

    assert result["draft"]["proposed_registry_version"] == "semantics-layer-foundation-alpha.3"
    assert result["artifact_kind"] == "semantic_registry_draft"


def test_discover_semantic_bootstrap_candidates_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="discover_semantic_bootstrap_candidates",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_id = uuid4()

    monkeypatch.setattr(
        "app.services.agent_task_actions.discover_semantic_bootstrap_candidates",
        lambda session, **kwargs: {
            "report_name": "semantic_bootstrap_candidate_report",
            "extraction_strategy": "corpus_phrase_mining_v1",
            "input_document_ids": [str(document_id)],
            "document_count": 1,
            "total_source_count": 2,
            "existing_registry_term_exclusion": True,
            "candidate_count": 1,
            "candidates": [
                {
                    "candidate_id": "bootstrap:incident_response_latency",
                    "concept_key": "incident_response_latency",
                    "preferred_label": "Incident Response Latency",
                    "normalized_phrase": "incident response latency",
                    "phrase_tokens": ["incident", "response", "latency"],
                    "epistemic_status": "candidate_bootstrap",
                    "document_ids": [str(document_id)],
                    "document_count": 1,
                    "source_count": 2,
                    "source_types": ["chunk", "table"],
                    "score": 0.88,
                    "evidence_refs": [],
                    "details": {},
                }
            ],
            "warnings": [],
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_bootstrap_candidate_report.json",
        ),
    )

    result = _discover_semantic_bootstrap_candidates_executor(
        session=object(),
        task=task,
        payload=DiscoverSemanticBootstrapCandidatesTaskInput(document_ids=[document_id]),
    )

    assert result["report"]["candidate_count"] == 1
    assert result["artifact_kind"] == "semantic_bootstrap_candidate_report"


def test_draft_semantic_registry_update_executor_supports_bootstrap_source(monkeypatch) -> None:
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="draft_semantic_registry_update",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session = SimpleNamespace(
        get=lambda model, key: (
            AgentTask(
                id=source_task_id,
                task_type="discover_semantic_bootstrap_candidates",
                status="completed",
                priority=100,
                side_effect_level="read_only",
                requires_approval=False,
                input_json={},
                result_json={},
                workflow_version="v1",
                model_settings_json={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )
            if model is AgentTask and key == source_task_id
            else None
        )
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            task_id=source_task_id,
            task_type="discover_semantic_bootstrap_candidates",
            output={
                "report": {
                    "report_name": "semantic_bootstrap_candidate_report",
                    "extraction_strategy": "corpus_phrase_mining_v1",
                    "input_document_ids": [str(uuid4())],
                    "document_count": 1,
                    "total_source_count": 2,
                    "existing_registry_term_exclusion": True,
                    "candidate_count": 1,
                    "candidates": [
                        {
                            "candidate_id": "bootstrap:incident_response_latency",
                            "concept_key": "incident_response_latency",
                            "preferred_label": "Incident Response Latency",
                            "normalized_phrase": "incident response latency",
                            "phrase_tokens": ["incident", "response", "latency"],
                            "epistemic_status": "candidate_bootstrap",
                            "document_ids": [str(uuid4())],
                            "document_count": 1,
                            "source_count": 2,
                            "source_types": ["chunk", "table"],
                            "score": 0.88,
                            "evidence_refs": [],
                            "details": {},
                        }
                    ],
                    "warnings": [],
                    "success_metrics": [],
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "semantic_bootstrap_candidate_report",
                "artifact_path": "/tmp/semantic_bootstrap_candidate_report.json",
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.draft_semantic_registry_update_from_bootstrap_report",
        lambda session, report, **kwargs: {
            "base_registry_version": "semantics-layer-foundation-alpha.2",
            "proposed_registry_version": "semantics-layer-foundation-alpha.3",
            "source_task_id": kwargs["source_task_id"],
            "source_task_type": kwargs["source_task_type"],
            "rationale": kwargs["rationale"],
            "document_ids": report["input_document_ids"],
            "operations": [
                {
                    "operation_id": (
                        "add_concept:incident_response_latency:incident_response_latency"
                    ),
                    "operation_type": "add_concept",
                    "concept_key": "incident_response_latency",
                    "alias_text": None,
                    "category_key": None,
                    "source_issue_ids": ["bootstrap:incident_response_latency"],
                    "rationale": "bootstrap concept",
                }
            ],
            "effective_registry": {"registry_version": "semantics-layer-foundation-alpha.3"},
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_registry_draft.json",
        ),
    )

    result = _draft_semantic_registry_update_executor(
        session=session,
        task=task,
        payload=DraftSemanticRegistryUpdateTaskInput(
            source_task_id=source_task_id,
            rationale="bootstrap the registry from corpus evidence",
        ),
    )

    assert result["draft"]["operations"][0]["operation_type"] == "add_concept"
    assert result["artifact_kind"] == "semantic_registry_draft"


def test_verify_draft_semantic_registry_update_executor_writes_verification_artifact(
    monkeypatch,
) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="verify_draft_semantic_registry_update",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.verify_draft_semantic_registry_update_task",
        lambda session, verification_task, payload: {
            "draft": {
                "base_registry_version": "semantics-layer-foundation-alpha.2",
                "proposed_registry_version": "semantics-layer-foundation-alpha.3",
                "source_task_id": str(uuid4()),
                "source_task_type": "triage_semantic_pass",
                "rationale": "alias update",
                "document_ids": [str(uuid4())],
                "operations": [],
                "effective_registry": {"registry_version": "semantics-layer-foundation-alpha.3"},
                "success_metrics": [],
            },
            "document_deltas": [],
            "summary": {"improved_document_count": 1, "regressed_document_count": 0},
            "success_metrics": [],
            "verification": {
                "verification_id": str(uuid4()),
                "target_task_id": str(uuid4()),
                "verification_task_id": str(task.id),
                "verifier_type": "semantic_registry_draft_gate",
                "outcome": "passed",
                "metrics": {"document_count": 1},
                "reasons": [],
                "details": {},
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            },
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_registry_draft_verification.json",
        ),
    )

    result = _verify_draft_semantic_registry_update_executor(
        session=object(),
        task=task,
        payload=VerifyDraftSemanticRegistryUpdateTaskInput(target_task_id=uuid4()),
    )

    assert result["artifact_kind"] == "semantic_registry_draft_verification"
    assert result["verification"]["verifier_type"] == "semantic_registry_draft_gate"


def test_apply_semantic_registry_update_executor_persists_registry(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    committed = {"value": False}
    fake_session = SimpleNamespace(commit=lambda: committed.__setitem__("value", True))
    task = AgentTask(
        id=uuid4(),
        task_type="apply_semantic_registry_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    dependencies = {
        ("draft_semantic_registry_update", draft_task_id): SimpleNamespace(
            task_id=draft_task_id,
            task_type="draft_semantic_registry_update",
            output={
                "draft": {
                    "base_registry_version": "semantics-layer-foundation-alpha.2",
                    "proposed_registry_version": "semantics-layer-foundation-alpha.3",
                    "source_task_id": str(uuid4()),
                    "source_task_type": "triage_semantic_pass",
                    "rationale": "alias update",
                    "document_ids": [str(uuid4())],
                    "operations": [
                        {
                            "operation_id": "add_alias:integration_threshold:integration_guardrail",
                            "operation_type": "add_alias",
                            "concept_key": "integration_threshold",
                            "alias_text": "integration guardrail",
                            "category_key": None,
                            "source_issue_ids": ["missing_expected_concept:integration_threshold"],
                            "rationale": "missing alias",
                        }
                    ],
                    "effective_registry": {
                        "registry_version": "semantics-layer-foundation-alpha.3"
                    },
                    "success_metrics": [],
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "semantic_registry_draft",
                "artifact_path": "/tmp/semantic_registry_draft.json",
            },
        ),
        ("verify_draft_semantic_registry_update", verification_task_id): SimpleNamespace(
            task_id=verification_task_id,
            task_type="verify_draft_semantic_registry_update",
            output={
                "draft": {
                    "base_registry_version": "semantics-layer-foundation-alpha.2",
                    "proposed_registry_version": "semantics-layer-foundation-alpha.3",
                    "source_task_id": str(uuid4()),
                    "source_task_type": "triage_semantic_pass",
                    "rationale": "alias update",
                    "document_ids": [str(uuid4())],
                    "operations": [
                        {
                            "operation_id": "add_alias:integration_threshold:integration_guardrail",
                            "operation_type": "add_alias",
                            "concept_key": "integration_threshold",
                            "alias_text": "integration guardrail",
                            "category_key": None,
                            "source_issue_ids": ["missing_expected_concept:integration_threshold"],
                            "rationale": "missing alias",
                        }
                    ],
                    "effective_registry": {
                        "registry_version": "semantics-layer-foundation-alpha.3"
                    },
                    "success_metrics": [],
                },
                "document_deltas": [],
                "summary": {"improved_document_count": 1, "regressed_document_count": 0},
                "success_metrics": [],
                "verification": {
                    "verification_id": str(uuid4()),
                    "target_task_id": str(draft_task_id),
                    "verification_task_id": str(verification_task_id),
                    "verifier_type": "semantic_registry_draft_gate",
                    "outcome": "passed",
                    "metrics": {"document_count": 1},
                    "reasons": [],
                    "details": {},
                    "created_at": datetime.now(UTC).isoformat(),
                    "completed_at": datetime.now(UTC).isoformat(),
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "semantic_registry_draft_verification",
                "artifact_path": "/tmp/semantic_registry_draft_verification.json",
            },
        ),
    }
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda session, task_id, depends_on_task_id, expected_task_type, **kwargs: dependencies[
            (expected_task_type, depends_on_task_id)
        ],
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.persist_semantic_ontology_snapshot",
        lambda session, payload, **kwargs: SimpleNamespace(id=uuid4()),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.get_semantic_registry",
        lambda session: SimpleNamespace(
            registry_version="semantics-layer-foundation-alpha.3",
            sha256="new-registry-sha",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/applied_semantic_registry_update.json",
        ),
    )

    result = _apply_semantic_registry_update_executor(
        session=fake_session,
        task=task,
        payload=ApplySemanticRegistryUpdateTaskInput(
            draft_task_id=draft_task_id,
            verification_task_id=verification_task_id,
            reason="publish the verified registry update",
        ),
    )

    assert result["applied_registry_version"] == "semantics-layer-foundation-alpha.3"
    assert result["applied_registry_sha256"] == "new-registry-sha"
    assert result["config_path"].startswith("db://semantic_ontology_snapshots/")
    assert result["artifact_kind"] == "applied_semantic_registry_update"
    assert committed["value"] is True


def test_initialize_workspace_ontology_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="initialize_workspace_ontology",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    snapshot_id = uuid4()
    monkeypatch.setattr(
        "app.services.agent_task_actions.initialize_workspace_ontology",
        lambda session: {
            "snapshot": {
                "snapshot_id": snapshot_id,
                "ontology_name": "portable_upper_ontology",
                "ontology_version": "portable-upper-ontology-v1",
                "upper_ontology_version": "portable-upper-ontology-v1",
                "sha256": "ontology-sha",
                "source_kind": "upper_seed",
                "source_task_id": None,
                "source_task_type": None,
                "concept_count": 0,
                "category_count": 0,
                "relation_count": 1,
                "relation_keys": ["document_mentions_concept"],
                "created_at": datetime.now(UTC).isoformat(),
                "activated_at": datetime.now(UTC).isoformat(),
            },
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/active_ontology_snapshot.json",
        ),
    )

    result = _initialize_workspace_ontology_executor(
        session=object(),
        task=task,
        _payload=InitializeWorkspaceOntologyTaskInput(),
    )

    assert result["snapshot"]["snapshot_id"] == snapshot_id
    assert result["artifact_kind"] == "active_ontology_snapshot"


def test_get_active_ontology_snapshot_executor_returns_payload(monkeypatch) -> None:
    snapshot_id = uuid4()
    monkeypatch.setattr(
        "app.services.agent_task_actions.get_active_ontology_snapshot_payload",
        lambda session: {
            "snapshot": {
                "snapshot_id": snapshot_id,
                "ontology_name": "portable_upper_ontology",
                "ontology_version": "portable-upper-ontology-v1",
                "upper_ontology_version": "portable-upper-ontology-v1",
                "sha256": "ontology-sha",
                "source_kind": "upper_seed",
                "source_task_id": None,
                "source_task_type": None,
                "concept_count": 0,
                "category_count": 0,
                "relation_count": 1,
                "relation_keys": ["document_mentions_concept"],
                "created_at": datetime.now(UTC).isoformat(),
                "activated_at": datetime.now(UTC).isoformat(),
            },
            "success_metrics": [],
        },
    )

    result = _get_active_ontology_snapshot_executor(
        session=object(),
        _task=object(),
        _payload=GetActiveOntologySnapshotTaskInput(),
    )

    assert result["snapshot"]["snapshot_id"] == snapshot_id


def test_draft_ontology_extension_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="draft_ontology_extension",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    source_task_id = uuid4()
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output={
                "report": {
                    "input_document_ids": [str(uuid4())],
                    "candidate_count": 1,
                    "candidates": [
                        {
                            "candidate_id": "bootstrap:incident_response_latency",
                            "concept_key": "incident_response_latency",
                            "preferred_label": "Incident Response Latency",
                            "normalized_phrase": "incident response latency",
                            "phrase_tokens": ["incident", "response", "latency"],
                            "document_ids": [str(uuid4())],
                            "document_count": 1,
                            "source_count": 2,
                            "source_types": ["chunk"],
                            "score": 0.84,
                            "evidence_refs": [],
                            "details": {},
                        }
                    ],
                    "warnings": [],
                    "success_metrics": [],
                    "extraction_strategy": "phrase_mining_v1",
                    "document_count": 1,
                    "total_source_count": 2,
                    "existing_registry_term_exclusion": True,
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "semantic_bootstrap_candidate_report",
                "artifact_path": "/tmp/semantic_bootstrap_candidate_report.json",
            },
            task_type="discover_semantic_bootstrap_candidates",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.draft_ontology_extension_from_bootstrap_report",
        lambda session, report, **kwargs: {
            "base_snapshot_id": uuid4(),
            "base_ontology_version": "portable-upper-ontology-v1",
            "proposed_ontology_version": "portable-upper-ontology-v1.1",
            "upper_ontology_version": "portable-upper-ontology-v1",
            "source_task_id": source_task_id,
            "source_task_type": "discover_semantic_bootstrap_candidates",
            "rationale": kwargs["rationale"],
            "document_ids": [uuid4()],
            "operations": [
                {
                    "operation_id": "add_concept:incident_response_latency",
                    "operation_type": "add_concept",
                    "concept_key": "incident_response_latency",
                    "preferred_label": "Incident Response Latency",
                    "alias_text": None,
                    "category_key": None,
                    "source_issue_ids": [],
                    "rationale": "bootstrap discovery",
                }
            ],
            "effective_ontology": {"registry_version": "portable-upper-ontology-v1.1"},
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/ontology_extension_draft.json",
        ),
    )
    session = SimpleNamespace(
        get=lambda model, key: SimpleNamespace(task_type="discover_semantic_bootstrap_candidates")
    )

    result = _draft_ontology_extension_executor(
        session=session,
        task=task,
        payload=DraftOntologyExtensionTaskInput(
            source_task_id=source_task_id,
            rationale="extend ontology from corpus evidence",
        ),
    )

    assert result["draft"]["proposed_ontology_version"] == "portable-upper-ontology-v1.1"
    assert result["artifact_kind"] == "ontology_extension_draft"


def test_verify_draft_ontology_extension_executor_writes_verification_artifact(
    monkeypatch,
) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="verify_draft_ontology_extension",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    draft_task_id = uuid4()
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            task_id=draft_task_id,
            task_type="draft_ontology_extension",
            output={
                "draft": {
                    "base_snapshot_id": str(uuid4()),
                    "base_ontology_version": "portable-upper-ontology-v1",
                    "proposed_ontology_version": "portable-upper-ontology-v1.1",
                    "upper_ontology_version": "portable-upper-ontology-v1",
                    "source_task_id": str(uuid4()),
                    "source_task_type": "discover_semantic_bootstrap_candidates",
                    "rationale": "extend ontology from corpus evidence",
                    "document_ids": [str(uuid4())],
                    "operations": [],
                    "effective_ontology": {"registry_version": "portable-upper-ontology-v1.1"},
                    "success_metrics": [],
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "ontology_extension_draft",
                "artifact_path": "/tmp/ontology_extension_draft.json",
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.verify_draft_ontology_extension",
        lambda session, draft, **kwargs: (
            [],
            {"document_count": 1, "improved_document_count": 1, "regressed_document_count": 0},
            {"document_count": 1},
            [],
            "passed",
            [],
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_verification_record",
        lambda session, **kwargs: SimpleNamespace(
            model_dump=lambda mode="json": {
                "verification_id": str(uuid4()),
                "target_task_id": str(draft_task_id),
                "verification_task_id": str(task.id),
                "verifier_type": kwargs["verifier_type"],
                "outcome": kwargs["outcome"],
                "metrics": kwargs["metrics"],
                "reasons": kwargs["reasons"],
                "details": kwargs["details"],
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            }
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/ontology_extension_draft_verification.json",
        ),
    )

    result = _verify_draft_ontology_extension_executor(
        session=object(),
        task=task,
        payload=VerifyDraftOntologyExtensionTaskInput(target_task_id=draft_task_id),
    )

    assert result["verification"]["outcome"] == "passed"
    assert result["artifact_kind"] == "ontology_extension_draft_verification"


def test_apply_ontology_extension_executor_writes_artifact(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="apply_ontology_extension",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    dependencies = {
        ("draft_ontology_extension", draft_task_id): SimpleNamespace(
            output={
                "draft": {
                    "base_snapshot_id": str(uuid4()),
                    "base_ontology_version": "portable-upper-ontology-v1",
                    "proposed_ontology_version": "portable-upper-ontology-v1.1",
                    "upper_ontology_version": "portable-upper-ontology-v1",
                    "source_task_id": str(uuid4()),
                    "source_task_type": "discover_semantic_bootstrap_candidates",
                    "rationale": "extend ontology from corpus evidence",
                    "document_ids": [str(uuid4())],
                    "operations": [],
                    "effective_ontology": {"registry_version": "portable-upper-ontology-v1.1"},
                    "success_metrics": [],
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "ontology_extension_draft",
                "artifact_path": "/tmp/ontology_extension_draft.json",
            }
        ),
        ("verify_draft_ontology_extension", verification_task_id): SimpleNamespace(
            output={
                "draft": {
                    "base_snapshot_id": str(uuid4()),
                    "base_ontology_version": "portable-upper-ontology-v1",
                    "proposed_ontology_version": "portable-upper-ontology-v1.1",
                    "upper_ontology_version": "portable-upper-ontology-v1",
                    "source_task_id": str(uuid4()),
                    "source_task_type": "discover_semantic_bootstrap_candidates",
                    "rationale": "extend ontology from corpus evidence",
                    "document_ids": [str(uuid4())],
                    "operations": [],
                    "effective_ontology": {"registry_version": "portable-upper-ontology-v1.1"},
                    "success_metrics": [],
                },
                "document_deltas": [],
                "summary": {},
                "success_metrics": [],
                "verification": {
                    "verification_id": str(uuid4()),
                    "target_task_id": str(draft_task_id),
                    "verification_task_id": str(verification_task_id),
                    "verifier_type": "ontology_extension_draft_gate",
                    "outcome": "passed",
                    "metrics": {"document_count": 1},
                    "reasons": [],
                    "details": {},
                    "created_at": datetime.now(UTC).isoformat(),
                    "completed_at": datetime.now(UTC).isoformat(),
                },
                "artifact_id": str(uuid4()),
                "artifact_kind": "ontology_extension_draft_verification",
                "artifact_path": "/tmp/ontology_extension_draft_verification.json",
            }
        ),
    }
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda session, task_id, depends_on_task_id, expected_task_type, **kwargs: dependencies[
            (expected_task_type, depends_on_task_id)
        ],
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.apply_ontology_extension",
        lambda session, draft, **kwargs: {
            "applied_snapshot_id": uuid4(),
            "applied_ontology_version": "portable-upper-ontology-v1.1",
            "applied_ontology_sha256": "ontology-sha",
            "upper_ontology_version": "portable-upper-ontology-v1",
            "reason": kwargs["reason"],
            "applied_operations": [],
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/applied_ontology_extension.json",
        ),
    )

    result = _apply_ontology_extension_executor(
        session=object(),
        task=task,
        payload=ApplyOntologyExtensionTaskInput(
            draft_task_id=draft_task_id,
            verification_task_id=verification_task_id,
            reason="publish verified ontology extension",
        ),
    )

    assert result["applied_ontology_version"] == "portable-upper-ontology-v1.1"
    assert result["artifact_kind"] == "applied_ontology_extension"


def test_build_document_fact_graph_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="build_document_fact_graph",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_id = uuid4()
    monkeypatch.setattr(
        "app.services.agent_task_actions.build_document_fact_graph",
        lambda session, **kwargs: {
            "document_id": document_id,
            "run_id": uuid4(),
            "semantic_pass_id": uuid4(),
            "ontology_snapshot_id": uuid4(),
            "ontology_version": "portable-upper-ontology-v1.1",
            "fact_count": 1,
            "approved_fact_count": 1,
            "entity_count": 2,
            "relation_counts": {"document_mentions_concept": 1},
            "facts": [
                {
                    "fact_id": uuid4(),
                    "document_id": document_id,
                    "run_id": uuid4(),
                    "semantic_pass_id": uuid4(),
                    "relation_key": "document_mentions_concept",
                    "relation_label": "Document Mentions Concept",
                    "subject_entity_key": f"document:{document_id}",
                    "subject_label": "Integration One",
                    "object_entity_key": "concept:integration_threshold",
                    "object_label": "Integration Threshold",
                    "object_value_text": None,
                    "review_status": "approved",
                    "assertion_id": uuid4(),
                    "evidence_ids": [uuid4()],
                }
            ],
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_fact_graph.json",
        ),
    )

    result = _build_document_fact_graph_executor(
        session=object(),
        task=task,
        payload=BuildDocumentFactGraphTaskInput(document_id=document_id),
    )

    assert result["fact_count"] == 1
    assert result["artifact_kind"] == "semantic_fact_graph"


def test_build_shadow_semantic_graph_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="build_shadow_semantic_graph",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_ids = [uuid4(), uuid4()]
    monkeypatch.setattr(
        "app.services.agent_task_actions.build_shadow_semantic_graph",
        lambda session, **kwargs: _shadow_graph_output_payload(document_ids=document_ids)[
            "shadow_graph"
        ],
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/shadow_semantic_graph.json",
        ),
    )

    result = _build_shadow_semantic_graph_executor(
        session=object(),
        task=task,
        payload=BuildShadowSemanticGraphTaskInput(
            document_ids=document_ids,
            minimum_review_status="approved",
            min_shared_documents=2,
            score_threshold=0.45,
        ),
    )

    assert result["shadow_graph"]["edge_count"] == 1
    assert result["artifact_kind"] == "shadow_semantic_graph"


def test_evaluate_semantic_relation_extractor_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="evaluate_semantic_relation_extractor",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_ids = [uuid4(), uuid4()]
    monkeypatch.setattr(
        "app.services.agent_task_actions.evaluate_semantic_relation_extractor",
        lambda session, **kwargs: {
            key: value
            for key, value in _semantic_relation_evaluation_output_payload(
                document_ids=document_ids
            ).items()
            if key not in {"artifact_id", "artifact_kind", "artifact_path"}
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_relation_evaluation.json",
        ),
    )

    result = _evaluate_semantic_relation_extractor_executor(
        session=object(),
        task=task,
        payload=EvaluateSemanticRelationExtractorTaskInput(
            document_ids=document_ids,
            minimum_review_status="approved",
            baseline_min_shared_documents=2,
            candidate_score_threshold=0.45,
            expected_min_shared_documents=1,
        ),
    )

    assert result["summary"]["candidate_expected_recall"] == 1.0
    assert result["artifact_kind"] == "semantic_relation_evaluation"


def test_triage_semantic_graph_disagreements_executor_writes_artifact(monkeypatch) -> None:
    evaluation_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="triage_semantic_graph_disagreements",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_ids = [uuid4(), uuid4()]
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output=_semantic_relation_evaluation_output_payload(document_ids=document_ids),
            task_type="evaluate_semantic_relation_extractor",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.triage_semantic_graph_disagreements",
        lambda evaluation, **kwargs: _graph_triage_output_payload(
            evaluation_task_id=evaluation_task_id,
            verification_task_id=task.id,
        )["disagreement_report"],
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_verification_record",
        lambda session, **kwargs: SimpleNamespace(
            model_dump=lambda mode="json": {
                "verification_id": str(uuid4()),
                "target_task_id": str(task.id),
                "verification_task_id": str(task.id),
                "verifier_type": kwargs["verifier_type"],
                "outcome": kwargs["outcome"],
                "metrics": kwargs["metrics"],
                "reasons": kwargs["reasons"],
                "details": kwargs["details"],
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            }
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_graph_disagreement_report.json",
        ),
    )

    result = _triage_semantic_graph_disagreements_executor(
        session=object(),
        task=task,
        payload=TriageSemanticGraphDisagreementsTaskInput(
            target_task_id=evaluation_task_id,
            min_score=0.45,
            expected_only=True,
        ),
    )

    assert result["disagreement_report"]["issue_count"] == 1
    assert result["recommendation"]["next_action"] == "draft_graph_promotions"
    assert result["artifact_kind"] == "semantic_graph_disagreement_report"


def test_draft_graph_promotions_executor_writes_artifact(monkeypatch) -> None:
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="draft_graph_promotions",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output=_graph_triage_output_payload(
                evaluation_task_id=uuid4(),
                verification_task_id=uuid4(),
            ),
            task_type="triage_semantic_graph_disagreements",
        ),
    )
    session = SimpleNamespace(
        get=lambda model, key: (
            SimpleNamespace(task_type="triage_semantic_graph_disagreements")
            if model is AgentTask and key == source_task_id
            else None
        )
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.draft_graph_promotions",
        lambda session, **kwargs: _draft_graph_output_payload(
            source_task_id=source_task_id,
            source_task_type="triage_semantic_graph_disagreements",
        )["draft"],
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_graph_promotion_draft.json",
        ),
    )

    result = _draft_graph_promotions_executor(
        session=session,
        task=task,
        payload=DraftGraphPromotionsTaskInput(
            source_task_id=source_task_id,
            rationale="Promote approved graph memory.",
            min_score=0.45,
        ),
    )

    assert result["draft"]["proposed_graph_version"] == "portable-upper-ontology-v1.1.graph.1"
    assert result["artifact_kind"] == "semantic_graph_promotion_draft"


def test_verify_draft_graph_promotions_executor_writes_artifact(monkeypatch) -> None:
    draft_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="verify_draft_graph_promotions",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output=_draft_graph_output_payload(
                source_task_id=uuid4(),
                source_task_type="triage_semantic_graph_disagreements",
            ),
            task_type="draft_graph_promotions",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.verify_draft_graph_promotions",
        lambda session, draft, **kwargs: (
            {
                "promoted_edge_count": 1,
                "supported_edge_count": 1,
                "stale_edge_count": 0,
                "unsupported_edge_count": 0,
                "ontology_mismatch_count": 0,
                "conflict_count": 0,
                "traceable_edge_ratio": 1.0,
            },
            {
                "promoted_edge_count": 1,
                "supported_edge_count": 1,
                "stale_edge_count": 0,
                "unsupported_edge_count": 0,
                "ontology_mismatch_count": 0,
                "conflict_count": 0,
            },
            [],
            "passed",
            _verify_graph_output_payload(
                draft_task_id=draft_task_id,
                verification_task_id=task.id,
            )["success_metrics"],
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_verification_record",
        lambda session, **kwargs: SimpleNamespace(
            model_dump=lambda mode="json": {
                "verification_id": str(uuid4()),
                "target_task_id": str(draft_task_id),
                "verification_task_id": str(task.id),
                "verifier_type": kwargs["verifier_type"],
                "outcome": kwargs["outcome"],
                "metrics": kwargs["metrics"],
                "reasons": kwargs["reasons"],
                "details": kwargs["details"],
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            }
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/semantic_graph_promotion_verification.json",
        ),
    )

    result = _verify_draft_graph_promotions_executor(
        session=object(),
        task=task,
        payload=VerifyDraftGraphPromotionsTaskInput(target_task_id=draft_task_id),
    )

    assert result["verification"]["outcome"] == "passed"
    assert result["artifact_kind"] == "semantic_graph_promotion_verification"


def test_apply_graph_promotions_executor_writes_artifact(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="apply_graph_promotions",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    dependencies = {
        ("draft_graph_promotions", draft_task_id): SimpleNamespace(
            output=_draft_graph_output_payload(
                source_task_id=uuid4(),
                source_task_type="triage_semantic_graph_disagreements",
            )
        ),
        ("verify_draft_graph_promotions", verification_task_id): SimpleNamespace(
            output=_verify_graph_output_payload(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
            )
        ),
    }
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda session, task_id, depends_on_task_id, expected_task_type, **kwargs: dependencies[
            (expected_task_type, depends_on_task_id)
        ],
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.apply_graph_promotions",
        lambda session, draft, **kwargs: {
            "applied_snapshot_id": uuid4(),
            "applied_graph_version": "portable-upper-ontology-v1.1.graph.1",
            "applied_graph_sha256": "graph-sha",
            "ontology_snapshot_id": uuid4(),
            "reason": kwargs["reason"],
            "applied_edge_count": 1,
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/applied_semantic_graph_snapshot.json",
        ),
    )

    result = _apply_graph_promotions_executor(
        session=object(),
        task=task,
        payload=ApplyGraphPromotionsTaskInput(
            draft_task_id=draft_task_id,
            verification_task_id=verification_task_id,
            reason="Publish the verified semantic graph memory snapshot.",
        ),
    )

    assert result["applied_graph_version"] == "portable-upper-ontology-v1.1.graph.1"
    assert result["artifact_kind"] == "applied_semantic_graph_snapshot"


def test_validate_agent_task_output_accepts_migrated_draft_shape() -> None:
    artifact_id = uuid4()
    source_task_id = uuid4()

    validated = validate_agent_task_output(
        "draft_harness_config_update",
        {
            "draft": {
                "draft_harness_name": "wide_v2_review",
                "base_harness_name": "wide_v2",
                "source_task_id": str(source_task_id),
                "source_task_type": "triage_replay_regression",
                "rationale": "publish review harness",
                "override_spec": {
                    "base_harness_name": "wide_v2",
                    "retrieval_profile_overrides": {},
                    "reranker_overrides": {"result_type_priority_bonus": 0.009},
                    "override_type": "draft_harness_config_update",
                    "override_source": "task_draft",
                    "draft_task_id": str(uuid4()),
                    "source_task_id": str(source_task_id),
                    "rationale": "publish review harness",
                },
                "effective_harness_config": {"base_harness_name": "wide_v2"},
            },
            "artifact_id": str(artifact_id),
            "artifact_kind": "harness_config_draft",
            "artifact_path": "/tmp/harness_config_draft.json",
        },
    )

    assert validated["artifact_id"] == str(artifact_id)
    assert validated["draft"]["source_task_id"] == str(source_task_id)


def test_validate_agent_task_output_rejects_invalid_migrated_draft_shape() -> None:
    try:
        validate_agent_task_output(
            "draft_harness_config_update",
            {
                "artifact_id": str(uuid4()),
                "artifact_kind": "harness_config_draft",
                "artifact_path": "/tmp/harness_config_draft.json",
            },
        )
    except ValidationError as exc:
        assert "draft" in str(exc)
    else:
        raise AssertionError("Expected draft output validation to fail")


def test_validate_agent_task_output_accepts_migrated_evaluate_shape() -> None:
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()

    validated = validate_agent_task_output(
        "evaluate_search_harness",
        {
            "candidate_harness_name": "wide_v2",
            "baseline_harness_name": "default_v1",
            "evaluation": {
                "baseline_harness_name": "default_v1",
                "candidate_harness_name": "wide_v2",
                "limit": 12,
                "total_shared_query_count": 4,
                "total_improved_count": 1,
                "total_regressed_count": 0,
                "total_unchanged_count": 3,
                "sources": [
                    {
                        "source_type": "evaluation_queries",
                        "baseline_replay_run_id": str(baseline_replay_run_id),
                        "candidate_replay_run_id": str(candidate_replay_run_id),
                        "baseline_query_count": 4,
                        "candidate_query_count": 4,
                        "baseline_passed_count": 4,
                        "candidate_passed_count": 4,
                        "baseline_zero_result_count": 0,
                        "candidate_zero_result_count": 0,
                        "baseline_table_hit_count": 1,
                        "candidate_table_hit_count": 1,
                        "baseline_top_result_changes": 0,
                        "candidate_top_result_changes": 0,
                        "baseline_mrr": 1.0,
                        "candidate_mrr": 1.0,
                        "baseline_foreign_top_result_count": 0,
                        "candidate_foreign_top_result_count": 0,
                        "acceptance_checks": {"no_regressions": True},
                        "shared_query_count": 4,
                        "improved_count": 1,
                        "regressed_count": 0,
                        "unchanged_count": 3,
                    }
                ],
            },
        },
    )

    assert validated["candidate_harness_name"] == "wide_v2"
    assert validated["evaluation"]["sources"][0]["source_type"] == "evaluation_queries"


def test_execute_agent_task_action_includes_output_schema_metadata(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={
            "draft_harness_name": "wide_v2_review",
            "base_harness_name": "wide_v2",
        },
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    action = replace(
        get_agent_task_action("draft_harness_config_update"),
        executor=lambda session, current_task, payload: {
            "draft": {
                "draft_harness_name": payload.draft_harness_name,
                "base_harness_name": payload.base_harness_name,
                "source_task_id": None,
                "source_task_type": None,
                "rationale": None,
                "override_spec": {
                    "base_harness_name": payload.base_harness_name,
                    "retrieval_profile_overrides": {},
                    "reranker_overrides": {},
                    "override_type": "draft_harness_config_update",
                    "override_source": "task_draft",
                    "draft_task_id": str(current_task.id),
                    "source_task_id": None,
                    "rationale": None,
                },
                "effective_harness_config": {"base_harness_name": payload.base_harness_name},
            },
            "artifact_id": str(uuid4()),
            "artifact_kind": "harness_config_draft",
            "artifact_path": "/tmp/harness_config_draft.json",
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.get_agent_task_action", lambda _task_type: action
    )

    result = execute_agent_task_action(object(), task)

    assert result["output_schema_name"] == "draft_harness_config_update_output"
    assert result["output_schema_version"] == "1.0"
    assert result["payload"]["draft"]["draft_harness_name"] == "wide_v2_review"


def test_get_agent_task_action_exposes_evaluate_output_schema_metadata() -> None:
    action = get_agent_task_action("evaluate_search_harness")

    assert action.output_schema_name == "evaluate_search_harness_output"
    assert action.output_schema_version == "1.0"
    assert action.output_model is not None


def test_get_agent_task_action_exposes_verify_evaluation_output_schema_metadata() -> None:
    action = get_agent_task_action("verify_search_harness_evaluation")

    assert action.output_schema_name == "verify_search_harness_evaluation_output"
    assert action.output_schema_version == "1.0"
    assert action.output_model is not None


def test_get_agent_task_action_exposes_triage_output_schema_metadata() -> None:
    action = get_agent_task_action("triage_replay_regression")

    assert action.output_schema_name == "triage_replay_regression_output"
    assert action.output_schema_version == "1.0"
    assert action.output_model is not None


def test_get_agent_task_action_exposes_claim_support_judge_eval_metadata() -> None:
    action = get_agent_task_action("evaluate_claim_support_judge")

    assert action.capability == "technical_reports"
    assert action.definition_kind == "workflow"
    assert action.payload_model is EvaluateClaimSupportJudgeTaskInput
    assert action.output_schema_name == "evaluate_claim_support_judge_output"
    assert action.output_schema_version == "1.0"
    assert action.context_builder_name == "evaluate_claim_support_judge"
    assert action.output_model is not None


def test_get_agent_task_action_exposes_context_pack_eval_metadata() -> None:
    action = get_agent_task_action("evaluate_document_generation_context_pack")

    assert action.capability == "technical_reports"
    assert action.definition_kind == "verifier"
    assert action.payload_model is EvaluateDocumentGenerationContextPackTaskInput
    assert action.output_schema_name == "evaluate_document_generation_context_pack_output"
    assert action.output_schema_version == "1.0"
    assert action.context_builder_name == "evaluate_document_generation_context_pack"
    assert action.output_model is not None


def test_optimize_search_harness_from_case_does_not_recommend_noop_draft(
    monkeypatch,
) -> None:
    case_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="optimize_search_harness_from_case",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    optimization = SimpleNamespace(
        best_gate={"outcome": "passed"},
        best_override_spec={
            "base_harness_name": "wide_v2",
            "retrieval_profile_overrides": {},
            "reranker_overrides": {},
        },
        best_score={"sort_key": [1, 0, 0]},
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.get_eval_failure_case",
        lambda session, requested_case_id: {"case_id": str(requested_case_id)},
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.run_search_harness_optimization_loop",
        lambda session, request: optimization,
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/search_harness_optimization.json",
        ),
    )

    result = _optimize_search_harness_from_case_executor(
        session=object(),
        task=task,
        payload=OptimizeSearchHarnessFromCaseTaskInput(
            case_id=case_id,
            limit=1,
            iterations=1,
        ),
    )

    assert result["recommendation"]["next_action"] == "inspect_optimizer_attempts"
    assert "did not change the harness" in result["recommendation"]["summary"]


def test_draft_harness_from_optimization_uses_augmented_override_for_snapshot(
    monkeypatch,
) -> None:
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update_from_optimization",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    source_output = SimpleNamespace(
        case={"case_id": str(uuid4())},
        optimization=SimpleNamespace(
            base_harness_name="wide_v2",
            best_override_spec={
                "base_harness_name": "wide_v2",
                "retrieval_profile_overrides": {"keyword_candidate_multiplier": 9},
                "reranker_overrides": {},
            },
            stopped_reason="iteration_limit_reached",
            iterations_completed=1,
            best_score={"sort_key": [1, 0, 1]},
            best_gate={"outcome": "passed"},
        ),
    )
    captured: dict = {}

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output={},
            task_type="optimize_search_harness_from_case",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.OptimizeSearchHarnessFromCaseTaskOutput.model_validate",
        lambda output: source_output,
    )

    def fake_get_search_harness(name, harness_overrides=None):
        override_spec = dict((harness_overrides or {})[name])
        captured["override_spec"] = override_spec
        return SimpleNamespace(
            config_snapshot={
                "harness_name": name,
                "base_harness_name": override_spec["base_harness_name"],
                "metadata": {
                    "draft_task_id": override_spec.get("draft_task_id"),
                    "source_task_id": override_spec.get("source_task_id"),
                    "rationale": override_spec.get("rationale"),
                },
            }
        )

    monkeypatch.setattr(
        "app.services.agent_task_actions.get_search_harness",
        fake_get_search_harness,
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: SimpleNamespace(
            id=uuid4(),
            artifact_kind=kwargs["artifact_kind"],
            storage_path="/tmp/harness_config_draft.json",
        ),
    )

    result = _draft_harness_config_from_optimization_executor(
        session=object(),
        task=task,
        payload=DraftHarnessConfigFromOptimizationTaskInput(
            source_task_id=source_task_id,
            draft_harness_name="case_review",
            rationale="Use wider candidate generation.",
        ),
    )

    assert captured["override_spec"]["draft_task_id"] == str(task.id)
    assert captured["override_spec"]["source_task_id"] == str(source_task_id)
    assert result["draft"]["effective_harness_config"]["metadata"] == {
        "draft_task_id": str(task.id),
        "source_task_id": str(source_task_id),
        "rationale": "Use wider candidate generation.",
    }


def test_draft_harness_from_optimization_rejects_noop_best_override(monkeypatch) -> None:
    source_task_id = uuid4()
    task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update_from_optimization",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    source_output = SimpleNamespace(
        case={"case_id": str(uuid4())},
        optimization=SimpleNamespace(
            base_harness_name="wide_v2",
            best_override_spec={
                "base_harness_name": "wide_v2",
                "retrieval_profile_overrides": {},
                "reranker_overrides": {},
            },
            stopped_reason="no_improving_candidates",
            iterations_completed=0,
            best_score={"sort_key": [1, 0, 0]},
            best_gate={"outcome": "passed"},
        ),
    )

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output={},
            task_type="optimize_search_harness_from_case",
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.OptimizeSearchHarnessFromCaseTaskOutput.model_validate",
        lambda output: source_output,
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.get_search_harness",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("no-op optimization should not build an effective harness")
        ),
    )

    try:
        _draft_harness_config_from_optimization_executor(
            session=object(),
            task=task,
            payload=DraftHarnessConfigFromOptimizationTaskInput(
                source_task_id=source_task_id,
                draft_harness_name="case_review",
            ),
        )
    except ValueError as exc:
        assert "no-op config update" in str(exc)
    else:
        raise AssertionError("Expected no-op optimization draft to be rejected")


def test_get_agent_task_action_exposes_eval_control_plane_actions() -> None:
    refresh_action = get_agent_task_action("refresh_eval_failure_cases")
    inspect_action = get_agent_task_action("inspect_eval_failure_case")
    triage_action = get_agent_task_action("triage_eval_failure_case")
    optimize_action = get_agent_task_action("optimize_search_harness_from_case")
    draft_action = get_agent_task_action("draft_harness_config_update_from_optimization")

    assert refresh_action.output_schema_name == "refresh_eval_failure_cases_output"
    assert inspect_action.output_schema_name == "inspect_eval_failure_case_output"
    assert triage_action.output_schema_name == "triage_eval_failure_case_output"
    assert optimize_action.output_schema_name == "optimize_search_harness_from_case_output"
    assert draft_action.output_schema_name == "draft_harness_config_update_output"
    assert draft_action.side_effect_level == "draft_change"


def test_verify_draft_harness_config_executor_writes_verification_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="verify_draft_harness_config",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    target_task_id = uuid4()

    monkeypatch.setattr(
        "app.services.agent_task_actions.verify_draft_harness_config_task",
        lambda session, verification_task, payload: {
            "draft": {"draft_harness_name": "wide_v2_review"},
            "evaluation": {"candidate_harness_name": "wide_v2_review"},
            "verification": {"outcome": "passed"},
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/harness_config_draft_verification.json",
            },
        )(),
    )

    result = _verify_draft_harness_config_executor(
        session=object(),
        task=task,
        payload=VerifyDraftHarnessConfigTaskInput(
            target_task_id=target_task_id,
            baseline_harness_name="wide_v2",
            source_types=["evaluation_queries"],
            limit=10,
        ),
    )

    assert result["verification"]["outcome"] == "passed"
    assert result["artifact_kind"] == "harness_config_draft_verification"


def test_apply_harness_config_update_executor_persists_review_harness(
    monkeypatch,
    tmp_path,
) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/applied_harness_config_update.json",
            },
        )(),
    )
    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=draft_task_id,
            )
        ),
    }

    def fake_resolve(
        session,
        *,
        expected_task_type,
        **_kwargs,
    ):
        return _resolve_payload_by_expected_type(
            resolver_payloads,
            expected_task_type,
        )

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    result = _apply_harness_config_update_executor(
        session=object(),
        task=apply_task,
        payload=ApplyHarnessConfigUpdateTaskInput(
            draft_task_id=draft_task_id,
            verification_task_id=verification_task_id,
            reason="publish review harness",
        ),
    )

    assert result["draft_harness_name"] == "wide_v2_review"
    assert result["applied_override"]["verification_task_id"] == str(verification_task_id)
    assert result["applied_override"]["applied_by"] == "operator@example.com"
    assert Path(result["config_path"]).exists()
    payload = json.loads(Path(result["config_path"]).read_text())
    assert payload["harnesses"]["wide_v2_review"]["base_harness_name"] == "wide_v2"


def test_apply_harness_config_update_executor_attaches_follow_up_evidence(
    monkeypatch,
    tmp_path,
) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )
    created_artifacts = []

    def fake_create_artifact(session, **kwargs):
        artifact = type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": f"/tmp/{kwargs['filename']}",
            },
        )()
        created_artifacts.append((kwargs["artifact_kind"], kwargs["payload"]))
        return artifact

    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        fake_create_artifact,
    )
    verification_output = _verification_output_payload(
        verification_task_id=verification_task_id,
        draft_task_id=draft_task_id,
    )
    verification_output["comprehension_gate"] = {
        "comprehension_passed": True,
        "claim_evidence_alignment": "aligned",
        "change_justification": "publish review harness",
        "predicted_blast_radius": {"changed_scopes": ["reranker_overrides"]},
        "rollback_condition": "rollback on regression",
        "follow_up_plan": {
            "baseline_harness_name": "wide_v2",
            "candidate_harness_name": "wide_v2_review",
            "source_types": ["evaluation_queries"],
            "limit": 10,
        },
        "reasons": [],
    }
    verification_output["follow_up_plan"] = verification_output["comprehension_gate"][
        "follow_up_plan"
    ]
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(output=verification_output),
    }
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda session, *, expected_task_type, **_kwargs: (
            _resolve_payload_by_expected_type(resolver_payloads, expected_task_type)
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.evaluate_search_harness",
        lambda session, request: {
            "baseline_harness_name": request.baseline_harness_name,
            "candidate_harness_name": request.candidate_harness_name,
            "limit": request.limit,
            "total_shared_query_count": 10,
            "total_improved_count": 1,
            "total_regressed_count": 0,
            "total_unchanged_count": 9,
            "sources": [],
        },
    )

    result = _apply_harness_config_update_executor(
        session=object(),
        task=apply_task,
        payload=ApplyHarnessConfigUpdateTaskInput(
            draft_task_id=draft_task_id,
            verification_task_id=verification_task_id,
            reason="publish review harness",
        ),
    )

    assert result["follow_up_summary"]["recommendation"] == "keep_override"
    assert result["follow_up_artifact_kind"] == "follow_up_evaluation_summary"
    assert [kind for kind, _payload in created_artifacts] == [
        "follow_up_evaluation_summary",
        "applied_harness_config_update",
    ]


def test_apply_harness_config_update_executor_rejects_mismatched_verification_target(
    monkeypatch,
) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    other_draft_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=other_draft_task_id,
            )
        ),
    }
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda session, *, expected_task_type, **_kwargs: (
            _resolve_payload_by_expected_type(resolver_payloads, expected_task_type)
        ),
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except ValueError as exc:
        assert "does not target the requested draft task" in str(exc)
    else:
        raise AssertionError("Expected mismatched verifier target to be rejected")


def test_apply_harness_config_update_executor_rejects_failed_verification(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    resolver_payloads = {
        "draft_harness_config_update": SimpleNamespace(
            output=_draft_output_payload(draft_task_id=draft_task_id)
        ),
        "verify_draft_harness_config": SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=draft_task_id,
                outcome="failed",
            )
        ),
    }
    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda session, *, expected_task_type, **_kwargs: (
            _resolve_payload_by_expected_type(resolver_payloads, expected_task_type)
        ),
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except ValueError as exc:
        assert "Only passed draft harness verifications can be applied" in str(exc)
    else:
        raise AssertionError("Expected failed verification to be rejected")


def test_apply_harness_config_update_executor_bubbles_dependency_role_errors(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    def fake_resolve(session, *, dependency_kind, **_kwargs):
        if dependency_kind == "draft_task":
            raise HTTPException(status_code=409, detail="wrong dependency kind")
        return SimpleNamespace(
            output=_verification_output_payload(
                verification_task_id=verification_task_id,
                draft_task_id=draft_task_id,
            )
        )

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail == "wrong dependency kind"
    else:
        raise AssertionError("Expected dependency role validation to bubble")


def test_apply_harness_config_update_executor_bubbles_schema_errors(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    def fake_resolve(session, *, dependency_kind, **_kwargs):
        if dependency_kind == "verification_task":
            raise HTTPException(status_code=409, detail="rerun required")
        return SimpleNamespace(output=_draft_output_payload(draft_task_id=draft_task_id))

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail == "rerun required"
    else:
        raise AssertionError("Expected schema/rerun validation to bubble")


def test_apply_harness_config_update_executor_bubbles_missing_verification(monkeypatch) -> None:
    draft_task_id = uuid4()
    verification_task_id = uuid4()
    apply_task = AgentTask(
        id=uuid4(),
        task_type="apply_harness_config_update",
        status="processing",
        priority=100,
        side_effect_level="promotable",
        requires_approval=True,
        approved_at=datetime.now(UTC),
        approved_by="operator@example.com",
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    def fake_resolve(session, *, dependency_kind, depends_on_task_id, **_kwargs):
        if dependency_kind == "verification_task":
            raise HTTPException(
                status_code=404, detail=f"Target task not found: {depends_on_task_id}"
            )
        return SimpleNamespace(output=_draft_output_payload(draft_task_id=draft_task_id))

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        fake_resolve,
    )

    try:
        _apply_harness_config_update_executor(
            session=object(),
            task=apply_task,
            payload=ApplyHarnessConfigUpdateTaskInput(
                draft_task_id=draft_task_id,
                verification_task_id=verification_task_id,
                reason="publish review harness",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 404
        assert str(verification_task_id) in exc.detail
    else:
        raise AssertionError("Expected missing verification task to bubble")


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


def test_prepare_semantic_generation_brief_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="prepare_semantic_generation_brief",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_id = uuid4()

    monkeypatch.setattr(
        "app.services.agent_task_actions.prepare_semantic_generation_brief",
        lambda session, **kwargs: _semantic_generation_brief_output_payload(
            task_id=task.id,
            document_id=document_id,
        )["brief"],
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_generation_brief.json",
            },
        )(),
    )

    result = _prepare_semantic_generation_brief_executor(
        session=object(),
        task=task,
        payload=PrepareSemanticGenerationBriefTaskInput(
            title="Integration Governance Brief",
            goal="Summarize the knowledge base guidance on integration governance.",
            audience="Operators",
            document_ids=[document_id],
            target_length="medium",
            review_policy="allow_candidate_with_disclosure",
        ),
    )

    assert result["brief"]["title"] == "Integration Governance Brief"
    assert result["artifact_kind"] == "semantic_generation_brief"


def test_prepare_semantic_generation_brief_executor_passes_shadow_arguments(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="prepare_semantic_generation_brief",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_id = uuid4()
    captured: dict = {}

    def _fake_prepare(_session, **kwargs):
        captured.update(kwargs)
        payload = _semantic_generation_brief_output_payload(
            task_id=task.id,
            document_id=document_id,
        )["brief"]
        payload["shadow_mode"] = True
        payload["shadow_candidate_extractor_name"] = kwargs["candidate_extractor_name"]
        payload["shadow_candidate_summary"] = {"candidate_count": 1}
        payload["shadow_candidates"] = [
            {
                "concept_key": "integration_owner",
                "preferred_label": "Integration Owner",
                "max_score": 0.71,
                "source_count": 1,
                "source_types": ["chunk"],
                "category_keys": ["integration_governance"],
                "expected_by_evaluation": True,
                "evidence_refs": [],
                "note": None,
            }
        ]
        return payload

    monkeypatch.setattr(
        "app.services.agent_task_actions.prepare_semantic_generation_brief",
        _fake_prepare,
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_generation_brief.json",
            },
        )(),
    )

    _prepare_semantic_generation_brief_executor(
        session=object(),
        task=task,
        payload=PrepareSemanticGenerationBriefTaskInput(
            title="Integration Governance Brief",
            goal="Summarize the knowledge base guidance on integration governance.",
            audience="Operators",
            document_ids=[document_id],
            target_length="medium",
            review_policy="allow_candidate_with_disclosure",
            include_shadow_candidates=True,
            candidate_extractor_name="concept_ranker_v1",
            candidate_score_threshold=0.4,
            max_shadow_candidates=5,
        ),
    )

    assert captured["include_shadow_candidates"] is True
    assert captured["candidate_extractor_name"] == "concept_ranker_v1"
    assert captured["candidate_score_threshold"] == 0.4
    assert captured["max_shadow_candidates"] == 5


def test_export_semantic_supervision_corpus_executor_writes_artifact(monkeypatch, tmp_path) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="export_semantic_supervision_corpus",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_id = uuid4()

    monkeypatch.setattr(
        "app.services.agent_task_actions.export_semantic_supervision_corpus",
        lambda session, **kwargs: {
            "corpus_name": "semantic_supervision_corpus",
            "document_count": 1,
            "row_count": 4,
            "row_type_counts": {"semantic_evaluation_expectation": 2},
            "label_type_counts": {"expected_concept": 2},
            "rows": [],
            "jsonl_path": str(tmp_path / "semantic_supervision_corpus.jsonl"),
            "success_metrics": [],
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_supervision_corpus.json",
            },
        )(),
    )

    result = _export_semantic_supervision_corpus_executor(
        session=object(),
        task=task,
        payload=ExportSemanticSupervisionCorpusTaskInput(document_ids=[document_id]),
    )

    assert result["corpus"]["document_count"] == 1
    assert result["artifact_kind"] == "semantic_supervision_corpus"


def test_evaluate_semantic_candidate_extractor_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="evaluate_semantic_candidate_extractor",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_id = uuid4()

    monkeypatch.setattr(
        "app.services.agent_task_actions.evaluate_semantic_candidate_extractor",
        lambda session, **kwargs: {
            key: value
            for key, value in _semantic_candidate_evaluation_output_payload(
                document_id=str(document_id)
            ).items()
            if key not in {"artifact_id", "artifact_kind", "artifact_path"}
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_candidate_evaluation.json",
            },
        )(),
    )

    result = _evaluate_semantic_candidate_extractor_executor(
        session=object(),
        task=task,
        payload=EvaluateSemanticCandidateExtractorTaskInput(document_ids=[document_id]),
    )

    assert result["summary"]["candidate_expected_recall"] == 1.0
    assert result["artifact_kind"] == "semantic_candidate_evaluation"


def test_triage_semantic_candidate_disagreements_executor_writes_artifact(monkeypatch) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="triage_semantic_candidate_disagreements",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    evaluation_task_id = uuid4()

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda *args, **kwargs: SimpleNamespace(
            output=_semantic_candidate_evaluation_output_payload(),
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.triage_semantic_candidate_disagreements",
        lambda payload, min_score, include_expected_only: (
            {
                "baseline_extractor_name": "registry_lexical_v1",
                "candidate_extractor_name": "concept_ranker_v1",
                "issue_count": 1,
                "issues": [
                    {
                        "issue_id": "shadow:1",
                        "document_id": str(uuid4()),
                        "concept_key": "integration_owner",
                        "severity": "high",
                        "expected_by_evaluation": True,
                        "in_live_semantics": False,
                        "baseline_found": False,
                        "max_score": 0.71,
                        "summary": "Shadow candidate surfaced outside live semantics.",
                        "evidence_refs": [],
                        "details": {},
                    }
                ],
                "recommended_followups": [],
                "success_metrics": [],
            },
            {
                "outcome": "passed",
                "metrics": {"issue_count": 1},
                "reasons": [],
                "details": {"min_score": min_score, "include_expected_only": include_expected_only},
            },
            {"next_action": "review_shadow_candidates", "confidence": 0.7, "summary": "Review it."},
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_verification_record",
        lambda session, **kwargs: SimpleNamespace(
            verification_id=uuid4(),
            target_task_id=task.id,
            verification_task_id=task.id,
            outcome=kwargs["outcome"],
            metrics=kwargs["metrics"],
            reasons=kwargs["reasons"],
            details=kwargs["details"],
            model_dump=lambda mode="json": {
                "verification_id": str(uuid4()),
                "target_task_id": str(task.id),
                "verification_task_id": str(task.id),
                "verifier_type": kwargs["verifier_type"],
                "outcome": kwargs["outcome"],
                "metrics": kwargs["metrics"],
                "reasons": kwargs["reasons"],
                "details": kwargs["details"],
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_candidate_disagreement_report.json",
            },
        )(),
    )

    result = _triage_semantic_candidate_disagreements_executor(
        session=object(),
        task=task,
        payload=TriageSemanticCandidateDisagreementsTaskInput(
            target_task_id=evaluation_task_id,
        ),
    )

    assert result["disagreement_report"]["issue_count"] == 1
    assert result["recommendation"]["next_action"] == "review_shadow_candidates"
    assert result["artifact_kind"] == "semantic_candidate_disagreement_report"


def test_draft_semantic_grounded_document_executor_writes_artifact_and_markdown(
    monkeypatch,
    tmp_path,
) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="draft_semantic_grounded_document",
        status="processing",
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    brief_task_id = uuid4()
    document_id = uuid4()
    brief_output = _semantic_generation_brief_output_payload(
        task_id=brief_task_id,
        document_id=document_id,
    )
    draft_payload = {
        "document_kind": "knowledge_brief",
        "title": "Integration Governance Brief",
        "goal": "Summarize the knowledge base guidance on integration governance.",
        "audience": "Operators",
        "review_policy": "allow_candidate_with_disclosure",
        "target_length": "medium",
        "brief_task_id": str(brief_task_id),
        "generator_name": "structured_fallback",
        "generator_model": None,
        "used_fallback": True,
        "required_concept_keys": ["integration_threshold"],
        "document_refs": brief_output["brief"]["document_refs"],
        "assertion_index": brief_output["brief"]["semantic_dossier"][0]["assertions"],
        "sections": [
            {
                "section_id": "section:integration_governance",
                "title": "Integration Governance",
                "body_markdown": "- Integration Threshold appears in Integration One.",
                "claim_ids": ["claim:integration_threshold"],
            }
        ],
        "claims": [
            {
                "claim_id": "claim:integration_threshold",
                "section_id": "section:integration_governance",
                "rendered_text": "Integration Threshold appears in Integration One.",
                "concept_keys": ["integration_threshold"],
                "assertion_ids": [
                    brief_output["brief"]["semantic_dossier"][0]["assertions"][0]["assertion_id"]
                ],
                "evidence_labels": ["E1"],
                "source_document_ids": [str(document_id)],
                "support_level": "supported",
                "review_policy_status": "candidate_disclosed",
                "disclosure_note": "Candidate-backed support requires review.",
            }
        ],
        "evidence_pack": brief_output["brief"]["evidence_pack"],
        "markdown": "# Integration Governance Brief\n\n## Evidence Appendix\n",
        "markdown_path": None,
        "warnings": [],
        "success_metrics": [],
    }

    monkeypatch.setattr(
        "app.services.agent_task_actions.resolve_required_dependency_task_output_context",
        lambda session, **kwargs: SimpleNamespace(output=brief_output),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.draft_semantic_grounded_document",
        lambda brief_payload, *, brief_task_id: {
            **draft_payload,
            "brief_task_id": brief_task_id,
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.StorageService",
        lambda: type(
            "FakeStorage",
            (),
            {"get_agent_task_dir": lambda self, _task_id: tmp_path},
        )(),
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_grounded_document_draft.json",
            },
        )(),
    )

    result = _draft_semantic_grounded_document_executor(
        session=object(),
        task=task,
        payload=DraftSemanticGroundedDocumentTaskInput(target_task_id=brief_task_id),
    )

    assert result["draft"]["brief_task_id"] == brief_task_id
    assert result["artifact_kind"] == "semantic_grounded_document_draft"
    assert Path(result["draft"]["markdown_path"]).name == "semantic_grounded_document.md"
    assert (
        Path(result["draft"]["markdown_path"])
        .read_text()
        .startswith("# Integration Governance Brief")
    )


def test_verify_semantic_grounded_document_executor_writes_verification_artifact(
    monkeypatch,
) -> None:
    task = AgentTask(
        id=uuid4(),
        task_type="verify_semantic_grounded_document",
        status="processing",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    draft_task_id = uuid4()

    monkeypatch.setattr(
        "app.services.agent_task_actions.verify_semantic_grounded_document_task",
        lambda session, task, payload: {
            "draft": {
                "document_kind": "knowledge_brief",
                "title": "Integration Governance Brief",
                "goal": "Summarize the knowledge base guidance on integration governance.",
                "audience": "Operators",
                "review_policy": "allow_candidate_with_disclosure",
                "target_length": "medium",
                "brief_task_id": str(uuid4()),
                "generator_name": "structured_fallback",
                "generator_model": None,
                "used_fallback": True,
                "required_concept_keys": ["integration_threshold"],
                "document_refs": [],
                "assertion_index": [],
                "sections": [],
                "claims": [],
                "evidence_pack": [],
                "markdown": "# Integration Governance Brief\n",
                "markdown_path": "/tmp/semantic_grounded_document.md",
                "warnings": [],
                "success_metrics": [],
            },
            "summary": {
                "claim_count": 1,
                "unsupported_claim_count": 0,
                "required_concept_coverage_ratio": 1.0,
            },
            "success_metrics": [],
            "verification": {
                "verification_id": str(uuid4()),
                "target_task_id": str(draft_task_id),
                "verification_task_id": str(task.id),
                "verifier_type": "semantic_grounded_document_gate",
                "outcome": "passed",
                "metrics": {"claim_count": 1},
                "reasons": [],
                "details": {},
                "created_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
            },
        },
    )
    monkeypatch.setattr(
        "app.services.agent_task_actions.create_agent_task_artifact",
        lambda session, **kwargs: type(
            "ArtifactRow",
            (),
            {
                "id": uuid4(),
                "artifact_kind": kwargs["artifact_kind"],
                "storage_path": "/tmp/semantic_grounded_document_verification.json",
            },
        )(),
    )

    result = _verify_semantic_grounded_document_executor(
        session=object(),
        task=task,
        payload=VerifySemanticGroundedDocumentTaskInput(target_task_id=draft_task_id),
    )

    assert result["verification"]["outcome"] == "passed"
    assert result["artifact_kind"] == "semantic_grounded_document_verification"
