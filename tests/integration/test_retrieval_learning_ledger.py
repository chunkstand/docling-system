from __future__ import annotations

import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.db.models import (
    AuditBundleExport,
    AuditBundleValidationReceipt,
    ClaimEvidenceDerivation,
    EvidencePackageExport,
    EvidenceTraceEdge,
    EvidenceTraceNode,
    RetrievalHardNegative,
    RetrievalJudgment,
    RetrievalJudgmentSet,
    RetrievalLearningCandidateEvaluation,
    RetrievalRerankerArtifact,
    RetrievalTrainingRun,
    SearchFeedback,
    SearchHarnessEvaluation,
    SearchHarnessRelease,
    SearchReplayQuery,
    SearchReplayRun,
    SearchRequestRecord,
    SearchRequestResult,
    SearchRequestResultSpan,
    SemanticGovernanceEvent,
)
from app.schemas.search import (
    RetrievalLearningCandidateEvaluationRequest,
    RetrievalRerankerArtifactRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessReleaseResponse,
)
from app.services.retrieval_learning import (
    create_retrieval_reranker_artifact,
    evaluate_retrieval_learning_candidate,
    materialize_retrieval_learning_dataset,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def _make_search_request(*, now: datetime) -> SearchRequestRecord:
    return SearchRequestRecord(
        id=uuid4(),
        parent_request_id=None,
        evaluation_id=None,
        run_id=None,
        origin="api",
        query_text="vent stack sizing",
        mode="hybrid",
        filters_json={},
        details_json={},
        limit=5,
        tabular_query=False,
        harness_name="default_v1",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="default_v1",
        harness_config_json={"harness_name": "default_v1"},
        embedding_status="ready",
        embedding_error=None,
        candidate_count=2,
        result_count=2,
        table_hit_count=1,
        duration_ms=3.0,
        created_at=now,
    )


def _make_result(
    *,
    request_id,
    rank: int,
    result_type: str,
    now: datetime,
) -> SearchRequestResult:
    source_id = uuid4()
    return SearchRequestResult(
        id=uuid4(),
        search_request_id=request_id,
        rank=rank,
        base_rank=rank,
        result_type=result_type,
        document_id=uuid4(),
        run_id=uuid4(),
        chunk_id=source_id if result_type == "chunk" else None,
        table_id=source_id if result_type == "table" else None,
        score=1.0 / rank,
        keyword_score=0.4,
        semantic_score=0.6,
        hybrid_score=0.5,
        rerank_features_json={"rank_feature": rank},
        page_from=rank,
        page_to=rank,
        source_filename="fixture.pdf",
        label=f"{result_type}-{rank}",
        preview_text=f"{result_type} result {rank}",
        created_at=now,
    )


def test_materialize_retrieval_learning_dataset_roundtrip(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    now = datetime.now(UTC)

    with postgres_integration_harness.session_factory() as session:
        search_request = _make_search_request(now=now)
        session.add(search_request)
        session.flush()

        chunk_result = _make_result(
            request_id=search_request.id,
            rank=1,
            result_type="chunk",
            now=now,
        )
        table_result = _make_result(
            request_id=search_request.id,
            rank=2,
            result_type="table",
            now=now,
        )
        session.add_all([chunk_result, table_result])
        session.flush()

        session.add(
            SearchRequestResultSpan(
                id=uuid4(),
                search_request_id=search_request.id,
                search_request_result_id=chunk_result.id,
                retrieval_evidence_span_id=None,
                span_rank=1,
                score_kind="keyword",
                score=0.4,
                source_type="chunk",
                source_id=chunk_result.chunk_id,
                span_index=0,
                page_from=1,
                page_to=1,
                text_excerpt="vent stack sizing evidence",
                content_sha256="chunk-content-sha",
                source_snapshot_sha256="chunk-snapshot-sha",
                metadata_json={"fixture": "retrieval-learning"},
                created_at=now,
            )
        )

        relevant_feedback = SearchFeedback(
            id=uuid4(),
            search_request_id=search_request.id,
            search_request_result_id=table_result.id,
            result_rank=2,
            feedback_type="relevant",
            note="good table",
            created_at=now,
        )
        irrelevant_feedback = SearchFeedback(
            id=uuid4(),
            search_request_id=search_request.id,
            search_request_result_id=chunk_result.id,
            result_rank=1,
            feedback_type="irrelevant",
            note="wrong section",
            created_at=now,
        )
        missing_table_feedback = SearchFeedback(
            id=uuid4(),
            search_request_id=search_request.id,
            search_request_result_id=None,
            result_rank=None,
            feedback_type="missing_table",
            note="need the sizing table",
            created_at=now,
        )
        session.add_all([relevant_feedback, irrelevant_feedback, missing_table_feedback])

        replay_run = SearchReplayRun(
            id=uuid4(),
            source_type="feedback",
            status="completed",
            harness_name="candidate_v2",
            reranker_name="linear_feature_reranker",
            reranker_version="v2",
            retrieval_profile_name="wide_v2",
            harness_config_json={"harness_name": "candidate_v2"},
            query_count=1,
            passed_count=0,
            failed_count=1,
            zero_result_count=0,
            table_hit_count=1,
            top_result_changes=1,
            max_rank_shift=1,
            summary_json={"source_type": "feedback"},
            error_message=None,
            created_at=now,
            completed_at=now,
        )
        session.add(replay_run)
        session.flush()
        replay_query = SearchReplayQuery(
            id=uuid4(),
            replay_run_id=replay_run.id,
            source_search_request_id=search_request.id,
            replay_search_request_id=search_request.id,
            feedback_id=missing_table_feedback.id,
            evaluation_query_id=None,
            query_text=search_request.query_text,
            mode=search_request.mode,
            filters_json={},
            expected_result_type="table",
            expected_top_n=1,
            passed=False,
            result_count=2,
            table_hit_count=1,
            overlap_count=1,
            added_count=1,
            removed_count=0,
            top_result_changed=True,
            max_rank_shift=1,
            details_json={"feedback_type": "missing_table", "source_reason": "feedback_label"},
            created_at=now,
        )
        session.add(replay_query)
        session.flush()

        response = materialize_retrieval_learning_dataset(
            session,
            limit=10,
            source_types=["feedback", "replay"],
            set_name="integration-retrieval-learning",
            created_by="integration",
        )
        training_run_id = response["retrieval_training_run_id"]
        evaluation_id = uuid4()
        release_id = uuid4()
        session.add(
            SearchHarnessEvaluation(
                id=evaluation_id,
                status="completed",
                baseline_harness_name="default_v1",
                candidate_harness_name="candidate_v2",
                limit=5,
                source_types_json=["feedback"],
                harness_overrides_json={},
                total_shared_query_count=1,
                total_improved_count=1,
                total_regressed_count=0,
                total_unchanged_count=0,
                summary_json={},
                error_message=None,
                created_at=now,
                completed_at=now,
            )
        )
        session.flush()
        session.add(
            SearchHarnessRelease(
                id=release_id,
                search_harness_evaluation_id=evaluation_id,
                outcome="passed",
                baseline_harness_name="default_v1",
                candidate_harness_name="candidate_v2",
                limit=5,
                source_types_json=["feedback"],
                thresholds_json={"max_total_regressed_count": 0},
                metrics_json={"total_shared_query_count": 1},
                reasons_json=[],
                details_json={"evaluation_id": str(evaluation_id)},
                evaluation_snapshot_json={"evaluation_id": str(evaluation_id)},
                release_package_sha256="release-package-sha",
                requested_by="integration",
                review_note="learning candidate gate",
                created_at=now,
            )
        )
        session.flush()
        evaluation_response = SearchHarnessEvaluationResponse(
            evaluation_id=evaluation_id,
            status="completed",
            baseline_harness_name="default_v1",
            candidate_harness_name="candidate_v2",
            source_types=["feedback"],
            limit=5,
            total_shared_query_count=1,
            total_improved_count=1,
            total_regressed_count=0,
            total_unchanged_count=0,
            created_at=now,
            completed_at=now,
            sources=[],
        )
        release_response = SearchHarnessReleaseResponse(
            release_id=release_id,
            evaluation_id=evaluation_id,
            outcome="passed",
            baseline_harness_name="default_v1",
            candidate_harness_name="candidate_v2",
            limit=5,
            source_types=["feedback"],
            thresholds={"max_total_regressed_count": 0},
            metrics={"total_shared_query_count": 1},
            reasons=[],
            release_package_sha256="release-package-sha",
            requested_by="integration",
            review_note="learning candidate gate",
            created_at=now,
            details={"evaluation_id": str(evaluation_id)},
            evaluation_snapshot=evaluation_response.model_dump(mode="json"),
        )
        monkeypatch.setattr(
            "app.services.retrieval_learning.evaluate_search_harness",
            lambda session, request: evaluation_response,
        )
        monkeypatch.setattr(
            "app.services.retrieval_learning.record_search_harness_release_gate",
            lambda session, evaluation, payload, *, requested_by=None, review_note=None: (
                release_response
            ),
        )
        candidate_response = evaluate_retrieval_learning_candidate(
            session,
            RetrievalLearningCandidateEvaluationRequest(
                retrieval_training_run_id=UUID(training_run_id),
                candidate_harness_name="candidate_v2",
                source_types=["feedback"],
                limit=5,
                requested_by="integration",
                review_note="learning candidate gate",
            ),
        )
        session.commit()

    monkeypatch.setattr(
        "app.services.audit_bundles.get_settings",
        lambda: SimpleNamespace(
            audit_bundle_signing_key="retrieval-training-secret",
            audit_bundle_signing_key_id="retrieval-training-key",
        ),
    )
    audit_response = postgres_integration_harness.client.post(
        f"/search/retrieval-training-runs/{training_run_id}/audit-bundles",
        json={"created_by": "integration"},
    )
    assert audit_response.status_code == 200
    training_audit_bundle = audit_response.json()
    training_audit_payload = training_audit_bundle["bundle"]["payload"]
    assert training_audit_bundle["bundle_kind"] == "retrieval_training_run_provenance"
    assert training_audit_bundle["integrity"]["complete"] is True
    assert training_audit_payload["audit_checklist"]["complete"] is True
    assert training_audit_payload["integrity"]["training_dataset_hash_matches"] is True
    assert training_audit_payload["integrity"]["judgment_count"] == 4
    assert training_audit_payload["integrity"]["hard_negative_count"] == 3
    assert len(training_audit_payload["retrieval_judgments"]) == 4
    assert len(training_audit_payload["retrieval_hard_negatives"]) == 3
    assert all(
        row["source_payload_sha256"] for row in training_audit_payload["retrieval_judgments"]
    )
    assert all(
        row["source_payload_sha256"]
        for row in training_audit_payload["retrieval_hard_negatives"]
    )
    assert any(
        row["evidence_refs"] for row in training_audit_payload["retrieval_hard_negatives"]
    )
    assert any(
        row["event_kind"] == "retrieval_training_run_materialized"
        for row in training_audit_payload["semantic_governance_events"]
    )
    assert training_audit_payload["source_payload_hashes"]
    assert any(
        edge["usedEntity"].startswith("docling:retrieval_hard_negative:")
        for edge in training_audit_payload["prov"]["wasDerivedFrom"]
    )
    latest_training_audit_response = postgres_integration_harness.client.get(
        f"/search/retrieval-training-runs/{training_run_id}/audit-bundles/latest"
    )
    assert latest_training_audit_response.status_code == 200
    assert latest_training_audit_response.json()["bundle_id"] == training_audit_bundle["bundle_id"]

    receipt_response = postgres_integration_harness.client.post(
        f"/search/audit-bundles/{training_audit_bundle['bundle_id']}/validation-receipts",
        json={"created_by": "integration"},
    )
    assert receipt_response.status_code == 200
    training_receipt = receipt_response.json()
    assert training_receipt["validation_profile"] == "audit_bundle_validation_v1"
    assert training_receipt["validation_status"] == "passed"
    assert training_receipt["receipt"]["audit_bundle"]["bundle_id"] == (
        training_audit_bundle["bundle_id"]
    )
    assert training_receipt["receipt_sha256"] == training_receipt["receipt"]["receipt_sha256"]
    assert training_receipt["prov_jsonld"]["@graph"]
    assert training_receipt["integrity"]["complete"] is True
    assert training_receipt["semantic_governance_valid"] is True
    assert training_receipt["receipt"]["validation_checks"]["semantic_governance_valid"] is True

    receipt_list_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{training_audit_bundle['bundle_id']}/validation-receipts"
    )
    assert receipt_list_response.status_code == 200
    assert receipt_list_response.json()[0]["receipt_id"] == training_receipt["receipt_id"]

    receipt_detail_response = postgres_integration_harness.client.get(
        receipt_response.headers["Location"]
    )
    assert receipt_detail_response.status_code == 200
    assert receipt_detail_response.json()["receipt_id"] == training_receipt["receipt_id"]

    latest_receipt_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{training_audit_bundle['bundle_id']}/validation-receipts/latest"
    )
    assert latest_receipt_response.status_code == 200
    assert latest_receipt_response.json()["receipt_id"] == training_receipt["receipt_id"]

    with postgres_integration_harness.session_factory() as session:
        judgment_sets = session.execute(select(RetrievalJudgmentSet)).scalars().all()
        judgments = session.execute(select(RetrievalJudgment)).scalars().all()
        hard_negatives = session.execute(select(RetrievalHardNegative)).scalars().all()
        training_runs = session.execute(select(RetrievalTrainingRun)).scalars().all()
        candidate_rows = (
            session.execute(select(RetrievalLearningCandidateEvaluation)).scalars().all()
        )
        governance_events = session.execute(select(SemanticGovernanceEvent)).scalars().all()
        audit_bundle_rows = session.execute(select(AuditBundleExport)).scalars().all()
        validation_receipt_rows = (
            session.execute(select(AuditBundleValidationReceipt)).scalars().all()
        )

    assert len(judgment_sets) == 1
    assert len(training_runs) == 1
    assert len(candidate_rows) == 1
    assert len(audit_bundle_rows) == 1
    assert len(validation_receipt_rows) == 1
    assert audit_bundle_rows[0].retrieval_training_run_id == UUID(training_run_id)
    assert audit_bundle_rows[0].bundle_sha256 == training_audit_bundle["bundle_sha256"]
    assert validation_receipt_rows[0].audit_bundle_export_id == UUID(
        training_audit_bundle["bundle_id"]
    )
    assert response["summary"]["judgment_count"] == 4
    assert response["summary"]["positive_count"] == 1
    assert response["summary"]["negative_count"] == 2
    assert response["summary"]["missing_count"] == 1
    assert response["summary"]["hard_negative_count"] == 3
    assert response["summary"]["training_example_count"] == 7
    assert {row.judgment_kind for row in judgments} == {"positive", "negative", "missing"}
    assert {row.hard_negative_kind for row in hard_negatives} >= {
        "explicit_irrelevant",
        "wrong_result_type",
    }
    assert any(row.evidence_refs_json for row in judgments if row.result_type == "chunk")
    assert all(row.source_payload_sha256 for row in judgments)
    assert all(row.source_payload_sha256 for row in hard_negatives)
    assert any(row.evidence_refs_json for row in hard_negatives)
    assert any(row.positive_judgment_id is not None for row in hard_negatives)
    assert all(row.source_search_request_id == row.search_request_id for row in hard_negatives)
    assert training_runs[0].training_dataset_sha256 == response["training_dataset_sha256"]
    assert training_runs[0].example_count == 7
    assert training_runs[0].training_payload_json["summary"]["training_example_count"] == 7
    training_event = next(
        row
        for row in governance_events
        if row.event_kind == "retrieval_training_run_materialized"
    )
    candidate_event = next(
        row
        for row in governance_events
        if row.event_kind == "retrieval_learning_candidate_evaluated"
    )
    assert training_runs[0].semantic_governance_event_id == training_event.id
    assert training_runs[0].search_harness_evaluation_id == (
        candidate_response.search_harness_evaluation_id
    )
    assert training_runs[0].search_harness_release_id == (
        candidate_response.search_harness_release_id
    )
    assert candidate_rows[0].training_dataset_sha256 == response["training_dataset_sha256"]
    assert candidate_rows[0].learning_package_sha256 == (
        candidate_response.learning_package_sha256
    )
    assert candidate_rows[0].semantic_governance_event_id is not None
    assert candidate_rows[0].semantic_governance_event_id == candidate_event.id
    assert training_event.event_payload_json["retrieval_training_run"][
        "training_dataset_sha256"
    ] == response["training_dataset_sha256"]
    assert (
        candidate_event.event_payload_json["retrieval_learning_candidate_evaluation"][
            "training_dataset_sha256"
        ]
        == response["training_dataset_sha256"]
    )


