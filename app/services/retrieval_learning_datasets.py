from __future__ import annotations

import uuid
from collections import Counter
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.hashes import payload_sha256 as _payload_sha256
from app.core.json_utils import canonical_json_value as _json_payload
from app.core.time import utcnow
from app.db.models import (
    RetrievalHardNegative,
    RetrievalJudgment,
    RetrievalJudgmentKind,
    RetrievalJudgmentSet,
    RetrievalTrainingRun,
    RetrievalTrainingRunStatus,
    SemanticGovernanceEventKind,
)
from app.services import retrieval_learning_dataset_rows as _rows
from app.services import retrieval_learning_dataset_sources as _sources
from app.services import retrieval_learning_replay_alert_sources as _replay_alert_sources
from app.services.semantic_governance import record_semantic_governance_event

RETRIEVAL_LEARNING_DATASET_SCHEMA = "retrieval_learning_dataset"
RETRIEVAL_LEARNING_DATASET_SCHEMA_VERSION = "1.0"
RETRIEVAL_LEARNING_SOURCE_FEEDBACK = "feedback"
RETRIEVAL_LEARNING_SOURCE_REPLAY = "replay"
RETRIEVAL_LEARNING_SOURCE_CLAIM_SUPPORT_REPLAY_ALERT_CORPUS = (
    "claim_support_replay_alert_corpus"
)
RETRIEVAL_LEARNING_SOURCE_TECHNICAL_REPORT_CLAIM_FEEDBACK = (
    "technical_report_claim_feedback"
)
RETRIEVAL_LEARNING_SOURCES = {
    RETRIEVAL_LEARNING_SOURCE_FEEDBACK,
    RETRIEVAL_LEARNING_SOURCE_REPLAY,
    RETRIEVAL_LEARNING_SOURCE_CLAIM_SUPPORT_REPLAY_ALERT_CORPUS,
    RETRIEVAL_LEARNING_SOURCE_TECHNICAL_REPORT_CLAIM_FEEDBACK,
}

collect_feedback_sources = _sources.collect_feedback_sources
collect_replay_sources = _sources.collect_replay_sources
collect_technical_report_claim_feedback_sources = (
    _sources.collect_technical_report_claim_feedback_sources
)
collect_claim_support_replay_alert_corpus_sources = (
    _replay_alert_sources.collect_claim_support_replay_alert_corpus_sources
)


def normalize_retrieval_learning_source_types(
    source_types: list[str] | tuple[str, ...] | None,
) -> list[str]:
    if source_types is None:
        return ["feedback", "replay"]
    normalized: list[str] = []
    for source_type in source_types:
        if source_type not in RETRIEVAL_LEARNING_SOURCES:
            raise ValueError(f"Unsupported retrieval learning source_type: {source_type}.")
        if source_type not in normalized:
            normalized.append(source_type)
    if not normalized:
        raise ValueError("At least one retrieval learning source_type is required.")
    return normalized


def _set_kind(source_types: list[str]) -> str:
    if len(source_types) == 1:
        return source_types[0]
    return "mixed"


def _summary(
    *,
    source_types: list[str],
    limit: int,
    judgments: list[dict[str, Any]],
    hard_negatives: list[dict[str, Any]],
) -> dict[str, Any]:
    judgment_counts = Counter(row["judgment_kind"] for row in judgments)
    hard_negative_counts = Counter(row["hard_negative_kind"] for row in hard_negatives)
    source_counts = Counter(row["source_type"] for row in judgments)
    return {
        "schema_name": RETRIEVAL_LEARNING_DATASET_SCHEMA,
        "schema_version": RETRIEVAL_LEARNING_DATASET_SCHEMA_VERSION,
        "source_types": source_types,
        "source_limit": limit,
        "judgment_count": len(judgments),
        "positive_count": judgment_counts[RetrievalJudgmentKind.POSITIVE.value],
        "negative_count": judgment_counts[RetrievalJudgmentKind.NEGATIVE.value],
        "missing_count": judgment_counts[RetrievalJudgmentKind.MISSING.value],
        "hard_negative_count": len(hard_negatives),
        "judgment_counts_by_source_type": dict(sorted(source_counts.items())),
        "hard_negative_counts_by_kind": dict(sorted(hard_negative_counts.items())),
    }


