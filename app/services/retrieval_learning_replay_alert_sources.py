from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.coercion import maybe_uuid as _maybe_uuid
from app.core.hashes import embedded_payload_hash_matches as _payload_hash_matches_embedded_field
from app.core.hashes import payload_sha256 as _payload_sha256
from app.core.json_utils import canonical_json_value as _json_payload
from app.db.public.agent_tasks import AgentTaskArtifact
from app.db.public.claim_support import (
    ClaimSupportReplayAlertFixtureCorpusRow,
    ClaimSupportReplayAlertFixtureCorpusSnapshot,
)
from app.db.public.retrieval import RetrievalHardNegativeKind, RetrievalJudgmentKind
from app.db.public.semantic_memory import SemanticGovernanceEvent
from app.services.claim_support_replay_alert_fixture_corpus import (
    active_replay_alert_fixture_corpus_rows,
    replay_alert_fixture_corpus_snapshot_governance_integrity,
)
from app.services.query_utils import load_by_ids as _load_by_ids

RETRIEVAL_LEARNING_SOURCE_CLAIM_SUPPORT_REPLAY_ALERT_CORPUS = (
    "claim_support_replay_alert_corpus"
)
CLAIM_SUPPORT_FIXTURE_PROMOTION_ARTIFACT_KIND = (
    "claim_support_policy_impact_fixture_promotion"
)
CLAIM_SUPPORT_FIXTURE_PROMOTION_EVENT_KIND = "claim_support_policy_impact_fixture_promoted"
CLAIM_SUPPORT_REPLAY_ESCALATION_EVENT_KIND = (
    "claim_support_policy_impact_replay_escalated"
)
CLAIM_SUPPORT_EXPECTED_VERDICTS = {
    "supported",
    "unsupported",
    "insufficient_evidence",
}
CLAIM_SUPPORT_RESULT_REQUIRED_VERDICTS = {
    "supported",
    "unsupported",
}


def _claim_support_fixture_claim(fixture: dict[str, Any]) -> dict[str, Any]:
    draft_payload = fixture.get("draft_payload") if isinstance(fixture, dict) else {}
    claims = draft_payload.get("claims") if isinstance(draft_payload, dict) else []
    claim_id = str(fixture.get("claim_id") or "")
    for claim in claims or []:
        if not isinstance(claim, dict):
            continue
        if claim_id and str(claim.get("claim_id") or "") != claim_id:
            continue
        return claim
    for claim in claims or []:
        if isinstance(claim, dict):
            return claim
    return {}


def _claim_support_query_text(
    fixture: dict[str, Any],
    row: ClaimSupportReplayAlertFixtureCorpusRow,
) -> str:
    claim = _claim_support_fixture_claim(fixture)
    return (
        str(claim.get("rendered_text") or "").strip()
        or str(fixture.get("description") or "").strip()
        or str(fixture.get("case_id") or "").strip()
        or str(row.case_id or "").strip()
    )


