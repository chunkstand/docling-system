from __future__ import annotations

import os

import pytest

from tests.integration import retrieval_learning_ledger_support as ledger_support

UTC, UUID, AgentTask, ClaimEvidenceDerivation, EvidencePackageExport, EvidenceTraceEdge = ledger_support.UTC, ledger_support.UUID, ledger_support.AgentTask, ledger_support.ClaimEvidenceDerivation, ledger_support.EvidencePackageExport, ledger_support.EvidenceTraceEdge  # noqa: E501
EvidenceTraceNode, RetrievalJudgmentSet, RetrievalLearningCandidateEvaluation = ledger_support.EvidenceTraceNode, ledger_support.RetrievalJudgmentSet, ledger_support.RetrievalLearningCandidateEvaluation  # noqa: E501
RetrievalLearningCandidateEvaluationRequest, RetrievalRerankerArtifact, RetrievalRerankerArtifactRequest = ledger_support.RetrievalLearningCandidateEvaluationRequest, ledger_support.RetrievalRerankerArtifact, ledger_support.RetrievalRerankerArtifactRequest  # noqa: E501
RetrievalTrainingRun, SearchHarnessEvaluation, SearchHarnessEvaluationResponse, SearchHarnessRelease, SearchHarnessReleaseResponse = ledger_support.RetrievalTrainingRun, ledger_support.SearchHarnessEvaluation, ledger_support.SearchHarnessEvaluationResponse, ledger_support.SearchHarnessRelease, ledger_support.SearchHarnessReleaseResponse  # noqa: E501
SearchReplayRunRequest, SearchRequestRecord, SemanticGovernanceEvent, SimpleNamespace = ledger_support.SearchReplayRunRequest, ledger_support.SearchRequestRecord, ledger_support.SemanticGovernanceEvent, ledger_support.SimpleNamespace  # noqa: E501
TechnicalReportClaimRetrievalFeedback, _make_result, _make_search_request = ledger_support.TechnicalReportClaimRetrievalFeedback, ledger_support._make_result, ledger_support._make_search_request  # noqa: E501
create_retrieval_reranker_artifact, datetime, evaluate_retrieval_learning_candidate = ledger_support.create_retrieval_reranker_artifact, ledger_support.datetime, ledger_support.evaluate_retrieval_learning_candidate  # noqa: E501
materialize_retrieval_learning_dataset, payload_sha256, run_search_replay_suite = ledger_support.materialize_retrieval_learning_dataset, ledger_support.payload_sha256, ledger_support.run_search_replay_suite  # noqa: E501
select, uuid4 = ledger_support.select, ledger_support.uuid4

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def test_claim_feedback_replay_source_drives_learning_candidate_and_artifact(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    now = datetime.now(UTC)
    verification_task_id = uuid4()

    with postgres_integration_harness.session_factory() as session:
        request = _make_search_request(now=now)
        result = _make_result(request_id=request.id, rank=1, result_type="chunk", now=now)
        verification_task = AgentTask(
            id=verification_task_id,
            task_type="verify_technical_report",
            status="completed",
            input_json={},
            result_json={},
            created_at=now,
            updated_at=now,
            completed_at=now,
        )
        source_payload = {
            "schema_name": "technical_report_claim_retrieval_feedback_source",
            "schema_version": "1.0",
            "technical_report_verification_task_id": str(verification_task_id),
            "claim_id": "claim:replay-source",
            "claim_text": "The generated claim overstates the cited evidence.",
            "support_verdict": "unsupported",
            "support_score": 0.18,
            "feedback_status": "rejected",
            "learning_label": "negative",
            "hard_negative_kind": "explicit_irrelevant",
            "source_search_request_ids": [str(request.id)],
            "source_search_request_result_ids": [str(result.id)],
        }
        source_payload_sha256 = str(payload_sha256(source_payload))
        feedback_payload = {
            "schema_name": "technical_report_claim_retrieval_feedback",
            "schema_version": "1.0",
            "feedback_kind": "generation_claim_retrieval_feedback",
            "technical_report_verification_task_id": str(verification_task_id),
            "claim_id": "claim:replay-source",
            "feedback_status": "rejected",
            "learning_label": "negative",
            "hard_negative_kind": "explicit_irrelevant",
            "source_payload_sha256": source_payload_sha256,
            "source": source_payload,
        }
        feedback = TechnicalReportClaimRetrievalFeedback(
            id=uuid4(),
            technical_report_verification_task_id=verification_task_id,
            claim_id="claim:replay-source",
            claim_text="The generated claim overstates the cited evidence.",
            support_verdict="unsupported",
            support_score=0.18,
            feedback_status="rejected",
            learning_label="negative",
            hard_negative_kind="explicit_irrelevant",
            source_search_request_id=request.id,
            search_request_result_id=result.id,
            source_search_request_ids_json=[str(request.id)],
            source_search_request_result_ids_json=[str(result.id)],
            search_request_result_span_ids_json=[],
            retrieval_evidence_span_ids_json=[],
            semantic_ontology_snapshot_ids_json=[],
            semantic_graph_snapshot_ids_json=[],
            retrieval_reranker_artifact_ids_json=[],
            search_harness_release_ids_json=[],
            release_audit_bundle_ids_json=[],
            release_validation_receipt_ids_json=[],
            evidence_refs_json=[],
            retrieval_context_json={
                "primary_query_text": request.query_text,
                "primary_mode": request.mode,
                "primary_harness_name": request.harness_name,
                "primary_reranker_name": request.reranker_name,
                "primary_reranker_version": request.reranker_version,
                "primary_retrieval_profile_name": request.retrieval_profile_name,
                "primary_harness_config": request.harness_config_json,
            },
            feedback_payload_json=feedback_payload,
            feedback_payload_sha256=str(payload_sha256(feedback_payload)),
            source_payload_json=source_payload,
            source_payload_sha256=source_payload_sha256,
            created_at=now,
            updated_at=now,
        )
        session.add_all([request, result, verification_task, feedback])
        session.flush()
        learning_response = materialize_retrieval_learning_dataset(
            session,
            limit=10,
            source_types=["technical_report_claim_feedback"],
            set_name="integration-claim-feedback-replay-source",
            created_by="integration",
        )
        training_run_id = UUID(learning_response["retrieval_training_run_id"])
        feedback_id = feedback.id
        target_result_id = result.chunk_id
        session.commit()

    def fake_execute_search(
        session,
        search_request,
        *,
        origin,
        parent_request_id=None,
        harness_overrides=None,
    ):
        replay_request_id = uuid4()
        replay_result = _make_result(
            request_id=replay_request_id,
            rank=1,
            result_type="chunk",
            now=now,
        )
        assert replay_result.chunk_id != target_result_id
        replay_request = SearchRequestRecord(
            id=replay_request_id,
            parent_request_id=parent_request_id,
            evaluation_id=None,
            run_id=None,
            origin=origin,
            query_text=search_request.query,
            mode=search_request.mode,
            filters_json=(
                search_request.filters.model_dump(exclude_none=True)
                if search_request.filters is not None
                else {}
            ),
            details_json={},
            limit=search_request.limit,
            tabular_query=False,
            harness_name=search_request.harness_name or "default_v1",
            reranker_name="linear_feature_reranker",
            reranker_version="v1",
            retrieval_profile_name=search_request.harness_name or "default_v1",
            harness_config_json={"harness_name": search_request.harness_name or "default_v1"},
            embedding_status="ready",
            embedding_error=None,
            candidate_count=1,
            result_count=1,
            table_hit_count=0,
            duration_ms=2.0,
            created_at=now,
        )
        session.add_all([replay_request, replay_result])
        session.flush()
        return SimpleNamespace(
            request_id=replay_request_id,
            results=[
                SimpleNamespace(
                    result_type="chunk",
                    chunk_id=replay_result.chunk_id,
                    table_id=None,
                    source_filename=replay_result.source_filename,
                    document_id=replay_result.document_id,
                    run_id=replay_result.run_id,
                    score=replay_result.score,
                )
            ],
            table_hit_count=0,
            embedding_status="ready",
            harness_name=search_request.harness_name or "default_v1",
            reranker_name="linear_feature_reranker",
            reranker_version="v1",
            retrieval_profile_name=search_request.harness_name or "default_v1",
            harness_config={"harness_name": search_request.harness_name or "default_v1"},
        )

    monkeypatch.setattr("app.services.search_replays.execute_search", fake_execute_search)

    with postgres_integration_harness.session_factory() as session:
        replay = run_search_replay_suite(
            session,
            SearchReplayRunRequest(
                source_type="technical_report_claim_feedback",
                limit=5,
                harness_name="default_v1",
            ),
        )
        candidate = evaluate_retrieval_learning_candidate(
            session,
            RetrievalLearningCandidateEvaluationRequest(
                retrieval_training_run_id=training_run_id,
                candidate_harness_name="default_v1",
                baseline_harness_name="default_v1",
                source_types=["technical_report_claim_feedback"],
                limit=5,
                requested_by="integration",
            ),
        )
        artifact = create_retrieval_reranker_artifact(
            session,
            RetrievalRerankerArtifactRequest(
                retrieval_training_run_id=training_run_id,
                artifact_name="integration-claim-feedback-reranker",
                candidate_harness_name="claim_feedback_candidate",
                baseline_harness_name="default_v1",
                base_harness_name="default_v1",
                source_types=["technical_report_claim_feedback"],
                limit=5,
                requested_by="integration",
            ),
        )
        session.commit()

    assert replay.status == "completed"
    assert replay.source_type == "technical_report_claim_feedback"
    assert replay.query_count == 1
    assert replay.passed_count == 1
    assert replay.query_results[0].details["claim_feedback_id"] == str(feedback_id)
    assert replay.query_results[0].details["target_rank"] is None
    assert replay.query_results[0].details["claim_feedback_traceability_complete"] is True
    assert replay.query_results[0].details["claim_feedback_traceability_issues"] == []
    assert (
        replay.query_results[0].details["claim_feedback_replay_verdict"]
        == "negative_target_excluded"
    )
    assert candidate.gate_outcome == "passed"
    assert candidate.evaluation.source_types == ["technical_report_claim_feedback"]
    assert artifact.gate_outcome == "passed"
    assert artifact.evaluation.source_types == ["technical_report_claim_feedback"]


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
        return evaluation_response.model_copy(update={"harness_overrides": harness_overrides})

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
    assert (
        artifact_event.event_payload_json["retrieval_reranker_artifact"]["artifact_sha256"]
        == response.artifact_sha256
    )