def _criteria() -> dict[str, Any]:
    return {
        "feedback": {
            "positive_feedback_types": ["relevant"],
            "negative_feedback_types": ["irrelevant"],
            "missing_feedback_types": ["missing_table", "missing_chunk", "no_answer"],
        },
        "replay": {
            "passed_queries": "positive_or_expected_no_answer",
            "failed_queries": "missing_or_top_result_hard_negative",
        },
        RETRIEVAL_LEARNING_SOURCE_CLAIM_SUPPORT_REPLAY_ALERT_CORPUS: {
            "active_snapshot_required": True,
            "snapshot_governance_required": True,
            "row_lineage_required": [
                "fixture_expected_verdict",
                "fixture_hard_case_kind",
                "fixture_sha256",
                "promotion_event",
                "promotion_artifact",
                "source_change_impact_ids",
                "source_escalation_events",
            ],
            "supported_verdict": "positive_judgment",
            "unsupported_verdict": (
                "negative_judgment_with_explicit_irrelevant_hard_negative"
            ),
            "insufficient_evidence_verdict": "missing_judgment",
        },
        RETRIEVAL_LEARNING_SOURCE_TECHNICAL_REPORT_CLAIM_FEEDBACK: {
            "ledger_table": "technical_report_claim_retrieval_feedback",
            "feedback_payload_hash_required": True,
            "source_payload_hash_required": True,
            "claim_supported_label": "positive_judgment",
            "claim_rejected_or_contradicted_label": (
                "negative_judgment_with_explicit_irrelevant_hard_negative"
            ),
            "claim_missing_label": "missing_judgment",
        },
    }


