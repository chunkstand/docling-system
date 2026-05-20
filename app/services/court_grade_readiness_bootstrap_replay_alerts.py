from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.hashes import payload_sha256
from app.core.time import utcnow
from app.db.models import (
    AgentTask,
    ClaimSupportFixtureSet,
    SearchRequestRecord,
    SearchRequestResult,
)
from app.services.agent_task_artifacts import create_agent_task_artifact
from app.services.claim_support_replay_alert_fixture_corpus import (
    ensure_active_replay_alert_fixture_corpus_snapshot,
    replay_alert_fixture_corpus_snapshot_summary,
)
from app.services.court_grade_readiness_bootstrap_support import (
    CourtGradeReadinessBootstrapError,
    ReplayAlertFixtureExecution,
    execute_bootstrap_search,
    result_at_rank,
    result_source_id,
)
from app.services.evidence_constants import (
    CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND,
    CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND,
    CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND,
)
from app.services.semantic_governance import (
    active_semantic_basis,
    record_semantic_governance_event,
)
from app.services.storage import StorageService


def _fixture_result_card(
    *,
    case_id: str,
    request: SearchRequestRecord,
    result: SearchRequestResult,
    excerpt: str,
) -> dict[str, Any]:
    result_type = result.result_type
    source_id = result_source_id(result)
    payload: dict[str, Any] = {
        "evidence_card_id": f"card:{case_id}:source",
        "evidence_kind": "source_evidence",
        "source_type": result_type,
        "source_locator": f"{result_type}:{case_id}:source",
        "source_id": str(source_id),
        "document_id": str(result.document_id),
        "run_id": str(result.run_id),
        "page_from": result.page_from,
        "page_to": result.page_to,
        "excerpt": excerpt,
        "source_search_request_ids": [str(request.id)],
        "source_search_request_result_ids": [str(result.id)],
        "metadata": {"fixture": "court_grade_readiness_bootstrap"},
    }
    if result_type == "chunk":
        payload["chunk_id"] = str(result.chunk_id)
    else:
        payload["table_id"] = str(result.table_id)
    return payload


def _build_replay_alert_fixture(
    *,
    seed: dict[str, Any],
    request: SearchRequestRecord,
    result: SearchRequestResult | None,
) -> dict[str, Any]:
    evidence_cards = (
        [
            _fixture_result_card(
                case_id=str(seed["case_id"]),
                request=request,
                result=result,
                excerpt=result.preview_text or str(seed["claim_text"]),
            )
        ]
        if result is not None
        else []
    )
    evidence_card_ids = [card["evidence_card_id"] for card in evidence_cards]
    return {
        "case_id": seed["case_id"],
        "description": seed["description"],
        "hard_case_kind": seed["hard_case_kind"],
        "expected_verdict": seed["expected_verdict"],
        "claim_id": seed["claim_id"],
        "draft_payload": {
            "document_kind": "technical_report",
            "title": "Court-grade readiness replay-alert fixture",
            "goal": "Publish deterministic replay-alert fixtures for readiness coverage.",
            "claims": [
                {
                    "claim_id": seed["claim_id"],
                    "rendered_text": seed["claim_text"],
                    "source_search_request_ids": [str(request.id)],
                    "source_search_request_result_ids": (
                        [str(result.id)] if result is not None else []
                    ),
                    "source_document_ids": (
                        [str(result.document_id)] if result is not None else []
                    ),
                    "evidence_card_ids": evidence_card_ids,
                }
            ],
            "evidence_cards": evidence_cards,
            "markdown": seed["claim_text"],
        },
        "replay_alert_source": {
            "candidate_identity_sha256": str(
                payload_sha256(
                    {
                        "case_id": seed["case_id"],
                        "claim_id": seed["claim_id"],
                        "query_text": request.query_text,
                    }
                )
            ),
            "draft_source": "court_grade_readiness_bootstrap",
        },
    }


