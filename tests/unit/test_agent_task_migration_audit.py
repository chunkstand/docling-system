from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.db.models import AgentTask
from app.schemas.documents import DocumentUploadResponse
from app.schemas.evaluations import EvaluationDetailResponse
from app.schemas.quality import QualityEvaluationCandidateResponse
from app.schemas.search import (
    SearchReplayDiffResponse,
    SearchReplayResponse,
    SearchReplayRunDetailResponse,
    SearchRequestDetailResponse,
)
from app.services.agent_task_actions import (
    get_agent_task_action,
    validate_agent_task_output,
)
from app.services.agent_task_context import build_agent_task_context
from app.services.agent_tasks import list_agent_task_action_definitions

MIGRATED_TASK_TYPES = {
    "get_latest_evaluation",
    "get_latest_semantic_pass",
    "initialize_workspace_ontology",
    "get_active_ontology_snapshot",
    "discover_semantic_bootstrap_candidates",
    "export_semantic_supervision_corpus",
    "evaluate_semantic_candidate_extractor",
    "build_shadow_semantic_graph",
    "evaluate_semantic_relation_extractor",
    "prepare_semantic_generation_brief",
    "list_quality_eval_candidates",
    "replay_search_request",
    "run_search_replay_suite",
    "evaluate_search_harness",
    "verify_search_harness_evaluation",
    "draft_harness_config_update",
    "draft_semantic_grounded_document",
    "verify_draft_harness_config",
    "verify_semantic_grounded_document",
    "triage_replay_regression",
    "triage_semantic_pass",
    "triage_semantic_candidate_disagreements",
    "triage_semantic_graph_disagreements",
    "enqueue_document_reprocess",
    "apply_harness_config_update",
    "draft_semantic_registry_update",
    "draft_ontology_extension",
    "draft_graph_promotions",
    "verify_draft_semantic_registry_update",
    "verify_draft_ontology_extension",
    "verify_draft_graph_promotions",
    "apply_semantic_registry_update",
    "apply_ontology_extension",
    "apply_graph_promotions",
    "build_document_fact_graph",
}


def _task(task_type: str) -> AgentTask:
    now = datetime.now(UTC)
    return AgentTask(
        id=uuid4(),
        task_type=task_type,
        status="completed",
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )


class _AuditSession:
    def get(self, model, key):
        del model, key
        return None


def _search_request_detail() -> SearchRequestDetailResponse:
    now = datetime.now(UTC)
    return SearchRequestDetailResponse(
        search_request_id=uuid4(),
        parent_search_request_id=None,
        evaluation_id=None,
        run_id=None,
        origin="operator",
        query="vent stack",
        mode="keyword",
        filters={},
        details={},
        limit=10,
        tabular_query=False,
        harness_name="default_v1",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="default_v1",
        harness_config={},
        embedding_status="not_requested",
        embedding_error=None,
        candidate_count=2,
        result_count=2,
        table_hit_count=1,
        duration_ms=1.0,
        created_at=now,
        feedback=[],
        results=[],
    )


def test_all_migrated_task_types_expose_output_schema_metadata() -> None:
    definitions = {row.task_type: row for row in list_agent_task_action_definitions()}

    assert MIGRATED_TASK_TYPES.issubset(definitions)
    for task_type in MIGRATED_TASK_TYPES:
        definition = definitions[task_type]
        assert definition.output_schema_name is not None
        assert definition.output_schema_version == "1.0"
        assert definition.output_schema is not None