def test_create_retrieval_reranker_artifact_records_change_impact(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    now = datetime.now(UTC)
    judgment_set_id = uuid4()
    training_run_id = uuid4()
    evaluation_id = uuid4()
    release_id = uuid4()
    document_id = uuid4()
    run_id = uuid4()
    table_result_id = uuid4()
    chunk_result_id = uuid4()
    export_id = uuid4()
    source_node_id = uuid4()
    claim_node_id = uuid4()
    training_payload = {
        "schema_name": "retrieval_learning_dataset",
        "schema_version": "1.0",
        "judgment_set": {
            "judgment_set_id": str(judgment_set_id),
            "set_name": "reranker-artifact-set",
        },
        "summary": {
            "training_example_count": 2,
            "judgment_count": 1,
            "hard_negative_count": 1,
        },
        "judgments": [
            {
                "judgment_id": str(uuid4()),
                "source_payload_sha256": "positive-source-sha",
                "judgment_kind": "positive",
                "judgment_label": "operator_relevant",
                "source": {"source_type": "feedback", "source_ref_id": str(uuid4())},
                "query": {"query_text": "fixture table", "mode": "hybrid", "filters": {}},
                "result": {
                    "result_type": "table",
                    "result_id": str(table_result_id),
                    "document_id": str(document_id),
                    "run_id": str(run_id),
                    "rerank_features": {
                        "phrase_overlap": 0.9,
                        "tabular_table_signal": 1.0,
                    },
                    "evidence_refs": [
                        {
                            "retrieval_evidence_span_id": str(uuid4()),
                            "content_sha256": "span-content-sha",
                        }
                    ],
                },
            }
        ],
        "hard_negatives": [
            {
                "hard_negative_id": str(uuid4()),
                "source_payload_sha256": "negative-source-sha",
                "judgment_id": str(uuid4()),
                "hard_negative_kind": "wrong_result_type",
                "source": {"source_type": "replay", "source_ref_id": str(uuid4())},
                "query": {"query_text": "fixture table", "mode": "hybrid", "filters": {}},
                "result": {
                    "result_type": "chunk",
                    "result_id": str(chunk_result_id),
                    "document_id": str(document_id),
                    "run_id": str(run_id),
                    "rerank_features": {
                        "phrase_overlap": 0.1,
                        "tabular_table_signal": 0.0,
                    },
                    "evidence_refs": [],
                },
            }
        ],
    }

    with postgres_integration_harness.session_factory() as session:
        session.add(
            RetrievalJudgmentSet(
                id=judgment_set_id,
                set_name="reranker-artifact-set",
                set_kind="mixed",
                source_types_json=["feedback", "replay"],
                source_limit=10,
                criteria_json={"fixture": "reranker-artifact"},
                summary_json=training_payload["summary"],
                judgment_count=1,
                positive_count=1,
                negative_count=0,
                missing_count=0,
                hard_negative_count=1,
                payload_sha256="training-dataset-sha",
                created_by="integration",
                created_at=now,
            )
        )
        session.add(
            RetrievalTrainingRun(
                id=training_run_id,
                judgment_set_id=judgment_set_id,
                run_kind="materialized_training_dataset",
                status="completed",
                training_dataset_sha256="training-dataset-sha",
                training_payload_json=training_payload,
                summary_json=training_payload["summary"],
                example_count=2,
                positive_count=1,
                negative_count=0,
                missing_count=0,
                hard_negative_count=1,
                created_by="integration",
                created_at=now,
                completed_at=now,
            )
        )
        session.add(
            SearchHarnessEvaluation(
                id=evaluation_id,
                status="completed",
                baseline_harness_name="default_v1",
                candidate_harness_name="learned_reranker_v1",
                limit=5,
                source_types_json=["feedback"],
                harness_overrides_json={},
                total_shared_query_count=1,
                total_improved_count=1,
                total_regressed_count=0,
                total_unchanged_count=0,
                summary_json={},
                error_message=None,
                created_at=now,
                completed_at=now,
            )
        )
        session.add(
            SearchHarnessRelease(
                id=release_id,
                search_harness_evaluation_id=evaluation_id,
                outcome="passed",
                baseline_harness_name="default_v1",
                candidate_harness_name="learned_reranker_v1",
                limit=5,
                source_types_json=["feedback"],
                thresholds_json={"max_total_regressed_count": 0},
                metrics_json={"total_shared_query_count": 1},
                reasons_json=[],
                details_json={"evaluation_id": str(evaluation_id)},
                evaluation_snapshot_json={"evaluation_id": str(evaluation_id)},
                release_package_sha256="release-package-sha",
                requested_by="integration",
                review_note="reranker artifact gate",
                created_at=now,
            )
        )
        session.add(
            EvidencePackageExport(
                id=export_id,
                package_kind="technical_report_claims",
                search_request_id=None,
                agent_task_id=None,
                agent_task_artifact_id=None,
                package_sha256="evidence-package-sha",
                trace_sha256="trace-sha",
                package_payload_json={},
                source_snapshot_sha256s_json=["span-content-sha"],
                operator_run_ids_json=[],
                document_ids_json=[str(document_id)],
                run_ids_json=[str(run_id)],
                claim_ids_json=["claim-1"],
                export_status="completed",
                created_at=now,
            )
        )
        session.flush()
        session.add_all(
            [
                EvidenceTraceNode(
                    id=source_node_id,
                    evidence_manifest_id=None,
                    evidence_package_export_id=export_id,
                    node_key="source-document",
                    node_kind="source_document",
                    source_table="documents",
                    source_id=document_id,
                    source_ref=None,
                    content_sha256="span-content-sha",
                    payload_json={"fixture": "source"},
                    created_at=now,
                ),
                EvidenceTraceNode(
                    id=claim_node_id,
                    evidence_manifest_id=None,
                    evidence_package_export_id=export_id,
                    node_key="claim-1",
                    node_kind="technical_report_claim",
                    source_table=None,
                    source_id=None,
                    source_ref="claim-1",
                    content_sha256="claim-content-sha",
                    payload_json={"claim_id": "claim-1"},
                    created_at=now,
                ),
            ]
        )
        session.flush()
        session.add(
            EvidenceTraceEdge(
                id=uuid4(),
                evidence_manifest_id=None,
                evidence_package_export_id=export_id,
                edge_key="source-to-claim",
                edge_kind="source_supports_claim",
                from_node_id=source_node_id,
                to_node_id=claim_node_id,
                from_node_key="source-document",
                to_node_key="claim-1",
                derivation_sha256="derivation-sha",
                content_sha256="edge-content-sha",
                payload_json={"fixture": "edge"},
                created_at=now,
            )
        )
        session.add(
            ClaimEvidenceDerivation(
                id=uuid4(),
                evidence_package_export_id=export_id,
                agent_task_id=None,
                claim_id="claim-1",
                claim_text="Fixture claim",
                derivation_rule="fixture_source_supports_claim",
                evidence_card_ids_json=[],
                graph_edge_ids_json=[],
                fact_ids_json=[],
                assertion_ids_json=[],
                source_document_ids_json=[str(document_id)],
                source_snapshot_sha256s_json=["span-content-sha"],
                evidence_package_sha256="evidence-package-sha",
                derivation_sha256="derivation-sha",
                created_at=now,
            )
        )
        session.commit()

    evaluation_response = SearchHarnessEvaluationResponse(
        evaluation_id=evaluation_id,
        status="completed",
        baseline_harness_name="default_v1",
        candidate_harness_name="learned_reranker_v1",
        source_types=["feedback"],
        limit=5,
        total_shared_query_count=1,
        total_improved_count=1,
        total_regressed_count=0,
        total_unchanged_count=0,
        created_at=now,
        completed_at=now,
        sources=[],
    )
    release_response = SearchHarnessReleaseResponse(
        release_id=release_id,
        evaluation_id=evaluation_id,
        outcome="passed",
        baseline_harness_name="default_v1",
        candidate_harness_name="learned_reranker_v1",
        limit=5,
        source_types=["feedback"],
        thresholds={"max_total_regressed_count": 0},
        metrics={"total_shared_query_count": 1},
        reasons=[],
        release_package_sha256="release-package-sha",
        requested_by="integration",
        review_note="reranker artifact gate",
        created_at=now,
        details={"evaluation_id": str(evaluation_id)},
        evaluation_snapshot=evaluation_response.model_dump(mode="json"),
    )

    def fake_evaluate_search_harness(session, request, *, harness_overrides=None):
        assert harness_overrides is not None
        overrides = harness_overrides["learned_reranker_v1"]["reranker_overrides"]
        assert overrides["result_type_priority_bonus"] > 0.005
        assert overrides["phrase_overlap_bonus"] > 0.03
        return evaluation_response.model_copy(
            update={"harness_overrides": harness_overrides}
        )

    monkeypatch.setattr(
        "app.services.retrieval_learning.evaluate_search_harness",
        fake_evaluate_search_harness,
    )
    monkeypatch.setattr(
        "app.services.retrieval_learning.record_search_harness_release_gate",
        lambda session, evaluation, payload, *, requested_by=None, review_note=None: (
            release_response
        ),
    )

    with postgres_integration_harness.session_factory() as session:
        response = create_retrieval_reranker_artifact(
            session,
            RetrievalRerankerArtifactRequest(
                retrieval_training_run_id=training_run_id,
                artifact_name="learned-table-reranker",
                candidate_harness_name="learned_reranker_v1",
                baseline_harness_name="default_v1",
                base_harness_name="default_v1",
                source_types=["feedback"],
                limit=5,
                requested_by="integration",
                review_note="reranker artifact gate",
            ),
        )
        session.commit()

    assert response.artifact_name == "learned-table-reranker"
    assert response.gate_outcome == "passed"
    assert response.harness_overrides["learned_reranker_v1"]["override_type"] == (
        "retrieval_reranker_artifact"
    )
    assert response.artifact_sha256
    assert response.change_impact_sha256
    impact = response.change_impact_report["affected_trace_summary"]
    assert impact["matching_trace_node_count"] >= 1
    assert impact["affected_claim_count"] == 1
    assert impact["affected_derivation_count"] == 1

    with postgres_integration_harness.session_factory() as session:
        artifacts = session.execute(select(RetrievalRerankerArtifact)).scalars().all()
        candidate_rows = (
            session.execute(select(RetrievalLearningCandidateEvaluation)).scalars().all()
        )
        governance_events = session.execute(select(SemanticGovernanceEvent)).scalars().all()

    assert len(artifacts) == 1
    assert artifacts[0].artifact_sha256 == response.artifact_sha256
    assert artifacts[0].change_impact_sha256 == response.change_impact_sha256
    assert len(candidate_rows) == 1
    assert candidate_rows[0].details_json["learning_loop_stage"] == (
        "training_dataset_to_reranker_artifact_gate"
    )
    artifact_event = next(
        row
        for row in governance_events
        if row.event_kind == "retrieval_reranker_artifact_materialized"
    )
    assert artifacts[0].semantic_governance_event_id == artifact_event.id
    assert artifact_event.event_payload_json["retrieval_reranker_artifact"][
        "artifact_sha256"
    ] == response.artifact_sha256