def seed_replay_alert_fixture_corpus(
    session: Session,
    *,
    document_id: uuid.UUID,
    seed_rows: list[dict[str, Any]],
    storage_service: StorageService,
) -> dict[str, Any]:
    executions: list[ReplayAlertFixtureExecution] = []
    for seed in seed_rows:
        request, results = execute_bootstrap_search(
            session,
            query_text=str(seed["query"]),
            mode=str(seed.get("mode") or "hybrid"),
            document_id=document_id,
        )
        result = result_at_rank(
            results,
            result_rank=seed.get("result_rank"),
            query_text=str(seed["query"]),
        )
        executions.append(
            ReplayAlertFixtureExecution(
                seed=seed,
                request=request,
                result=result,
            )
        )

    fixtures = [
        _build_replay_alert_fixture(
            seed=execution.seed,
            request=execution.request,
            result=execution.result,
        )
        for execution in executions
    ]

    now = utcnow()
    promotion_task = AgentTask(
        id=uuid.uuid4(),
        task_type="claim_support_replay_alert_fixture_promotion",
        status="completed",
        priority=100,
        side_effect_level="promotable",
        requires_approval=False,
        input_json={"source": "court_grade_readiness_bootstrap"},
        result_json={},
        attempts=1,
        workflow_version="court_grade_readiness_bootstrap_v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    session.add(promotion_task)
    session.flush()

    fixture_set_sha256 = str(
        payload_sha256(
            {
                "schema_name": "claim_support_fixture_set",
                "fixture_set_name": "court_grade_readiness_replay_alert_corpus",
                "fixture_set_version": "v1",
                "fixtures": fixtures,
            }
        )
    )
    fixture_set = ClaimSupportFixtureSet(
        id=uuid.uuid4(),
        fixture_set_name="court_grade_readiness_replay_alert_corpus",
        fixture_set_version="v1",
        status="active",
        fixture_set_sha256=fixture_set_sha256,
        fixture_count=len(fixtures),
        hard_case_kinds_json=sorted({row["hard_case_kind"] for row in fixtures}),
        verdicts_json=sorted({row["expected_verdict"] for row in fixtures}),
        fixtures_json=fixtures,
        metadata_json={"source": "court_grade_readiness_bootstrap"},
        created_at=now,
    )
    session.add(fixture_set)
    session.flush()

    change_impact_ids: list[uuid.UUID] = []
    escalation_event_ids: list[uuid.UUID] = []
    for fixture in fixtures:
        change_impact_id = uuid.uuid4()
        change_impact_ids.append(change_impact_id)
        escalation_event = record_semantic_governance_event(
            session,
            event_kind=CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND,
            governance_scope=f"claim_support_replay_alert:{fixture['case_id']}",
            subject_table="claim_support_policy_change_impacts",
            subject_id=change_impact_id,
            task_id=promotion_task.id,
            event_payload={
                "claim_support_policy_impact_replay_escalation": {
                    "case_id": fixture["case_id"],
                    "change_impact_id": str(change_impact_id),
                }
            },
            deduplication_key=(
                "court-grade-replay-alert-escalation:"
                f"{fixture_set.id}:{fixture['case_id']}"
            ),
            created_by="court_grade_bootstrap",
        )
        escalation_event_ids.append(escalation_event.id)

    candidates = [
        {
            "candidate_id": fixture["replay_alert_source"]["candidate_identity_sha256"],
            "candidate_identity_sha256": fixture["replay_alert_source"][
                "candidate_identity_sha256"
            ],
            "case_id": fixture["case_id"],
            "fixture_sha256": str(payload_sha256(fixture)),
            "change_impact_id": str(change_impact_id),
            "source_payload_sha256": str(payload_sha256(fixture["draft_payload"])),
            "escalation_event_ids": [str(escalation_event_id)],
            "latest_escalation_event_id": str(escalation_event_id),
            "hard_case_kind": fixture["hard_case_kind"],
            "expected_verdict": fixture["expected_verdict"],
        }
        for fixture, change_impact_id, escalation_event_id in zip(
            fixtures,
            change_impact_ids,
            escalation_event_ids,
            strict=True,
        )
    ]
    semantic_basis = active_semantic_basis(session)
    receipt_basis = {
        "schema_name": "claim_support_policy_impact_fixture_promotion_receipt",
        "schema_version": "1.0",
        "fixture_set_id": str(fixture_set.id),
        "fixture_set_name": fixture_set.fixture_set_name,
        "fixture_set_version": fixture_set.fixture_set_version,
        "fixture_set_sha256": fixture_set.fixture_set_sha256,
        "fixture_count": fixture_set.fixture_count,
        "candidate_count": len(candidates),
        "source_change_impact_ids": [str(value) for value in change_impact_ids],
        "source_escalation_event_ids": [str(value) for value in escalation_event_ids],
        "candidates": candidates,
        "semantic_basis": semantic_basis,
        "recorded_by": "court_grade_bootstrap",
        "recorded_at": utcnow().isoformat(),
        "deduplication_key": (
            f"court-grade-replay-alert-promotion:{fixture_set.id}:{fixture_set_sha256}"
        ),
    }
    receipt_payload = {
        **receipt_basis,
        "receipt_sha256": str(payload_sha256(receipt_basis)),
    }
    promotion_artifact = create_agent_task_artifact(
        session,
        task_id=promotion_task.id,
        artifact_kind=CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND,
        payload=receipt_payload,
        storage_service=storage_service,
        filename=(
            "claim_support_policy_impact_fixture_promotion_"
            f"{fixture_set.id}_{receipt_payload['receipt_sha256'][:12]}.json"
        ),
    )
    record_semantic_governance_event(
        session,
        event_kind=CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND,
        governance_scope=(
            f"claim_support_policy:{fixture_set.fixture_set_name}:"
            f"{fixture_set.fixture_set_version}"
        ),
        subject_table="claim_support_fixture_sets",
        subject_id=fixture_set.id,
        task_id=promotion_task.id,
        agent_task_artifact_id=promotion_artifact.id,
        receipt_sha256=receipt_payload["receipt_sha256"],
        event_payload={
            "claim_support_policy_impact_fixture_promotion": receipt_payload,
            "semantic_basis": semantic_basis,
        },
        deduplication_key=(
            "court-grade-replay-alert-promotion:"
            f"{fixture_set.id}:{receipt_payload['receipt_sha256']}"
        ),
        created_by="court_grade_bootstrap",
    )
    snapshot = ensure_active_replay_alert_fixture_corpus_snapshot(
        session,
        storage_service=storage_service,
        recorded_by="court_grade_bootstrap",
    )
    if snapshot is None:
        raise CourtGradeReadinessBootstrapError(
            "Court-grade bootstrap failed to publish an active replay-alert "
            "fixture corpus snapshot."
        )
    session.flush()
    return {
        "fixture_set_id": str(fixture_set.id),
        "fixture_count": len(fixtures),
        "active_snapshot": replay_alert_fixture_corpus_snapshot_summary(
            snapshot,
            session=session,
        ),
    }
