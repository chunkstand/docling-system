from __future__ import annotations

import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.db.models import (
    AgentTask,
    AgentTaskArtifact,
    AuditBundleExport,
    AuditBundleValidationReceipt,
    ClaimEvidenceDerivation,
    ClaimSupportFixtureSet,
    ClaimSupportReplayAlertFixtureCorpusRow,
    ClaimSupportReplayAlertFixtureCorpusSnapshot,
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
    SearchHarnessEvaluationSource,
    SearchHarnessRelease,
    SearchHarnessReleaseReadinessAssessment,
    SearchReplayQuery,
    SearchReplayRun,
    SearchRequestRecord,
    SearchRequestResult,
    SearchRequestResultSpan,
    SemanticGovernanceEvent,
    TechnicalReportClaimRetrievalFeedback,
)
from app.schemas.search import (
    RetrievalLearningCandidateEvaluationRequest,
    RetrievalRerankerArtifactRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessReleaseResponse,
)
from app.services.claim_support_replay_alert_fixture_corpus import (
    ensure_active_replay_alert_fixture_corpus_snapshot,
)
from app.services.evidence import payload_sha256
from app.services.retrieval_learning import (
    create_retrieval_reranker_artifact,
    evaluate_retrieval_learning_candidate,
    materialize_retrieval_learning_dataset,
)
from app.services.semantic_governance import record_semantic_governance_event

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


def _make_replay_run(
    *,
    replay_run_id,
    harness_name: str,
    now: datetime,
) -> SearchReplayRun:
    return SearchReplayRun(
        id=replay_run_id,
        source_type="evaluation_queries",
        status="completed",
        harness_name=harness_name,
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name=harness_name,
        harness_config_json={},
        query_count=1,
        passed_count=1,
        failed_count=0,
        zero_result_count=0,
        table_hit_count=1,
        top_result_changes=0,
        max_rank_shift=0,
        summary_json={"rank_metrics": {"mrr": 1.0, "foreign_top_result_count": 0}},
        error_message=None,
        created_at=now,
        completed_at=now,
    )


def _claim_support_learning_fixture(
    *,
    case_id: str,
    expected_verdict: str,
    hard_case_kind: str,
    rendered_text: str,
    evidence_excerpt: str | None,
) -> dict:
    document_id = uuid4()
    run_id = uuid4()
    request_id = uuid4()
    search_result_id = uuid4()
    chunk_id = uuid4()
    evidence_card_id = f"card:{case_id}:source"
    evidence_card_ids = [evidence_card_id] if evidence_excerpt is not None else []
    evidence_cards = (
        [
            {
                "evidence_card_id": evidence_card_id,
                "evidence_kind": "source_evidence",
                "source_type": "chunk",
                "source_locator": f"chunk:{case_id}:source",
                "chunk_id": str(chunk_id),
                "document_id": str(document_id),
                "run_id": str(run_id),
                "page_from": 3,
                "page_to": 3,
                "excerpt": evidence_excerpt,
                "source_search_request_ids": [str(request_id)],
                "source_search_request_result_ids": [str(search_result_id)],
                "metadata": {"fixture": "claim-support-replay-alert-corpus"},
            }
        ]
        if evidence_excerpt is not None
        else []
    )
    return {
        "case_id": case_id,
        "description": f"{hard_case_kind} replay-alert fixture",
        "hard_case_kind": hard_case_kind,
        "expected_verdict": expected_verdict,
        "claim_id": f"claim:{case_id}",
        "draft_payload": {
            "document_kind": "technical_report",
            "title": "Replay alert fixture",
            "goal": "Evaluate claim support replay alerts.",
            "claims": [
                {
                    "claim_id": f"claim:{case_id}",
                    "rendered_text": rendered_text,
                    "source_search_request_ids": [str(request_id)],
                    "source_search_request_result_ids": [str(search_result_id)],
                    "source_document_ids": [str(document_id)],
                    "evidence_card_ids": evidence_card_ids,
                }
            ],
            "evidence_cards": evidence_cards,
            "markdown": rendered_text,
        },
        "replay_alert_source": {
            "candidate_identity_sha256": f"candidate:{case_id}",
            "draft_source": "reconstructed_claim_derivation",
        },
    }


def _receipt_payload(payload: dict) -> dict:
    basis = dict(payload)
    return {**basis, "receipt_sha256": payload_sha256(basis)}