def _claim_support_evidence_cards(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    draft_payload = fixture.get("draft_payload") if isinstance(fixture, dict) else {}
    if not isinstance(draft_payload, dict):
        return []
    return [card for card in draft_payload.get("evidence_cards") or [] if isinstance(card, dict)]


def _claim_support_evidence_refs(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for card in _claim_support_evidence_cards(fixture):
        result_ids = [str(value) for value in card.get("source_search_request_result_ids") or []]
        request_ids = [str(value) for value in card.get("source_search_request_ids") or []]
        refs.append(
            _json_payload(
                {
                    "source": "claim_support_replay_alert_fixture",
                    "evidence_card_id": card.get("evidence_card_id"),
                    "source_type": card.get("source_type"),
                    "source_locator": card.get("source_locator"),
                    "source_search_request_ids": request_ids,
                    "source_search_request_result_ids": result_ids,
                    "document_id": card.get("document_id"),
                    "run_id": card.get("run_id"),
                    "chunk_id": card.get("chunk_id"),
                    "table_id": card.get("table_id"),
                    "source_id": card.get("source_id"),
                    "page_from": card.get("page_from"),
                    "page_to": card.get("page_to"),
                    "text_excerpt": card.get("excerpt"),
                    "source_snapshot_sha256": card.get("source_snapshot_sha256"),
                    "metadata": card.get("metadata") or {},
                }
            )
        )
    return refs


def _empty_claim_support_result_fields(fixture: dict[str, Any]) -> dict[str, Any]:
    return {
        "result_rank": None,
        "result_type": None,
        "result_id": None,
        "document_id": None,
        "run_id": None,
        "score": None,
        "rerank_features_json": {},
        "evidence_refs_json": _claim_support_evidence_refs(fixture),
    }


def _claim_support_result_fields(
    fixture: dict[str, Any],
    *,
    include_result: bool = True,
) -> dict[str, Any]:
    if not include_result:
        return _empty_claim_support_result_fields(fixture)
    for card in _claim_support_evidence_cards(fixture):
        result_type = str(card.get("source_type") or "").strip()
        if result_type not in {"chunk", "table"}:
            continue
        source_id_key = "chunk_id" if result_type == "chunk" else "table_id"
        result_id = _maybe_uuid(card.get(source_id_key))
        if result_id is None:
            result_id = _maybe_uuid(card.get("source_id"))
        return {
            "result_rank": None,
            "result_type": result_type,
            "result_id": result_id,
            "document_id": _maybe_uuid(card.get("document_id")),
            "run_id": _maybe_uuid(card.get("run_id")),
            "score": None,
            "rerank_features_json": {},
            "evidence_refs_json": _claim_support_evidence_refs(fixture),
        }
    return _empty_claim_support_result_fields(fixture)


def claim_support_expected_judgment(fixture: dict[str, Any]) -> tuple[str, str, str]:
    expected_verdict = str(fixture.get("expected_verdict") or "").strip()
    if expected_verdict == "supported":
        return (
            RetrievalJudgmentKind.POSITIVE.value,
            "claim_support_expected_supported",
            "Claim-support replay-alert fixture expects the claim to be supported.",
        )
    if expected_verdict == "unsupported":
        return (
            RetrievalJudgmentKind.NEGATIVE.value,
            "claim_support_expected_unsupported",
            (
                "Claim-support replay-alert fixture expects the supplied evidence "
                "not to support the claim."
            ),
        )
    if expected_verdict == "insufficient_evidence":
        return (
            RetrievalJudgmentKind.MISSING.value,
            "claim_support_expected_insufficient_evidence",
            "Claim-support replay-alert fixture expects insufficient traceable evidence.",
        )
    raise ValueError(
        "Unsupported claim-support replay-alert fixture expected_verdict: "
        f"{expected_verdict or '<missing>'}."
    )


def _claim_support_corpus_details(
    *,
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot,
    row: ClaimSupportReplayAlertFixtureCorpusRow,
    fixture: dict[str, Any],
    governance_integrity: dict[str, Any],
) -> dict[str, Any]:
    claim = _claim_support_fixture_claim(fixture)
    return _json_payload(
        {
            "source_family": RETRIEVAL_LEARNING_SOURCE_CLAIM_SUPPORT_REPLAY_ALERT_CORPUS,
            "snapshot": {
                "snapshot_id": snapshot.id,
                "snapshot_name": snapshot.snapshot_name,
                "snapshot_sha256": snapshot.snapshot_sha256,
                "semantic_governance_event_id": snapshot.semantic_governance_event_id,
                "governance_artifact_id": snapshot.governance_artifact_id,
                "governance_receipt_sha256": snapshot.governance_receipt_sha256,
                "governance_integrity": governance_integrity,
            },
            "row": {
                "corpus_row_id": row.id,
                "row_index": row.row_index,
                "case_id": row.case_id,
                "case_identity_sha256": row.case_identity_sha256,
                "fixture_sha256": row.fixture_sha256,
                "fixture_set_id": row.fixture_set_id,
                "promotion_event_id": row.promotion_event_id,
                "promotion_artifact_id": row.promotion_artifact_id,
                "promotion_receipt_sha256": row.promotion_receipt_sha256,
                "source_change_impact_ids": list(row.source_change_impact_ids_json or []),
                "source_escalation_event_ids": list(row.source_escalation_event_ids_json or []),
                "replay_alert_source": row.replay_alert_source_json or {},
            },
            "fixture": {
                "case_id": fixture.get("case_id"),
                "claim_id": fixture.get("claim_id"),
                "hard_case_kind": fixture.get("hard_case_kind"),
                "expected_verdict": fixture.get("expected_verdict"),
                "description": fixture.get("description"),
                "claim": claim,
                "evidence_card_count": len(_claim_support_evidence_cards(fixture)),
            },
        }
    )


def _uuid_list_with_failures(
    values: list[Any],
    *,
    row_prefix: str,
    field_name: str,
    failures: list[str],
) -> set[UUID]:
    parsed: set[UUID] = set()
    for value in values or []:
        parsed_value = _maybe_uuid(value)
        if parsed_value is None:
            failures.append(f"{row_prefix}:{field_name}_invalid")
            continue
        parsed.add(parsed_value)
    return parsed


def _claim_support_fixture_lineage_failures(
    *,
    row_prefix: str,
    row: ClaimSupportReplayAlertFixtureCorpusRow,
    fixture: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if not fixture.get("case_id"):
        failures.append(f"{row_prefix}:fixture_case_id_missing")
    expected_verdict = str(fixture.get("expected_verdict") or "").strip()
    if not expected_verdict:
        failures.append(f"{row_prefix}:fixture_expected_verdict_missing")
    elif expected_verdict not in CLAIM_SUPPORT_EXPECTED_VERDICTS:
        failures.append(f"{row_prefix}:fixture_expected_verdict_invalid")
    if not fixture.get("hard_case_kind"):
        failures.append(f"{row_prefix}:fixture_hard_case_kind_missing")
    if not _claim_support_query_text(fixture, row):
        failures.append(f"{row_prefix}:fixture_query_text_missing")
    if _payload_sha256(fixture) != row.fixture_sha256:
        failures.append(f"{row_prefix}:fixture_hash_mismatch")
    if not row.source_change_impact_ids_json:
        failures.append(f"{row_prefix}:source_change_impact_ids_missing")
    if not row.source_escalation_event_ids_json:
        failures.append(f"{row_prefix}:source_escalation_event_ids_missing")
    if not row.replay_alert_source_json:
        failures.append(f"{row_prefix}:replay_alert_source_missing")

    evidence_cards = _claim_support_evidence_cards(fixture)
    if expected_verdict in CLAIM_SUPPORT_RESULT_REQUIRED_VERDICTS:
        result_fields = _claim_support_result_fields(fixture)
        if not evidence_cards:
            failures.append(f"{row_prefix}:evidence_cards_missing")
        if result_fields["result_type"] is None:
            failures.append(f"{row_prefix}:evidence_result_type_missing")
        if result_fields["result_id"] is None:
            failures.append(f"{row_prefix}:evidence_object_id_missing")
    for card_index, card in enumerate(evidence_cards, start=1):
        card_prefix = f"{row_prefix}:evidence_card_{card_index}"
        result_type = str(card.get("source_type") or "").strip()
        if result_type and result_type not in {"chunk", "table"}:
            failures.append(f"{card_prefix}:source_type_invalid")
        for field_name in ("source_search_request_ids", "source_search_request_result_ids"):
            for value in card.get(field_name) or []:
                if _maybe_uuid(value) is None:
                    failures.append(f"{card_prefix}:{field_name}_invalid")
        for field_name in ("document_id", "run_id", "chunk_id", "table_id", "source_id"):
            if card.get(field_name) and _maybe_uuid(card.get(field_name)) is None:
                failures.append(f"{card_prefix}:{field_name}_invalid")
    return failures


def _claim_support_corpus_lineage_failures(
    session: Session,
    *,
    snapshot: ClaimSupportReplayAlertFixtureCorpusSnapshot,
    rows: list[ClaimSupportReplayAlertFixtureCorpusRow],
) -> list[str]:
    failures: list[str] = []
    if int(snapshot.invalid_promotion_event_count or 0):
        failures.append("snapshot_has_invalid_promotion_events")
        for invalid_event in (snapshot.snapshot_payload_json or {}).get(
            "invalid_promotion_events"
        ) or []:
            if not isinstance(invalid_event, dict):
                continue
            event_id = str(invalid_event.get("event_id") or "unknown")
            for failure in invalid_event.get("failures") or []:
                failures.append(f"snapshot_invalid_promotion_event:{event_id}:{failure}")

    promotion_event_ids = {row.promotion_event_id for row in rows if row.promotion_event_id}
    promotion_artifact_ids = {
        row.promotion_artifact_id for row in rows if row.promotion_artifact_id
    }
    escalation_event_ids = set()
    for row in rows:
        row_prefix = f"row_{row.row_index}_{row.case_id}"
        escalation_event_ids.update(
            _uuid_list_with_failures(
                row.source_escalation_event_ids_json,
                row_prefix=row_prefix,
                field_name="source_escalation_event_id",
                failures=failures,
            )
        )
        _uuid_list_with_failures(
            row.source_change_impact_ids_json,
            row_prefix=row_prefix,
            field_name="source_change_impact_id",
            failures=failures,
        )
    promotion_events = _load_by_ids(session, SemanticGovernanceEvent, promotion_event_ids)
    promotion_artifacts = _load_by_ids(session, AgentTaskArtifact, promotion_artifact_ids)
    escalation_events = _load_by_ids(session, SemanticGovernanceEvent, escalation_event_ids)

    for row in rows:
        row_prefix = f"row_{row.row_index}_{row.case_id}"
        fixture = dict(row.fixture_json or {})
        failures.extend(
            _claim_support_fixture_lineage_failures(
                row_prefix=row_prefix,
                row=row,
                fixture=fixture,
            )
        )
        row_change_impact_ids = {
            value
            for value in (_maybe_uuid(raw) for raw in row.source_change_impact_ids_json or [])
            if value is not None
        }

        if row.promotion_event_id is None:
            failures.append(f"{row_prefix}:promotion_event_missing")
        else:
            promotion_event = promotion_events.get(row.promotion_event_id)
            if promotion_event is None:
                failures.append(f"{row_prefix}:promotion_event_not_found")
            elif promotion_event.event_kind != CLAIM_SUPPORT_FIXTURE_PROMOTION_EVENT_KIND:
                failures.append(f"{row_prefix}:promotion_event_kind_mismatch")
            else:
                if (
                    promotion_event.subject_table != "claim_support_fixture_sets"
                    or promotion_event.subject_id != row.fixture_set_id
                ):
                    failures.append(f"{row_prefix}:promotion_event_subject_mismatch")
                if promotion_event.agent_task_artifact_id != row.promotion_artifact_id:
                    failures.append(f"{row_prefix}:promotion_event_artifact_mismatch")
                if not row.promotion_receipt_sha256:
                    failures.append(f"{row_prefix}:promotion_receipt_missing")
                elif promotion_event.receipt_sha256 != row.promotion_receipt_sha256:
                    failures.append(f"{row_prefix}:promotion_event_receipt_mismatch")

        if row.promotion_artifact_id is None:
            failures.append(f"{row_prefix}:promotion_artifact_missing")
        else:
            promotion_artifact = promotion_artifacts.get(row.promotion_artifact_id)
            if promotion_artifact is None:
                failures.append(f"{row_prefix}:promotion_artifact_not_found")
            else:
                if (
                    promotion_artifact.artifact_kind
                    != CLAIM_SUPPORT_FIXTURE_PROMOTION_ARTIFACT_KIND
                ):
                    failures.append(f"{row_prefix}:promotion_artifact_kind_mismatch")
                artifact_payload = dict(promotion_artifact.payload_json or {})
                if not row.promotion_receipt_sha256:
                    failures.append(f"{row_prefix}:promotion_artifact_receipt_missing")
                elif artifact_payload.get("receipt_sha256") != row.promotion_receipt_sha256:
                    failures.append(f"{row_prefix}:promotion_artifact_receipt_mismatch")
                if not _payload_hash_matches_embedded_field(
                    artifact_payload,
                    hash_field="receipt_sha256",
                ):
                    failures.append(f"{row_prefix}:promotion_artifact_hash_mismatch")

        for escalation_event_id in (
            _maybe_uuid(value) for value in row.source_escalation_event_ids_json or []
        ):
            if escalation_event_id is None:
                failures.append(f"{row_prefix}:source_escalation_event_id_invalid")
                continue
            escalation_event = escalation_events.get(escalation_event_id)
            if escalation_event is None:
                failures.append(f"{row_prefix}:source_escalation_event_not_found")
            elif escalation_event.event_kind != CLAIM_SUPPORT_REPLAY_ESCALATION_EVENT_KIND:
                failures.append(f"{row_prefix}:source_escalation_event_kind_mismatch")
            else:
                if escalation_event.subject_table != "claim_support_policy_change_impacts":
                    failures.append(f"{row_prefix}:source_escalation_event_subject_mismatch")
                if (
                    row_change_impact_ids
                    and escalation_event.subject_id not in row_change_impact_ids
                ):
                    failures.append(f"{row_prefix}:source_escalation_event_impact_mismatch")

    return failures


def collect_claim_support_replay_alert_corpus_sources(
    session: Session,
    *,
    judgment_set_id: UUID,
    limit: int,
    created_at: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    snapshot, selected_rows, _available = active_replay_alert_fixture_corpus_rows(
        session,
        limit=limit,
    )
    if snapshot is None:
        return [], []
    all_rows = list(
        session.scalars(
            select(ClaimSupportReplayAlertFixtureCorpusRow)
            .where(ClaimSupportReplayAlertFixtureCorpusRow.snapshot_id == snapshot.id)
            .order_by(
                ClaimSupportReplayAlertFixtureCorpusRow.row_index.asc(),
                ClaimSupportReplayAlertFixtureCorpusRow.id.asc(),
            )
        )
    )
    governance_integrity = replay_alert_fixture_corpus_snapshot_governance_integrity(
        session,
        snapshot,
    )
    if not governance_integrity.get("complete"):
        failures = ", ".join(str(value) for value in governance_integrity.get("failures") or [])
        raise ValueError(
            "Active replay-alert fixture corpus snapshot governance is incomplete"
            f": {failures}"
        )
    lineage_failures = _claim_support_corpus_lineage_failures(
        session,
        snapshot=snapshot,
        rows=all_rows,
    )
    if lineage_failures:
        raise ValueError(
            "Active replay-alert fixture corpus rows are not valid retrieval-learning "
            f"sources: {', '.join(lineage_failures)}"
        )

    judgments: list[dict[str, Any]] = []
    hard_negatives: list[dict[str, Any]] = []
    for corpus_row in selected_rows:
        fixture = dict(corpus_row.fixture_json or {})
        query_text = _claim_support_query_text(fixture, corpus_row)
        judgment_kind, judgment_label, rationale = claim_support_expected_judgment(fixture)
        result_fields = _claim_support_result_fields(
            fixture,
            include_result=judgment_kind != RetrievalJudgmentKind.MISSING.value,
        )
        details = _claim_support_corpus_details(
            snapshot=snapshot,
            row=corpus_row,
            fixture=fixture,
            governance_integrity=governance_integrity,
        )
        row_id = uuid.uuid4()
        judgment = {
            "id": row_id,
            "judgment_set_id": judgment_set_id,
            "judgment_kind": judgment_kind,
            "judgment_label": judgment_label,
            "source_type": RETRIEVAL_LEARNING_SOURCE_CLAIM_SUPPORT_REPLAY_ALERT_CORPUS,
            "source_ref_id": corpus_row.id,
            "search_feedback_id": None,
            "search_replay_query_id": None,
            "search_replay_run_id": None,
            "evaluation_query_id": None,
            "source_search_request_id": None,
            "search_request_id": None,
            "search_request_result_id": None,
            **result_fields,
            "query_text": query_text,
            "mode": "hybrid",
            "filters_json": {},
            "expected_result_type": result_fields["result_type"],
            "expected_top_n": 1 if result_fields["result_type"] else None,
            "harness_name": None,
            "reranker_name": None,
            "reranker_version": None,
            "retrieval_profile_name": None,
            "rationale": rationale,
            "payload_json": {
                "source_details": details,
                "harness_config": {},
            },
            "source_payload_sha256": None,
            "deduplication_key": ":".join(
                [
                    str(judgment_set_id),
                    "judgment",
                    RETRIEVAL_LEARNING_SOURCE_CLAIM_SUPPORT_REPLAY_ALERT_CORPUS,
                    str(corpus_row.id),
                    judgment_kind,
                    judgment_label,
                ]
            ),
            "created_at": created_at,
        }
        judgments.append(judgment)
        if judgment_kind == RetrievalJudgmentKind.NEGATIVE.value:
            hard_negatives.append(
                {
                    "id": uuid.uuid4(),
                    "judgment_set_id": judgment_set_id,
                    "judgment_id": row_id,
                    "positive_judgment_id": None,
                    "hard_negative_kind": RetrievalHardNegativeKind.EXPLICIT_IRRELEVANT.value,
                    "source_type": RETRIEVAL_LEARNING_SOURCE_CLAIM_SUPPORT_REPLAY_ALERT_CORPUS,
                    "source_ref_id": corpus_row.id,
                    "search_feedback_id": None,
                    "search_replay_query_id": None,
                    "search_replay_run_id": None,
                    "evaluation_query_id": None,
                    "source_search_request_id": None,
                    "search_request_id": None,
                    "search_request_result_id": None,
                    "result_rank": result_fields["result_rank"],
                    "result_type": result_fields["result_type"],
                    "result_id": result_fields["result_id"],
                    "document_id": result_fields["document_id"],
                    "run_id": result_fields["run_id"],
                    "score": result_fields["score"],
                    "query_text": query_text,
                    "mode": "hybrid",
                    "filters_json": {},
                    "rerank_features_json": result_fields["rerank_features_json"],
                    "expected_result_type": result_fields["result_type"],
                    "expected_top_n": 1 if result_fields["result_type"] else None,
                    "evidence_refs_json": result_fields["evidence_refs_json"],
                    "reason": (
                        "Claim-support fixture labels this evidence as not supporting the claim."
                    ),
                    "details_json": {"source_details": details, "harness_config": {}},
                    "source_payload_sha256": None,
                    "deduplication_key": ":".join(
                        [
                            str(judgment_set_id),
                            "hard-negative",
                            RETRIEVAL_LEARNING_SOURCE_CLAIM_SUPPORT_REPLAY_ALERT_CORPUS,
                            str(corpus_row.id),
                            RetrievalHardNegativeKind.EXPLICIT_IRRELEVANT.value,
                        ]
                    ),
                    "created_at": created_at,
                }
            )
    return judgments, hard_negatives