def test_remaining_backfill_tasks_validate_output_and_build_context() -> None:
    now = datetime.now(UTC)
    evaluation_detail = EvaluationDetailResponse(
        evaluation_id=uuid4(),
        run_id=uuid4(),
        corpus_name="default",
        fixture_name="fixture",
        status="completed",
        query_count=1,
        passed_queries=1,
        failed_queries=0,
        regressed_queries=0,
        improved_queries=0,
        stable_queries=1,
        baseline_run_id=None,
        error_message=None,
        created_at=now,
        completed_at=now,
        summary={},
        query_results=[],
    )
    replay_response = SearchReplayResponse(
        original_request=_search_request_detail(),
        replay_request=_search_request_detail(),
        diff=SearchReplayDiffResponse(),
    )
    replay_run = SearchReplayRunDetailResponse(
        replay_run_id=uuid4(),
        source_type="feedback",
        status="completed",
        harness_name="default_v1",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="default_v1",
        harness_config={},
        query_count=1,
        passed_count=1,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        rank_metrics={},
        created_at=now,
        completed_at=now,
        summary={},
        query_results=[],
    )
    quality_candidate = QualityEvaluationCandidateResponse(
        candidate_type="evaluation_failure",
        reason="missing_table",
        query_text="vent stack",
        mode="keyword",
        filters={},
        evaluation_kind="retrieval",
        expected_result_type=None,
        fixture_name="fixture",
        occurrence_count=1,
        latest_seen_at=now,
        resolution_status="unresolved",
        resolved_at=None,
        resolution_reason=None,
        document_id=None,
        source_filename=None,
        evaluation_id=None,
        search_request_id=None,
        chat_answer_id=None,
        harness_name="default_v1",
    )
    reprocess_response = DocumentUploadResponse(
        document_id=uuid4(),
        run_id=uuid4(),
        status="queued",
        duplicate=False,
    )

    samples = {
        "get_latest_evaluation": {
            "document_id": str(uuid4()),
            "evaluation": evaluation_detail.model_dump(mode="json"),
        },
        "initialize_workspace_ontology": {
            "snapshot": {
                "snapshot_id": str(uuid4()),
                "ontology_name": "portable_upper_ontology",
                "ontology_version": "portable-upper-ontology-v1",
                "upper_ontology_version": "portable-upper-ontology-v1",
                "sha256": "ontology-sha",
                "source_kind": "upper_seed",
                "source_task_id": None,
                "source_task_type": None,
                "concept_count": 0,
                "category_count": 0,
                "relation_count": 2,
                "relation_keys": [
                    "concept_related_to_concept",
                    "document_mentions_concept",
                ],
                "created_at": now.isoformat(),
                "activated_at": now.isoformat(),
            },
            "success_metrics": [],
            "artifact_id": str(uuid4()),
            "artifact_kind": "active_ontology_snapshot",
            "artifact_path": "/tmp/active_ontology_snapshot.json",
        },
        "get_active_ontology_snapshot": {
            "snapshot": {
                "snapshot_id": str(uuid4()),
                "ontology_name": "portable_upper_ontology",
                "ontology_version": "portable-upper-ontology-v1",
                "upper_ontology_version": "portable-upper-ontology-v1",
                "sha256": "ontology-sha",
                "source_kind": "upper_seed",
                "source_task_id": None,
                "source_task_type": None,
                "concept_count": 0,
                "category_count": 0,
                "relation_count": 2,
                "relation_keys": [
                    "concept_related_to_concept",
                    "document_mentions_concept",
                ],
                "created_at": now.isoformat(),
                "activated_at": now.isoformat(),
            },
            "success_metrics": [],
        },
        "list_quality_eval_candidates": {
            "limit": 12,
            "include_resolved": False,
            "candidate_count": 1,
            "candidates": [quality_candidate.model_dump(mode="json")],
        },
        "replay_search_request": {
            "search_request_id": str(uuid4()),
            "replay": replay_response.model_dump(mode="json"),
        },
        "run_search_replay_suite": {
            "source_type": "feedback",
            "harness_name": "default_v1",
            "replay_run": replay_run.model_dump(mode="json"),
        },
        "enqueue_document_reprocess": {
            "document_id": str(reprocess_response.document_id),
            "source_task_id": None,
            "reason": "triage requested reprocess",
            "reprocess": reprocess_response.model_dump(mode="json"),
        },
        "build_document_fact_graph": {
            "document_id": str(uuid4()),
            "run_id": str(uuid4()),
            "semantic_pass_id": str(uuid4()),
            "ontology_snapshot_id": str(uuid4()),
            "ontology_version": "portable-upper-ontology-v1",
            "fact_count": 1,
            "approved_fact_count": 1,
            "entity_count": 2,
            "relation_counts": {"document_mentions_concept": 1},
            "facts": [
                {
                    "fact_id": str(uuid4()),
                    "document_id": str(uuid4()),
                    "run_id": str(uuid4()),
                    "semantic_pass_id": str(uuid4()),
                    "relation_key": "document_mentions_concept",
                    "relation_label": "Document Mentions Concept",
                    "subject_entity_key": "document:1",
                    "subject_label": "Doc",
                    "object_entity_key": "concept:integration_threshold",
                    "object_label": "Integration Threshold",
                    "object_value_text": None,
                    "review_status": "approved",
                    "assertion_id": str(uuid4()),
                    "evidence_ids": [str(uuid4())],
                }
            ],
            "success_metrics": [],
            "artifact_id": str(uuid4()),
            "artifact_kind": "semantic_fact_graph",
            "artifact_path": "/tmp/semantic_fact_graph.json",
        },
    }

    for task_type, sample in samples.items():
        validated = validate_agent_task_output(task_type, sample)
        context = build_agent_task_context(
            _AuditSession(), _task(task_type), {"payload": validated}
        )
        assert context is not None
        action = get_agent_task_action(task_type)
        assert context.output_schema_name == action.output_schema_name
        expected_output = action.output_model.model_validate(validated)
        actual_output = action.output_model.model_validate(context.output)
        assert actual_output.model_dump(mode="json", exclude_none=True) == (
            expected_output.model_dump(mode="json", exclude_none=True)
        )