def _seed_governed_claim_support_replay_alert_corpus(
    session,
    *,
    now: datetime,
    fixtures: list[dict],
) -> ClaimSupportReplayAlertFixtureCorpusSnapshot:
    task_id = uuid4()
    session.add(
        AgentTask(
            id=task_id,
            task_type="claim_support_replay_alert_fixture_promotion",
            status="completed",
            priority=100,
            side_effect_level="promotable",
            requires_approval=False,
            input_json={},
            result_json={},
            attempts=1,
            workflow_version="claim_support_policy_change_impact_replay_v1",
            model_settings_json={},
            created_at=now,
            updated_at=now,
            completed_at=now,
        )
    )
    fixture_set_id = uuid4()
    fixture_set_sha256 = payload_sha256(
        {
            "schema_name": "claim_support_fixture_set",
            "fixture_set_name": "retrieval_learning_replay_alert_corpus",
            "fixture_set_version": "v1",
            "fixtures": fixtures,
        }
    )
    session.add(
        ClaimSupportFixtureSet(
            id=fixture_set_id,
            fixture_set_name="retrieval_learning_replay_alert_corpus",
            fixture_set_version="v1",
            status="active",
            fixture_set_sha256=fixture_set_sha256,
            fixture_count=len(fixtures),
            hard_case_kinds_json=sorted({row["hard_case_kind"] for row in fixtures}),
            verdicts_json=sorted({row["expected_verdict"] for row in fixtures}),
            fixtures_json=fixtures,
            metadata_json={"source": "integration"},
            created_at=now,
        )
    )
    escalation_event_ids = []
    change_impact_ids = []
    for fixture in fixtures:
        change_impact_id = uuid4()
        change_impact_ids.append(change_impact_id)
        escalation_event = record_semantic_governance_event(
            session,
            event_kind="claim_support_policy_impact_replay_escalated",
            governance_scope=f"claim_support_replay_alert:{fixture['case_id']}",
            subject_table="claim_support_policy_change_impacts",
            subject_id=change_impact_id,
            task_id=task_id,
            event_payload={
                "claim_support_policy_impact_replay_escalation": {
                    "case_id": fixture["case_id"],
                    "change_impact_id": str(change_impact_id),
                }
            },
            deduplication_key=(
                "test-replay-alert-escalation:"
                f"{fixture_set_id}:{fixture['case_id']}"
            ),
            created_by="integration",
        )
        escalation_event_ids.append(escalation_event.id)
    candidates = [
        {
            "candidate_id": fixture["replay_alert_source"]["candidate_identity_sha256"],
            "candidate_identity_sha256": fixture["replay_alert_source"][
                "candidate_identity_sha256"
            ],
            "case_id": fixture["case_id"],
            "fixture_sha256": payload_sha256(fixture),
            "change_impact_id": str(change_impact_id),
            "escalation_event_ids": [str(escalation_event_id)],
            "latest_escalation_event_id": str(escalation_event_id),
        }
        for fixture, change_impact_id, escalation_event_id in zip(
            fixtures,
            change_impact_ids,
            escalation_event_ids,
            strict=True,
        )
    ]
    promotion_payload = _receipt_payload(
        {
            "schema_name": "claim_support_policy_impact_fixture_promotion",
            "schema_version": "1.0",
            "fixture_set_id": str(fixture_set_id),
            "fixture_set_name": "retrieval_learning_replay_alert_corpus",
            "fixture_set_version": "v1",
            "fixture_set_sha256": fixture_set_sha256,
            "fixture_count": len(fixtures),
            "candidate_count": len(candidates),
            "source_change_impact_ids": [str(value) for value in change_impact_ids],
            "source_escalation_event_ids": [str(value) for value in escalation_event_ids],
            "candidates": candidates,
        }
    )
    promotion_artifact = AgentTaskArtifact(
        id=uuid4(),
        task_id=task_id,
        attempt_id=None,
        artifact_kind="claim_support_policy_impact_fixture_promotion",
        storage_path=None,
        payload_json=promotion_payload,
        created_at=now,
    )
    session.add(promotion_artifact)
    session.flush()
    record_semantic_governance_event(
        session,
        event_kind="claim_support_policy_impact_fixture_promoted",
        governance_scope="claim_support_policy:retrieval_learning_replay_alert_corpus:v1",
        subject_table="claim_support_fixture_sets",
        subject_id=fixture_set_id,
        task_id=task_id,
        agent_task_artifact_id=promotion_artifact.id,
        receipt_sha256=promotion_payload["receipt_sha256"],
        event_payload={"claim_support_policy_impact_fixture_promotion": promotion_payload},
        deduplication_key=(
            "test-replay-alert-fixture-promotion:"
            f"{fixture_set_id}:{promotion_payload['receipt_sha256']}"
        ),
        created_by="integration",
    )
    snapshot = ensure_active_replay_alert_fixture_corpus_snapshot(
        session,
        recorded_by="integration",
    )
    assert snapshot is not None
    assert snapshot.fixture_count == len(fixtures)
    assert snapshot.semantic_governance_event_id is not None
    assert snapshot.governance_artifact_id is not None
    return snapshot


