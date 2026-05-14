from __future__ import annotations

from datetime import UTC, datetime  # noqa: F401
from types import SimpleNamespace  # noqa: F401
from uuid import UUID, uuid4  # noqa: F401

from sqlalchemy import select  # noqa: F401

from app.db.models import (  # noqa: F401
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
from app.schemas.search import (  # noqa: F401
    RetrievalLearningCandidateEvaluationRequest,
    RetrievalRerankerArtifactRequest,
    SearchHarnessEvaluationResponse,
    SearchHarnessReleaseResponse,
    SearchReplayRunRequest,
)
from app.services.claim_support_replay_alert_fixture_corpus import (
    ensure_active_replay_alert_fixture_corpus_snapshot,
)
from app.services.evidence import payload_sha256
from app.services.retrieval_learning import (  # noqa: F401
    create_retrieval_reranker_artifact,
    evaluate_retrieval_learning_candidate,
    materialize_retrieval_learning_dataset,
)
from app.services.search_replays import run_search_replay_suite  # noqa: F401
from app.services.semantic_governance import record_semantic_governance_event


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
                f"test-replay-alert-escalation:{fixture_set_id}:{fixture['case_id']}"
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
