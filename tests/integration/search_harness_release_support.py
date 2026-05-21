from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.db.public.retrieval import (
    SearchHarnessEvaluation,
    SearchHarnessEvaluationSource,
    SearchReplayRun,
)


def payload_sha256(payload) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def replay_run(*, replay_run_id, harness_name: str) -> SearchReplayRun:
    now = datetime.now(UTC)
    return SearchReplayRun(
        id=replay_run_id,
        source_type="evaluation_queries",
        status="completed",
        harness_name=harness_name,
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name=harness_name,
        harness_config_json={},
        query_count=4,
        passed_count=4,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        summary_json={"rank_metrics": {"mrr": 1.0, "foreign_top_result_count": 0}},
        error_message=None,
        created_at=now,
        completed_at=now + timedelta(seconds=1),
    )


def build_training_dataset_payload(
    *,
    judgment_set_id,
    judgment_id,
    hard_negative_id,
) -> dict:
    return {
        "schema_name": "retrieval_learning_dataset",
        "schema_version": "1.0",
        "judgment_set": {
            "judgment_set_id": str(judgment_set_id),
            "set_name": "release-audit-learning-set",
        },
        "summary": {
            "training_example_count": 2,
            "judgment_count": 1,
            "hard_negative_count": 1,
        },
        "judgments": [{"judgment_id": str(judgment_id), "source_payload_sha256": "j-sha"}],
        "hard_negatives": [
            {"hard_negative_id": str(hard_negative_id), "source_payload_sha256": "hn-sha"}
        ],
    }


def build_reranker_artifact_payloads(
    *,
    reranker_artifact_id,
    training_run_id,
    judgment_set_id,
    training_dataset_sha256: str,
    evaluation_id,
    release_id: str,
    evaluation_snapshot: dict,
    release_snapshot: dict,
) -> dict[str, object]:
    feature_weights = {
        "keyword_score": 0.7,
        "semantic_score": 0.8,
        "table_type": 0.2,
    }
    harness_overrides = {
        "reranker": {
            "override_type": "retrieval_reranker_artifact",
            "artifact_id": str(reranker_artifact_id),
            "feature_weights": feature_weights,
        }
    }
    artifact_payload = {
        "schema_name": "retrieval_reranker_artifact",
        "schema_version": "1.0",
        "artifact_id": str(reranker_artifact_id),
        "artifact_kind": "linear_feature_weight_candidate",
        "artifact_name": "release-audit-reranker",
        "artifact_version": f"wide_v2+{training_dataset_sha256[:12]}",
        "candidate_harness_name": "wide_v2",
        "base_harness_name": "default_v1",
        "baseline_harness_name": "default_v1",
        "retrieval_training_run": {
            "retrieval_training_run_id": str(training_run_id),
            "judgment_set_id": str(judgment_set_id),
            "training_dataset_sha256": training_dataset_sha256,
            "training_example_count": 2,
        },
        "feature_weights": feature_weights,
        "harness_overrides": harness_overrides,
        "evaluation": evaluation_snapshot,
        "release": release_snapshot,
    }
    artifact_sha256 = payload_sha256(artifact_payload)
    change_impact_report = {
        "schema_name": "retrieval_reranker_change_impact_report",
        "schema_version": "1.0",
        "artifact": {
            "artifact_id": str(reranker_artifact_id),
            "artifact_sha256": artifact_sha256,
            "artifact_name": "release-audit-reranker",
            "artifact_version": f"wide_v2+{training_dataset_sha256[:12]}",
            "candidate_harness_name": "wide_v2",
            "base_harness_name": "default_v1",
        },
        "changed_state_refs": {
            "retrieval_training_run_id": str(training_run_id),
            "judgment_set_id": str(judgment_set_id),
            "training_dataset_sha256": training_dataset_sha256,
            "search_harness_evaluation_id": str(evaluation_id),
            "search_harness_release_id": release_id,
        },
        "affected_trace_summary": {
            "matching_trace_node_count": 0,
            "owner_trace_node_count": 0,
            "owner_trace_edge_count": 0,
            "affected_claim_count": 0,
            "affected_derivation_count": 0,
        },
        "impact_policy": {
            "scope": "ranking_artifact_to_training_sources_and_trace_owners",
            "requires_release_gate": True,
            "requires_semantic_governance_context": True,
            "requires_trace_recheck_when_affected_claim_count_gt_zero": True,
        },
    }
    return {
        "feature_weights": feature_weights,
        "harness_overrides": harness_overrides,
        "artifact_payload": artifact_payload,
        "artifact_sha256": artifact_sha256,
        "change_impact_report": change_impact_report,
        "change_impact_sha256": payload_sha256(change_impact_report),
    }


def seed_search_harness_release_evaluation(session_factory) -> tuple[datetime, UUID]:
    now = datetime.now(UTC)
    evaluation_id = uuid4()
    baseline_replay_run_id = uuid4()
    candidate_replay_run_id = uuid4()

    with session_factory() as session:
        session.add_all(
            [
                replay_run(
                    replay_run_id=baseline_replay_run_id,
                    harness_name="default_v1",
                ),
                replay_run(
                    replay_run_id=candidate_replay_run_id,
                    harness_name="wide_v2",
                ),
                SearchHarnessEvaluation(
                    id=evaluation_id,
                    status="completed",
                    baseline_harness_name="default_v1",
                    candidate_harness_name="wide_v2",
                    limit=4,
                    source_types_json=["evaluation_queries"],
                    harness_overrides_json={},
                    total_shared_query_count=4,
                    total_improved_count=1,
                    total_regressed_count=0,
                    total_unchanged_count=3,
                    summary_json={},
                    error_message=None,
                    created_at=now,
                    completed_at=now + timedelta(seconds=2),
                ),
            ]
        )
        session.flush()
        session.add(
            SearchHarnessEvaluationSource(
                id=uuid4(),
                search_harness_evaluation_id=evaluation_id,
                source_index=0,
                source_type="evaluation_queries",
                baseline_replay_run_id=baseline_replay_run_id,
                candidate_replay_run_id=candidate_replay_run_id,
                baseline_status="completed",
                candidate_status="completed",
                baseline_query_count=4,
                candidate_query_count=4,
                baseline_passed_count=4,
                candidate_passed_count=4,
                baseline_zero_result_count=0,
                candidate_zero_result_count=0,
                baseline_table_hit_count=1,
                candidate_table_hit_count=1,
                baseline_top_result_changes=0,
                candidate_top_result_changes=0,
                baseline_mrr=1.0,
                candidate_mrr=1.0,
                baseline_foreign_top_result_count=0,
                candidate_foreign_top_result_count=0,
                acceptance_checks_json={"no_regressions": True},
                shared_query_count=4,
                improved_count=1,
                regressed_count=0,
                unchanged_count=3,
                created_at=now,
            )
        )
        session.commit()

    return now, evaluation_id


def create_search_harness_release(client, *, evaluation_id: UUID):
    return client.post(
        "/search/harness-releases",
        json={
            "evaluation_id": str(evaluation_id),
            "max_total_regressed_count": 0,
            "min_total_shared_query_count": 1,
            "requested_by": "integration",
            "review_note": "roundtrip",
        },
    )