def test_materialize_retrieval_learning_dataset_from_governed_replay_alert_corpus(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    now = datetime.now(UTC)
    fixtures = [
        _claim_support_learning_fixture(
            case_id="replay-alert-supported",
            expected_verdict="supported",
            hard_case_kind="policy_change_supported",
            rendered_text="The policy exception is supported by the cited record.",
            evidence_excerpt="The record states the exception is authorized.",
        ),
        _claim_support_learning_fixture(
            case_id="replay-alert-unsupported",
            expected_verdict="unsupported",
            hard_case_kind="policy_change_unsupported",
            rendered_text="The policy exception is not supported by the cited record.",
            evidence_excerpt="The cited record discusses a different policy.",
        ),
        _claim_support_learning_fixture(
            case_id="replay-alert-insufficient",
            expected_verdict="insufficient_evidence",
            hard_case_kind="policy_change_insufficient_evidence",
            rendered_text="The policy exception lacks traceable source support.",
            evidence_excerpt="The cited record does not resolve the policy exception.",
        ),
    ]
    expected_chunk_ids = {
        fixture["draft_payload"]["evidence_cards"][0]["chunk_id"]
        for fixture in fixtures
        if fixture["expected_verdict"] in {"supported", "unsupported"}
    }
    source_search_result_ids = {
        fixture["draft_payload"]["evidence_cards"][0]["source_search_request_result_ids"][0]
        for fixture in fixtures
        if fixture["draft_payload"]["evidence_cards"]
    }

    with postgres_integration_harness.session_factory() as session:
        snapshot = _seed_governed_claim_support_replay_alert_corpus(
            session,
            now=now,
            fixtures=fixtures,
        )
        snapshot_id = str(snapshot.id)
        snapshot_sha256 = snapshot.snapshot_sha256
        response = materialize_retrieval_learning_dataset(
            session,
            limit=10,
            source_types=["claim_support_replay_alert_corpus"],
            set_name="integration-replay-alert-corpus-learning",
            created_by="integration",
        )
        training_run_id = response["retrieval_training_run_id"]
        judgment_set_id = UUID(response["judgment_set_id"])
        session.commit()

    assert response["summary"]["source_types"] == ["claim_support_replay_alert_corpus"]
    assert response["summary"]["judgment_count"] == 3
    assert response["summary"]["positive_count"] == 1
    assert response["summary"]["negative_count"] == 1
    assert response["summary"]["missing_count"] == 1
    assert response["summary"]["hard_negative_count"] == 1
    assert response["summary"]["training_example_count"] == 4
    assert response["summary"]["judgment_counts_by_source_type"] == {
        "claim_support_replay_alert_corpus": 3
    }

    with postgres_integration_harness.session_factory() as session:
        judgment_set = session.get(RetrievalJudgmentSet, judgment_set_id)
        judgments = list(
            session.scalars(
                select(RetrievalJudgment)
                .where(RetrievalJudgment.judgment_set_id == judgment_set_id)
                .order_by(RetrievalJudgment.deduplication_key.asc())
            )
        )
        hard_negatives = list(
            session.scalars(
                select(RetrievalHardNegative)
                .where(RetrievalHardNegative.judgment_set_id == judgment_set_id)
                .order_by(RetrievalHardNegative.deduplication_key.asc())
            )
        )
        training_run = session.get(RetrievalTrainingRun, UUID(training_run_id))

    assert judgment_set is not None
    assert judgment_set.set_kind == "claim_support_replay_alert_corpus"
    assert judgment_set.source_types_json == ["claim_support_replay_alert_corpus"]
    assert judgment_set.criteria_json["claim_support_replay_alert_corpus"][
        "snapshot_governance_required"
    ] is True
    assert training_run is not None
    assert training_run.training_payload_json["judgment_set"]["criteria"][
        "claim_support_replay_alert_corpus"
    ]["row_lineage_required"] == [
        "fixture_expected_verdict",
        "fixture_hard_case_kind",
        "fixture_sha256",
        "promotion_event",
        "promotion_artifact",
        "source_change_impact_ids",
        "source_escalation_events",
    ]
    assert {row.source_type for row in judgments} == {
        "claim_support_replay_alert_corpus"
    }
    assert {row.judgment_kind for row in judgments} == {
        "positive",
        "negative",
        "missing",
    }
    assert {str(row.result_id) for row in judgments if row.result_id} == expected_chunk_ids
    assert all(row.result_id is None for row in judgments if row.judgment_kind == "missing")
    assert all(row.evidence_refs_json for row in judgments)
    assert not {
        str(row.result_id)
        for row in judgments
        if row.result_id and str(row.result_id) in source_search_result_ids
    }
    assert all(row.search_request_id is None for row in judgments)
    assert all(row.search_request_result_id is None for row in judgments)
    assert all(row.source_payload_sha256 for row in judgments)
    assert len(hard_negatives) == 1
    assert hard_negatives[0].source_type == "claim_support_replay_alert_corpus"
    assert hard_negatives[0].hard_negative_kind == "explicit_irrelevant"
    assert hard_negatives[0].source_payload_sha256
    source_details = judgments[0].payload_json["source_details"]
    assert source_details["snapshot"]["snapshot_id"] == snapshot_id
    assert source_details["snapshot"]["snapshot_sha256"] == snapshot_sha256
    assert source_details["snapshot"]["governance_integrity"]["complete"] is True
    assert source_details["row"]["source_change_impact_ids"]
    assert source_details["row"]["source_escalation_event_ids"]
    assert source_details["row"]["promotion_event_id"]
    assert source_details["row"]["promotion_artifact_id"]

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
    audit_bundle = audit_response.json()
    audit_payload = audit_bundle["bundle"]["payload"]
    assert audit_payload["audit_checklist"]["complete"] is True
    assert audit_payload["integrity"]["judgment_count"] == 3
    assert audit_payload["integrity"]["hard_negative_count"] == 1
    assert (
        audit_payload["integrity"][
            "claim_support_replay_alert_corpus_lineage_complete"
        ]
        is True
    )
    assert (
        audit_payload["audit_checklist"][
            "claim_support_replay_alert_corpus_lineage_complete"
        ]
        is True
    )
    assert {
        row["source_type"] for row in audit_payload["retrieval_judgments"]
    } == {"claim_support_replay_alert_corpus"}
    assert all(
        row["payload"]["source_details"]["snapshot"]["snapshot_sha256"]
        == snapshot_sha256
        for row in audit_payload["retrieval_judgments"]
    )
    assert len(audit_payload["claim_support_replay_alert_corpus_source_references"]) == 4
    assert len(audit_payload["claim_support_replay_alert_corpus_snapshots"]) == 1
    assert len(audit_payload["claim_support_replay_alert_corpus_rows"]) == 3
    assert len(audit_payload["claim_support_replay_alert_promotion_artifacts"]) == 1
    assert len(audit_payload["claim_support_replay_alert_promotion_events"]) == 1
    assert len(audit_payload["claim_support_replay_alert_escalation_events"]) == 3
    assert (
        len(audit_payload["claim_support_replay_alert_snapshot_governance_artifacts"])
        == 1
    )
    assert len(audit_payload["claim_support_replay_alert_snapshot_governance_events"]) == 1
    corpus_integrity = audit_payload["claim_support_replay_alert_corpus_integrity"]
    assert corpus_integrity["complete"] is True
    assert corpus_integrity["row_fixture_hashes_match"] is True
    assert corpus_integrity["snapshot_hashes_match"] is True
    assert corpus_integrity["promotion_artifact_hashes_match"] is True
    assert corpus_integrity["snapshot_artifact_hashes_match"] is True
    assert any(
        value.get("prov:type") == "docling:ClaimSupportReplayAlertFixtureCorpusRow"
        for value in audit_payload["prov"]["entity"].values()
    )
    assert any(
        edge["usedEntity"].startswith(
            "docling:claim_support_replay_alert_corpus_row:"
        )
        for edge in audit_payload["prov"]["wasDerivedFrom"]
    )
    assert audit_payload["source_payload_hashes"]
    receipt_response = postgres_integration_harness.client.post(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts",
        json={"created_by": "integration"},
    )
    assert receipt_response.status_code == 200
    receipt_payload = receipt_response.json()
    assert receipt_payload["validation_status"] == "passed"
    assert receipt_payload["semantic_governance_valid"] is True


def test_materialize_retrieval_learning_dataset_from_claim_feedback_ledger(
    postgres_integration_harness,
) -> None:
    now = datetime.now(UTC)
    verification_task_id = uuid4()

    with postgres_integration_harness.session_factory() as session:
        request = _make_search_request(now=now)
        result = _make_result(request_id=request.id, rank=1, result_type="chunk", now=now)
        span = SearchRequestResultSpan(
            id=uuid4(),
            search_request_id=request.id,
            search_request_result_id=result.id,
            retrieval_evidence_span_id=None,
            span_rank=1,
            score_kind="lexical",
            score=0.93,
            source_type="chunk",
            source_id=result.chunk_id,
            span_index=0,
            page_from=1,
            page_to=1,
            text_excerpt="The cited result does not support the generated claim.",
            content_sha256="claim-feedback-span-sha",
            source_snapshot_sha256="claim-feedback-source-sha",
            metadata_json={"fixture": "technical_report_claim_feedback"},
            created_at=now,
        )
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
            "claim_id": "claim:unsupported",
            "claim_text": "The generated claim overstates the cited evidence.",
            "support_verdict": "unsupported",
            "support_score": 0.12,
            "feedback_status": "rejected",
            "learning_label": "negative",
            "hard_negative_kind": "explicit_irrelevant",
            "source_search_request_ids": [str(request.id)],
            "source_search_request_result_ids": [str(result.id)],
            "search_request_result_span_ids": [str(span.id)],
            "retrieval_evidence_span_ids": [],
        }
        source_payload_sha256 = str(payload_sha256(source_payload))
        feedback_payload = {
            "schema_name": "technical_report_claim_retrieval_feedback",
            "schema_version": "1.0",
            "feedback_kind": "generation_claim_retrieval_feedback",
            "technical_report_verification_task_id": str(verification_task_id),
            "claim_id": "claim:unsupported",
            "feedback_status": "rejected",
            "learning_label": "negative",
            "hard_negative_kind": "explicit_irrelevant",
            "source_payload_sha256": source_payload_sha256,
            "source": source_payload,
        }
        feedback = TechnicalReportClaimRetrievalFeedback(
            id=uuid4(),
            technical_report_verification_task_id=verification_task_id,
            claim_id="claim:unsupported",
            claim_text="The generated claim overstates the cited evidence.",
            support_verdict="unsupported",
            support_score=0.12,
            feedback_status="rejected",
            learning_label="negative",
            hard_negative_kind="explicit_irrelevant",
            source_search_request_id=request.id,
            search_request_result_id=result.id,
            source_search_request_ids_json=[str(request.id)],
            source_search_request_result_ids_json=[str(result.id)],
            search_request_result_span_ids_json=[str(span.id)],
            retrieval_evidence_span_ids_json=[],
            semantic_ontology_snapshot_ids_json=[],
            semantic_graph_snapshot_ids_json=[],
            retrieval_reranker_artifact_ids_json=[],
            search_harness_release_ids_json=[],
            release_audit_bundle_ids_json=[],
            release_validation_receipt_ids_json=[],
            evidence_refs_json=[
                {
                    "search_request_result_span_id": str(span.id),
                    "search_request_id": str(request.id),
                    "search_request_result_id": str(result.id),
                    "span_rank": 1,
                    "score_kind": "lexical",
                    "score": 0.93,
                    "source_type": "chunk",
                    "source_id": str(result.chunk_id),
                    "span_index": 0,
                    "page_from": 1,
                    "page_to": 1,
                    "text_excerpt": span.text_excerpt,
                    "content_sha256": span.content_sha256,
                    "source_snapshot_sha256": span.source_snapshot_sha256,
                    "metadata": span.metadata_json,
                }
            ],
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
        session.add_all([request, result, span, verification_task, feedback])
        session.flush()
        response = materialize_retrieval_learning_dataset(
            session,
            limit=10,
            source_types=["technical_report_claim_feedback"],
            set_name="integration-claim-feedback-learning",
            created_by="integration",
        )
        judgment_set_id = UUID(response["judgment_set_id"])
        request_id = request.id
        result_id = result.id
        session.commit()

    assert response["summary"]["source_types"] == ["technical_report_claim_feedback"]
    assert response["summary"]["judgment_count"] == 1
    assert response["summary"]["negative_count"] == 1
    assert response["summary"]["hard_negative_count"] == 1
    assert response["summary"]["judgment_counts_by_source_type"] == {
        "technical_report_claim_feedback": 1
    }

    with postgres_integration_harness.session_factory() as session:
        judgment = session.scalar(
            select(RetrievalJudgment).where(RetrievalJudgment.judgment_set_id == judgment_set_id)
        )
        hard_negative = session.scalar(
            select(RetrievalHardNegative).where(
                RetrievalHardNegative.judgment_set_id == judgment_set_id
            )
        )
        training_run = session.scalar(
            select(RetrievalTrainingRun).where(
                RetrievalTrainingRun.judgment_set_id == judgment_set_id
            )
        )

    assert judgment is not None
    assert judgment.source_type == "technical_report_claim_feedback"
    assert judgment.judgment_kind == "negative"
    assert judgment.search_request_id == request_id
    assert judgment.search_request_result_id == result_id
    assert judgment.evidence_refs_json
    assert judgment.payload_json["source_details"]["feedback_status"] == "rejected"
    assert hard_negative is not None
    assert hard_negative.source_type == "technical_report_claim_feedback"
    assert hard_negative.hard_negative_kind == "explicit_irrelevant"
    assert hard_negative.search_request_result_id == result_id
    assert training_run is not None
    assert training_run.training_payload_json["judgment_set"]["criteria"][
        "technical_report_claim_feedback"
    ]["feedback_payload_hash_required"] is True


def test_retrieval_training_audit_bundle_flags_tampered_replay_alert_corpus_lineage(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    now = datetime.now(UTC)
    fixtures = [
        _claim_support_learning_fixture(
            case_id="replay-alert-audit-tampered",
            expected_verdict="supported",
            hard_case_kind="policy_change_supported",
            rendered_text="The policy exception is supported by the cited record.",
            evidence_excerpt="The record states the exception is authorized.",
        )
    ]

    with postgres_integration_harness.session_factory() as session:
        snapshot = _seed_governed_claim_support_replay_alert_corpus(
            session,
            now=now,
            fixtures=fixtures,
        )
        response = materialize_retrieval_learning_dataset(
            session,
            limit=10,
            source_types=["claim_support_replay_alert_corpus"],
            set_name="integration-replay-alert-corpus-audit-tamper",
            created_by="integration",
        )
        training_run_id = response["retrieval_training_run_id"]
        row = session.scalar(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot.id)
            .limit(1)
        )
        assert row is not None
        row.fixture_json = {
            **row.fixture_json,
            "description": "tampered after training materialization",
        }
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
    audit_bundle = audit_response.json()
    audit_payload = audit_bundle["bundle"]["payload"]
    assert audit_payload["audit_checklist"]["complete"] is False
    assert (
        audit_payload["audit_checklist"][
            "claim_support_replay_alert_corpus_lineage_complete"
        ]
        is False
    )
    corpus_integrity = audit_payload["claim_support_replay_alert_corpus_integrity"]
    assert corpus_integrity["complete"] is False
    assert corpus_integrity["row_fixture_hashes_match"] is False
    receipt_response = postgres_integration_harness.client.post(
        f"/search/audit-bundles/{audit_bundle['bundle_id']}/validation-receipts",
        json={"created_by": "integration"},
    )
    assert receipt_response.status_code == 200
    receipt_payload = receipt_response.json()
    assert receipt_payload["validation_status"] == "failed"
    assert any(
        error["code"] == "claim_support_replay_alert_corpus_lineage_incomplete"
        for error in receipt_payload["validation_errors"]
    )


def test_release_audit_bundle_refreshes_stale_replay_alert_corpus_training_bundle(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    now = datetime.now(UTC)
    fixture = _claim_support_learning_fixture(
        case_id="replay-alert-release-stale-lineage",
        expected_verdict="supported",
        hard_case_kind="policy_change_supported",
        rendered_text="The policy exception is supported by the cited record.",
        evidence_excerpt="The record states the exception is authorized.",
    )
    monkeypatch.setattr(
        "app.services.audit_bundles.get_settings",
        lambda: SimpleNamespace(
            audit_bundle_signing_key="retrieval-training-secret",
            audit_bundle_signing_key_id="retrieval-training-key",
        ),
    )

    with postgres_integration_harness.session_factory() as session:
        snapshot = _seed_governed_claim_support_replay_alert_corpus(
            session,
            now=now,
            fixtures=[fixture],
        )
        snapshot_id = snapshot.id
        response = materialize_retrieval_learning_dataset(
            session,
            limit=10,
            source_types=["claim_support_replay_alert_corpus"],
            set_name="integration-replay-alert-release-stale-lineage",
            created_by="integration",
        )
        training_run_id = UUID(response["retrieval_training_run_id"])
        evaluation_id = uuid4()
        baseline_replay_run_id = uuid4()
        candidate_replay_run_id = uuid4()
        session.add_all(
            [
                _make_replay_run(
                    replay_run_id=baseline_replay_run_id,
                    harness_name="default_v1",
                    now=now,
                ),
                _make_replay_run(
                    replay_run_id=candidate_replay_run_id,
                    harness_name="candidate_v2",
                    now=now,
                ),
                SearchHarnessEvaluation(
                    id=evaluation_id,
                    status="completed",
                    baseline_harness_name="default_v1",
                    candidate_harness_name="candidate_v2",
                    limit=5,
                    source_types_json=["evaluation_queries"],
                    harness_overrides_json={},
                    total_shared_query_count=1,
                    total_improved_count=1,
                    total_regressed_count=0,
                    total_unchanged_count=0,
                    summary_json={},
                    error_message=None,
                    created_at=now,
                    completed_at=now,
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
                baseline_query_count=1,
                candidate_query_count=1,
                baseline_passed_count=1,
                candidate_passed_count=1,
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
                shared_query_count=1,
                improved_count=1,
                regressed_count=0,
                unchanged_count=0,
                created_at=now,
            )
        )
        session.commit()

    release_response = postgres_integration_harness.client.post(
        "/search/harness-releases",
        json={
            "evaluation_id": str(evaluation_id),
            "max_total_regressed_count": 0,
            "min_total_shared_query_count": 1,
            "requested_by": "integration",
            "review_note": "replay-alert release audit lineage",
        },
    )
    assert release_response.status_code == 200
    release_id = UUID(release_response.json()["release_id"])

    with postgres_integration_harness.session_factory() as session:
        training_run = session.get(RetrievalTrainingRun, training_run_id)
        assert training_run is not None
        training_run.search_harness_evaluation_id = evaluation_id
        training_run.search_harness_release_id = release_id
        candidate_id = uuid4()
        candidate = RetrievalLearningCandidateEvaluation(
            id=candidate_id,
            retrieval_training_run_id=training_run_id,
            judgment_set_id=training_run.judgment_set_id,
            search_harness_evaluation_id=evaluation_id,
            search_harness_release_id=release_id,
            training_dataset_sha256=training_run.training_dataset_sha256,
            training_example_count=training_run.example_count,
            positive_count=training_run.positive_count,
            negative_count=training_run.negative_count,
            missing_count=training_run.missing_count,
            hard_negative_count=training_run.hard_negative_count,
            baseline_harness_name="default_v1",
            candidate_harness_name="candidate_v2",
            source_types_json=["claim_support_replay_alert_corpus"],
            limit=5,
            status="completed",
            gate_outcome="passed",
            thresholds_json={"max_total_regressed_count": 0},
            metrics_json={"total_shared_query_count": 1},
            reasons_json=[],
            evaluation_snapshot_json={"evaluation_id": str(evaluation_id)},
            release_snapshot_json=release_response.json(),
            details_json={"fixture": "replay-alert release lineage"},
            learning_package_sha256="learning-package-sha",
            created_by="integration",
            review_note="replay-alert release audit lineage",
            created_at=now,
            completed_at=now,
        )
        session.add(candidate)
        session.flush()
        event = record_semantic_governance_event(
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
                    "training_dataset_sha256": training_run.training_dataset_sha256,
                    "learning_package_sha256": "learning-package-sha",
                }
            },
            deduplication_key=f"release-audit-learning-candidate:{candidate_id}",
            created_by="integration",
        )
        candidate.semantic_governance_event_id = event.id
        session.commit()

    original_training_audit_response = postgres_integration_harness.client.post(
        f"/search/retrieval-training-runs/{training_run_id}/audit-bundles",
        json={"created_by": "integration"},
    )
    assert original_training_audit_response.status_code == 200
    original_training_audit_bundle = original_training_audit_response.json()
    assert (
        original_training_audit_bundle["bundle"]["payload"][
            "claim_support_replay_alert_corpus_integrity"
        ]["complete"]
        is True
    )
    original_receipt_response = postgres_integration_harness.client.post(
        f"/search/audit-bundles/{original_training_audit_bundle['bundle_id']}"
        "/validation-receipts",
        json={"created_by": "integration"},
    )
    assert original_receipt_response.status_code == 200
    assert original_receipt_response.json()["validation_status"] == "passed"

    with postgres_integration_harness.session_factory() as session:
        row = session.scalar(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot_id)
            .limit(1)
        )
        assert row is not None
        row.fixture_json = {
            **row.fixture_json,
            "description": "tampered after a signed training bundle was created",
        }
        row.fixture_sha256 = payload_sha256(row.fixture_json)
        session.commit()

    release_audit_response = postgres_integration_harness.client.post(
        f"/search/harness-releases/{release_id}/audit-bundles",
        json={"created_by": "integration"},
    )
    assert release_audit_response.status_code == 200
    release_audit_bundle = release_audit_response.json()
    release_payload = release_audit_bundle["bundle"]["payload"]
    assert release_payload["audit_checklist"]["complete"] is False
    assert (
        release_payload["audit_checklist"][
            "training_audit_bundle_corpus_lineage_complete"
        ]
        is False
    )
    assert (
        release_payload["integrity"][
            "training_audit_bundle_corpus_lineage_complete"
        ]
        is False
    )
    training_bundle_ref = release_payload["retrieval_training_audit_bundles"][0]
    assert training_bundle_ref["bundle_id"] != original_training_audit_bundle["bundle_id"]
    assert (
        training_bundle_ref[
            "payload_claim_support_replay_alert_corpus_lineage_complete"
        ]
        is False
    )
    assert (
        training_bundle_ref[
            "payload_claim_support_replay_alert_corpus_source_reference_count"
        ]
        > 0
    )
    match_check = release_payload["integrity"]["training_audit_bundle_match_checks"][0]
    assert match_check["hashes_match_training_run"] is True
    assert match_check["claim_support_replay_alert_corpus_lineage_required"] is True
    assert match_check["claim_support_replay_alert_corpus_lineage_complete"] is False
    assert match_check["claim_support_replay_alert_corpus_lineage_bundle_complete"] is False
    assert match_check["claim_support_replay_alert_corpus_lineage_current_complete"] is False
    assert match_check["claim_support_replay_alert_corpus_source_reference_counts_match"] is True
    assert (
        training_bundle_ref[
            "payload_claim_support_replay_alert_corpus_source_reference_count"
        ]
        == match_check["claim_support_replay_alert_corpus_source_reference_count"]
    )
    training_receipt_ref = release_payload[
        "retrieval_training_audit_bundle_validation_receipts"
    ][0]
    assert training_receipt_ref["validation_status"] == "failed"

    latest_release_receipt_response = postgres_integration_harness.client.get(
        f"/search/audit-bundles/{release_audit_bundle['bundle_id']}"
        "/validation-receipts/latest"
    )
    assert latest_release_receipt_response.status_code == 200
    latest_release_receipt = latest_release_receipt_response.json()
    assert latest_release_receipt["validation_status"] == "failed"
    assert any(
        error["code"] == "training_bundle_corpus_lineage_incomplete"
        for error in latest_release_receipt["validation_errors"]
    )
    readiness_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/readiness"
    )
    assert readiness_response.status_code == 200
    readiness = readiness_response.json()
    assert readiness["ready"] is False
    assert readiness["blockers"] == ["validation_receipts_ready"]
    assert readiness["checks"]["validation_receipts_ready"] is False
    assert len(readiness["blocker_details"]) == 1
    blocker_detail = readiness["blocker_details"][0]
    assert blocker_detail["blocker"] == "validation_receipts_ready"
    assert blocker_detail["reasons"] == [
        "release_validation_receipt_failed",
        "payload_schema_invalid",
    ]
    assert blocker_detail["validation_error_codes"] == [
        "audit_checklist_incomplete",
        "training_bundle_corpus_lineage_incomplete",
    ]
    assert blocker_detail["audit_checklist_failed"] == [
        "training_audit_bundle_corpus_lineage_complete",
        "training_audit_bundle_validation_receipts_complete",
    ]
    assert blocker_detail["lineage_remediation_required"] is True
    assert readiness["validation_receipts"]["release_validation_receipt_passed"] is False
    assert readiness["validation_receipts"]["validation_error_codes"] == [
        "audit_checklist_incomplete",
        "training_bundle_corpus_lineage_incomplete",
    ]
    diagnostics = readiness["diagnostics"]
    assert diagnostics["release_audit_bundle_id"] == release_audit_bundle["bundle_id"]
    assert diagnostics["release_validation_receipt_id"] == latest_release_receipt["receipt_id"]
    assert diagnostics["release_validation_status"] == "failed"
    assert diagnostics["validation_error_codes"] == [
        "audit_checklist_incomplete",
        "training_bundle_corpus_lineage_incomplete",
    ]
    assert "training_audit_bundle_corpus_lineage_complete" in (
        diagnostics["audit_checklist_failed"]
    )
    diagnostic_match_check = diagnostics["training_audit_bundle_match_checks"][0]
    assert diagnostic_match_check["retrieval_training_run_id"] == str(training_run_id)
    assert diagnostic_match_check["claim_support_replay_alert_corpus_lineage_complete"] is False
    remediation = readiness["lineage_remediation"]
    assert remediation["status"] == "action_required"
    assert remediation["action_required"] is True
    assert remediation["affected_training_run_count"] == 1
    remediation_item = remediation["replay_alert_corpus"]["items"][0]
    assert remediation_item["retrieval_training_run_id"] == str(training_run_id)
    assert remediation_item["training_audit_bundle_id"] == training_bundle_ref["bundle_id"]
    assert remediation_item["bundle_lineage_complete"] is False
    assert remediation_item["current_lineage_complete"] is False
    assert remediation_item["source_reference_counts_match"] is True
    assert remediation_item["failure_reasons"] == [
        "training_bundle_lineage_incomplete",
        "current_corpus_lineage_incomplete",
    ]
    assert "recreate the release audit bundle" in (
        remediation_item["suggested_operator_action"]
    )

    assessment_response = postgres_integration_harness.client.post(
        f"/search/harness-releases/{release_id}/readiness-assessments",
        json={"created_by": "integration", "review_note": "freeze blocked readiness"},
    )
    assert assessment_response.status_code == 200
    assessment = assessment_response.json()
    assert assessment["schema_version"] == "1.1"
    assert assessment["readiness_status"] == "blocked"
    assert assessment["ready"] is False
    assert assessment["blockers"] == ["validation_receipts_ready"]
    assert assessment["latest_release_audit_bundle_id"] == (
        release_audit_bundle["bundle_id"]
    )
    assert assessment["latest_release_validation_receipt_id"] == (
        latest_release_receipt["receipt_id"]
    )
    assert assessment["blocker_details"][0]["lineage_remediation_required"] is True
    assert assessment["lineage_remediation"]["status"] == "action_required"
    assert assessment["readiness"]["ready"] is False
    assert assessment["readiness"]["latest_readiness_assessment"] is None
    assert assessment["semantic_governance_event_id"]
    assert assessment["integrity"]["complete"] is True
    assert assessment["integrity"]["readiness_payload_hash_matches"] is True
    assert assessment["integrity"]["assessment_payload_hash_matches"] is True
    assert assessment["integrity"]["assessment_payload_embeds_readiness_hash"] is True
    assert assessment["integrity"]["readiness_status_matches"] is True

    latest_assessment_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/readiness-assessments/latest"
    )
    assert latest_assessment_response.status_code == 200
    assert latest_assessment_response.json()["assessment_id"] == (
        assessment["assessment_id"]
    )
    assert latest_assessment_response.json()["integrity"]["complete"] is True

    readiness_after_assessment_response = postgres_integration_harness.client.get(
        f"/search/harness-releases/{release_id}/readiness"
    )
    assert readiness_after_assessment_response.status_code == 200
    readiness_after_assessment = readiness_after_assessment_response.json()
    assert readiness_after_assessment["latest_readiness_assessment"]["ready"] is False
    assert readiness_after_assessment["latest_readiness_assessment"]["assessment_id"] == (
        assessment["assessment_id"]
    )

    with postgres_integration_harness.session_factory() as session:
        refreshed_training_bundle = session.get(
            AuditBundleExport,
            UUID(training_bundle_ref["bundle_id"]),
        )
        assert refreshed_training_bundle is not None
        refreshed_payload = refreshed_training_bundle.bundle_payload_json["payload"]
        refreshed_integrity = refreshed_payload[
            "claim_support_replay_alert_corpus_integrity"
        ]
        assert refreshed_integrity["complete"] is False
        assert refreshed_integrity["reference_row_identity_hashes_match"] is False
        assert refreshed_integrity["row_fixture_hashes_match"] is True
        assessment_row = session.get(
            SearchHarnessReleaseReadinessAssessment,
            UUID(assessment["assessment_id"]),
        )
        assert assessment_row is not None
        assert assessment_row.ready is False
        assert assessment_row.release_audit_bundle_id == UUID(
            release_audit_bundle["bundle_id"]
        )
        assert assessment_row.release_validation_receipt_id == UUID(
            latest_release_receipt["receipt_id"]
        )
        event = session.get(
            SemanticGovernanceEvent,
            assessment_row.semantic_governance_event_id,
        )
        assert event is not None
        assert event.event_kind == "search_harness_release_readiness_assessed"
        assert event.search_harness_release_id == release_id


