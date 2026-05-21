from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.db.public.retrieval import (
    RetrievalHardNegative,
    RetrievalJudgment,
    RetrievalJudgmentSet,
    RetrievalLearningCandidateEvaluation,
    RetrievalRerankerArtifact,
    RetrievalTrainingRun,
)
from app.services.semantic_governance import record_semantic_governance_event
from tests.integration.search_harness_release_support import (
    build_reranker_artifact_payloads,
    build_training_dataset_payload,
    payload_sha256,
)


def materialize_search_harness_release_learning_records(
    session_factory,
    *,
    now: datetime,
    evaluation_id: UUID,
    release_body: dict[str, object],
) -> dict[str, object]:
    release_id = UUID(str(release_body["release_id"]))
    judgment_set_id = uuid4()
    training_run_id = uuid4()
    candidate_id = uuid4()
    judgment_id = uuid4()
    hard_negative_id = uuid4()
    training_payload = build_training_dataset_payload(
        judgment_set_id=judgment_set_id,
        judgment_id=judgment_id,
        hard_negative_id=hard_negative_id,
    )
    training_dataset_sha256 = payload_sha256(training_payload)
    common_result_kwargs = {
        "source_type": "feedback",
        "source_ref_id": None,
        "search_feedback_id": None,
        "search_replay_query_id": None,
        "search_replay_run_id": None,
        "evaluation_query_id": None,
        "source_search_request_id": None,
        "search_request_id": None,
        "search_request_result_id": None,
        "document_id": uuid4(),
        "run_id": uuid4(),
        "query_text": "fixture query",
        "mode": "hybrid",
        "filters_json": {},
        "expected_result_type": "table",
        "expected_top_n": 1,
    }

    with session_factory() as session:
        session.add(
            RetrievalJudgmentSet(
                id=judgment_set_id,
                set_name="release-audit-learning-set",
                set_kind="mixed",
                source_types_json=["feedback", "replay"],
                source_limit=10,
                criteria_json={"fixture": "release-audit"},
                summary_json={"training_example_count": 2},
                judgment_count=1,
                positive_count=1,
                negative_count=0,
                missing_count=0,
                hard_negative_count=1,
                payload_sha256=training_dataset_sha256,
                created_by="integration",
                created_at=now,
            )
        )
        training_run = RetrievalTrainingRun(
            id=training_run_id,
            judgment_set_id=judgment_set_id,
            run_kind="materialized_training_dataset",
            status="completed",
            search_harness_evaluation_id=evaluation_id,
            search_harness_release_id=release_id,
            training_dataset_sha256=training_dataset_sha256,
            training_payload_json=training_payload,
            summary_json={"training_example_count": 2},
            example_count=2,
            positive_count=1,
            negative_count=0,
            missing_count=0,
            hard_negative_count=1,
            created_by="integration",
            created_at=now,
            completed_at=now + timedelta(seconds=3),
        )
        session.add(training_run)
        session.flush()
        training_event = record_semantic_governance_event(
            session,
            event_kind="retrieval_training_run_materialized",
            governance_scope=f"retrieval_training:{training_run_id}",
            subject_table="retrieval_training_runs",
            subject_id=training_run_id,
            search_harness_evaluation_id=evaluation_id,
            search_harness_release_id=release_id,
            event_payload={
                "retrieval_training_run": {
                    "retrieval_training_run_id": str(training_run_id),
                    "training_dataset_sha256": training_dataset_sha256,
                }
            },
            deduplication_key=f"release-audit-training-run:{training_run_id}",
            created_by="integration",
        )
        training_run.semantic_governance_event_id = training_event.id
        session.add(
            RetrievalJudgment(
                id=judgment_id,
                judgment_set_id=judgment_set_id,
                judgment_kind="positive",
                judgment_label="relevant",
                result_rank=1,
                result_type="table",
                result_id=uuid4(),
                score=0.9,
                harness_name="default_v1",
                reranker_name="linear_feature_reranker",
                reranker_version="v1",
                retrieval_profile_name="default_v1",
                rerank_features_json={},
                evidence_refs_json=[{"source": "fixture"}],
                rationale="relevant table",
                payload_json={"fixture": "judgment"},
                source_payload_sha256="j-sha",
                deduplication_key=f"release-audit-judgment:{judgment_id}",
                created_at=now,
                **common_result_kwargs,
            )
        )
        session.flush()
        session.add(
            RetrievalHardNegative(
                id=hard_negative_id,
                judgment_set_id=judgment_set_id,
                judgment_id=judgment_id,
                positive_judgment_id=judgment_id,
                hard_negative_kind="explicit_irrelevant",
                result_rank=2,
                result_type="chunk",
                result_id=uuid4(),
                score=0.2,
                rerank_features_json={},
                evidence_refs_json=[{"source": "fixture"}],
                reason="wrong chunk",
                details_json={"fixture": "hard-negative"},
                source_payload_sha256="hn-sha",
                deduplication_key=f"release-audit-hard-negative:{hard_negative_id}",
                created_at=now,
                **common_result_kwargs,
            )
        )
        candidate = RetrievalLearningCandidateEvaluation(
            id=candidate_id,
            retrieval_training_run_id=training_run_id,
            judgment_set_id=judgment_set_id,
            search_harness_evaluation_id=evaluation_id,
            search_harness_release_id=release_id,
            training_dataset_sha256=training_dataset_sha256,
            training_example_count=2,
            positive_count=1,
            negative_count=0,
            missing_count=0,
            hard_negative_count=1,
            baseline_harness_name="default_v1",
            candidate_harness_name="wide_v2",
            source_types_json=["evaluation_queries"],
            limit=4,
            status="completed",
            gate_outcome="passed",
            thresholds_json={"max_total_regressed_count": 0},
            metrics_json={"total_shared_query_count": 4},
            reasons_json=[],
            evaluation_snapshot_json=release_body["evaluation_snapshot"],
            release_snapshot_json=release_body,
            details_json={"fixture": "release-audit-learning-candidate"},
            learning_package_sha256="learning-package-sha",
            created_by="integration",
            review_note="learning candidate audit",
            created_at=now,
            completed_at=now + timedelta(seconds=4),
        )
        session.add(candidate)
        session.flush()
        candidate_event = record_semantic_governance_event(
            session,
            event_kind="retrieval_learning_candidate_evaluated",
            governance_scope=f"retrieval_learning:{training_run_id}",
            subject_table="retrieval_learning_candidate_evaluations",
            subject_id=candidate_id,
            search_harness_evaluation_id=evaluation_id,
            search_harness_release_id=release_id,
            event_payload={
                "retrieval_learning_candidate_evaluation": {
                    "candidate_evaluation_id": str(candidate_id),
                    "retrieval_training_run_id": str(training_run_id),
                    "training_dataset_sha256": training_dataset_sha256,
                    "learning_package_sha256": "learning-package-sha",
                }
            },
            deduplication_key=f"release-audit-learning-candidate:{candidate_id}",
            created_by="integration",
        )
        candidate.semantic_governance_event_id = candidate_event.id
        reranker_artifact_id = uuid4()
        reranker_payloads = build_reranker_artifact_payloads(
            reranker_artifact_id=reranker_artifact_id,
            training_run_id=training_run_id,
            judgment_set_id=judgment_set_id,
            training_dataset_sha256=training_dataset_sha256,
            evaluation_id=evaluation_id,
            release_id=str(release_body["release_id"]),
            evaluation_snapshot=release_body["evaluation_snapshot"],
            release_snapshot=release_body,
        )
        reranker_artifact = RetrievalRerankerArtifact(
            id=reranker_artifact_id,
            retrieval_training_run_id=training_run_id,
            judgment_set_id=judgment_set_id,
            retrieval_learning_candidate_evaluation_id=candidate_id,
            search_harness_evaluation_id=evaluation_id,
            search_harness_release_id=release_id,
            artifact_kind="linear_feature_weight_candidate",
            artifact_name="release-audit-reranker",
            artifact_version=f"wide_v2+{training_dataset_sha256[:12]}",
            status="evaluated",
            gate_outcome="passed",
            baseline_harness_name="default_v1",
            candidate_harness_name="wide_v2",
            source_types_json=["evaluation_queries"],
            limit=4,
            training_dataset_sha256=training_dataset_sha256,
            training_example_count=2,
            positive_count=1,
            negative_count=0,
            missing_count=0,
            hard_negative_count=1,
            thresholds_json={"max_total_regressed_count": 0},
            metrics_json={"total_shared_query_count": 4},
            reasons_json=[],
            feature_weights_json=reranker_payloads["feature_weights"],
            harness_overrides_json=reranker_payloads["harness_overrides"],
            artifact_payload_json=reranker_payloads["artifact_payload"],
            evaluation_snapshot_json=release_body["evaluation_snapshot"],
            release_snapshot_json=release_body,
            change_impact_report_json=reranker_payloads["change_impact_report"],
            artifact_sha256=reranker_payloads["artifact_sha256"],
            change_impact_sha256=reranker_payloads["change_impact_sha256"],
            created_by="integration",
            review_note="reranker artifact audit",
            created_at=now,
            completed_at=now + timedelta(seconds=5),
        )
        session.add(reranker_artifact)
        session.flush()
        artifact_event = record_semantic_governance_event(
            session,
            event_kind="retrieval_reranker_artifact_materialized",
            governance_scope=f"retrieval_reranker_artifact:{reranker_artifact_id}",
            subject_table="retrieval_reranker_artifacts",
            subject_id=reranker_artifact_id,
            search_harness_evaluation_id=evaluation_id,
            search_harness_release_id=release_id,
            event_payload={
                "retrieval_reranker_artifact": {
                    "artifact_id": str(reranker_artifact_id),
                    "retrieval_training_run_id": str(training_run_id),
                    "training_dataset_sha256": training_dataset_sha256,
                    "artifact_sha256": reranker_payloads["artifact_sha256"],
                    "change_impact_sha256": reranker_payloads["change_impact_sha256"],
                }
            },
            deduplication_key=f"release-audit-reranker-artifact:{reranker_artifact_id}",
            created_by="integration",
        )
        reranker_artifact.semantic_governance_event_id = artifact_event.id
        session.commit()

    return {
        "training_run_id": training_run_id,
        "training_dataset_sha256": training_dataset_sha256,
        "reranker_artifact_id": reranker_artifact_id,
        "reranker_payloads": reranker_payloads,
    }