def materialize_retrieval_learning_dataset(
    session: Session,
    *,
    limit: int = 200,
    source_types: list[str] | tuple[str, ...] | None = None,
    set_name: str | None = None,
    created_by: str | None = None,
    search_harness_evaluation_id: UUID | None = None,
    search_harness_release_id: UUID | None = None,
) -> dict[str, Any]:
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    normalized_source_types = normalize_retrieval_learning_source_types(source_types)
    created_at = utcnow()
    judgment_set_id = uuid.uuid4()
    training_run_id = uuid.uuid4()
    effective_set_name = (
        set_name
        or f"retrieval-learning-{created_at.strftime('%Y%m%dT%H%M%SZ')}-{judgment_set_id.hex[:8]}"
    )

    judgments: list[dict[str, Any]] = []
    hard_negatives: list[dict[str, Any]] = []
    if RETRIEVAL_LEARNING_SOURCE_FEEDBACK in normalized_source_types:
        rows, negatives = collect_feedback_sources(
            session,
            judgment_set_id=judgment_set_id,
            limit=limit,
            created_at=created_at,
        )
        judgments.extend(rows)
        hard_negatives.extend(negatives)
    if RETRIEVAL_LEARNING_SOURCE_REPLAY in normalized_source_types:
        rows, negatives = collect_replay_sources(
            session,
            judgment_set_id=judgment_set_id,
            limit=limit,
            created_at=created_at,
        )
        judgments.extend(rows)
        hard_negatives.extend(negatives)
    if RETRIEVAL_LEARNING_SOURCE_CLAIM_SUPPORT_REPLAY_ALERT_CORPUS in normalized_source_types:
        rows, negatives = collect_claim_support_replay_alert_corpus_sources(
            session,
            judgment_set_id=judgment_set_id,
            limit=limit,
            created_at=created_at,
        )
        judgments.extend(rows)
        hard_negatives.extend(negatives)
    if RETRIEVAL_LEARNING_SOURCE_TECHNICAL_REPORT_CLAIM_FEEDBACK in normalized_source_types:
        rows, negatives = collect_technical_report_claim_feedback_sources(
            session,
            judgment_set_id=judgment_set_id,
            limit=limit,
            created_at=created_at,
        )
        judgments.extend(rows)
        hard_negatives.extend(negatives)

    judgments.sort(key=lambda row: row["deduplication_key"])
    hard_negatives.sort(key=lambda row: row["deduplication_key"])
    _rows.finalize_judgment_source_hashes(judgments)
    _rows.pair_hard_negatives_with_positive_judgments(judgments, hard_negatives)
    _rows.finalize_hard_negative_source_hashes(hard_negatives)
    summary = _summary(
        source_types=normalized_source_types,
        limit=limit,
        judgments=judgments,
        hard_negatives=hard_negatives,
    )
    summary = {
        **summary,
        "training_example_count": summary["judgment_count"] + summary["hard_negative_count"],
    }
    criteria = _criteria()
    training_payload = _json_payload(
        {
            "schema_name": RETRIEVAL_LEARNING_DATASET_SCHEMA,
            "schema_version": RETRIEVAL_LEARNING_DATASET_SCHEMA_VERSION,
            "judgment_set": {
                "judgment_set_id": judgment_set_id,
                "set_name": effective_set_name,
                "set_kind": _set_kind(normalized_source_types),
                "source_types": normalized_source_types,
                "source_limit": limit,
                "criteria": criteria,
            },
            "summary": summary,
            "judgments": [_rows.judgment_payload(row) for row in judgments],
            "hard_negatives": [_rows.hard_negative_payload(row) for row in hard_negatives],
        }
    )
    dataset_sha256 = _payload_sha256(training_payload)
    summary = {**summary, "training_dataset_sha256": dataset_sha256}

    judgment_set = RetrievalJudgmentSet(
        id=judgment_set_id,
        set_name=effective_set_name,
        set_kind=_set_kind(normalized_source_types),
        source_types_json=normalized_source_types,
        source_limit=limit,
        criteria_json=criteria,
        summary_json=summary,
        judgment_count=summary["judgment_count"],
        positive_count=summary["positive_count"],
        negative_count=summary["negative_count"],
        missing_count=summary["missing_count"],
        hard_negative_count=summary["hard_negative_count"],
        payload_sha256=dataset_sha256,
        created_by=created_by,
        created_at=created_at,
    )
    session.add(judgment_set)
    session.flush()
    session.add_all(RetrievalJudgment(**row) for row in judgments)
    session.flush()
    session.add_all(RetrievalHardNegative(**row) for row in hard_negatives)

    training_run = RetrievalTrainingRun(
        id=training_run_id,
        judgment_set_id=judgment_set_id,
        run_kind="materialized_training_dataset",
        status=RetrievalTrainingRunStatus.COMPLETED.value,
        search_harness_evaluation_id=search_harness_evaluation_id,
        search_harness_release_id=search_harness_release_id,
        training_dataset_sha256=dataset_sha256,
        training_payload_json=training_payload,
        summary_json=summary,
        example_count=summary["training_example_count"],
        positive_count=summary["positive_count"],
        negative_count=summary["negative_count"],
        missing_count=summary["missing_count"],
        hard_negative_count=summary["hard_negative_count"],
        created_by=created_by,
        created_at=created_at,
        completed_at=created_at,
    )
    session.add(training_run)
    session.flush()

    governance_scope = (
        f"search_harness_release:{search_harness_release_id}"
        if search_harness_release_id is not None
        else f"retrieval_learning:{judgment_set_id}"
    )
    governance_event = record_semantic_governance_event(
        session,
        event_kind=SemanticGovernanceEventKind.RETRIEVAL_TRAINING_RUN_MATERIALIZED.value,
        governance_scope=governance_scope,
        subject_table="retrieval_training_runs",
        subject_id=training_run_id,
        search_harness_evaluation_id=search_harness_evaluation_id,
        search_harness_release_id=search_harness_release_id,
        event_payload={
            "retrieval_training_run": {
                "retrieval_training_run_id": str(training_run_id),
                "judgment_set_id": str(judgment_set_id),
                "set_name": effective_set_name,
                "source_types": normalized_source_types,
                "source_limit": limit,
                "training_dataset_sha256": dataset_sha256,
                "summary": summary,
            }
        },
        deduplication_key=(
            f"retrieval_training_run_materialized:{training_run_id}:{dataset_sha256}"
        ),
        created_by=created_by,
    )
    training_run.semantic_governance_event_id = governance_event.id
    session.flush()

    return {
        "retrieval_training_run_id": str(training_run_id),
        "judgment_set_id": str(judgment_set_id),
        "semantic_governance_event_id": str(governance_event.id),
        "training_dataset_sha256": dataset_sha256,
        "set_name": effective_set_name,
        "source_types": normalized_source_types,
        "source_limit": limit,
        "summary": summary,
    }