def test_materialize_retrieval_learning_dataset_rejects_tampered_replay_alert_corpus(
    postgres_integration_harness,
) -> None:
    now = datetime.now(UTC)
    fixtures = [
        _claim_support_learning_fixture(
            case_id="replay-alert-tampered",
            expected_verdict="supported",
            hard_case_kind="policy_change_supported",
            rendered_text="The policy exception is supported by the cited record.",
            evidence_excerpt="The record states the exception is authorized.",
        )
    ]

    with postgres_integration_harness.session_factory() as session:
        snapshot = _seed_governed_claim_support_replay_alert_corpus(
            session,
            now=now,
            fixtures=fixtures,
        )
        row = session.scalar(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot.id)
            .limit(1)
        )
        assert row is not None
        row.fixture_sha256 = "tampered-fixture-hash"
        session.flush()

        with pytest.raises(ValueError, match="snapshot governance is incomplete"):
            materialize_retrieval_learning_dataset(
                session,
                limit=10,
                source_types=["claim_support_replay_alert_corpus"],
                set_name="tampered-replay-alert-corpus-learning",
                created_by="integration",
            )
        session.rollback()


def test_materialize_retrieval_learning_dataset_rejects_unusable_replay_alert_result(
    postgres_integration_harness,
) -> None:
    now = datetime.now(UTC)
    fixture = _claim_support_learning_fixture(
        case_id="replay-alert-missing-object-id",
        expected_verdict="unsupported",
        hard_case_kind="policy_change_unsupported",
        rendered_text="The policy exception is not supported by the cited record.",
        evidence_excerpt="The cited record discusses a different policy.",
    )
    fixture["draft_payload"]["evidence_cards"][0].pop("chunk_id")
    fixtures = [fixture]

    with postgres_integration_harness.session_factory() as session:
        _seed_governed_claim_support_replay_alert_corpus(
            session,
            now=now,
            fixtures=fixtures,
        )

        with pytest.raises(ValueError, match="evidence_object_id_missing"):
            materialize_retrieval_learning_dataset(
                session,
                limit=10,
                source_types=["claim_support_replay_alert_corpus"],
                set_name="invalid-replay-alert-corpus-result-learning",
                created_by="integration",
            )
        session.rollback()


def test_materialize_retrieval_learning_dataset_rechecks_promotion_artifact_integrity(
    postgres_integration_harness,
) -> None:
    now = datetime.now(UTC)
    fixtures = [
        _claim_support_learning_fixture(
            case_id="replay-alert-artifact-tampered",
            expected_verdict="supported",
            hard_case_kind="policy_change_supported",
            rendered_text="The policy exception is supported by the cited record.",
            evidence_excerpt="The record states the exception is authorized.",
        )
    ]

    with postgres_integration_harness.session_factory() as session:
        snapshot = _seed_governed_claim_support_replay_alert_corpus(
            session,
            now=now,
            fixtures=fixtures,
        )
        row = session.scalar(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot.id)
            .limit(1)
        )
        assert row is not None
        artifact = session.get(AgentTaskArtifact, row.promotion_artifact_id)
        assert artifact is not None
        artifact.payload_json = {
            **artifact.payload_json,
            "candidate_count": 999,
        }
        session.flush()

        with pytest.raises(ValueError, match="promotion_artifact_hash_mismatch"):
            materialize_retrieval_learning_dataset(
                session,
                limit=10,
                source_types=["claim_support_replay_alert_corpus"],
                set_name="tampered-promotion-artifact-learning",
                created_by="integration",
            )
        session.rollback()


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
