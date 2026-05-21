from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.hashes import payload_sha256
from app.core.time import utcnow
from app.db.public.audit_and_evidence import (
    TechnicalReportClaimRetrievalFeedback,
    TechnicalReportReleaseReadinessDbGate,
)
from app.db.public.claim_support import (
    ClaimSupportFixtureSet,
    ClaimSupportReplayAlertFixtureCorpusSnapshot,
)
from app.db.public.ingest import Document
from app.db.public.retrieval import (
    RetrievalJudgmentSet,
    RetrievalTrainingRun,
    SearchFeedback,
    SearchHarnessEvaluation,
    SearchHarnessEvaluationSource,
    SearchReplayRun,
    SearchRequestRecord,
    SearchRequestResult,
    SearchRequestResultSpan,
)
from app.schemas.search import SearchRequest
from app.services.evaluation_data_readiness import build_evaluation_data_readiness_report
from app.services.readiness_bootstrap_support import (
    count_model_rows,
    load_bootstrap_yaml_mapping,
    resolve_existing_bootstrap_path,
    resolve_readiness_output_path,
)
from app.services.search import execute_search

READINESS_REPORT_FILENAME = "evaluation_data_readiness.latest.json"
DEFAULT_MANUAL_CORPUS_PATH = Path("docs/evaluation_corpus.yaml")
DEFAULT_AUTO_CORPUS_PATH = Path("storage/evaluation_corpus.auto.yaml")
DEFAULT_OPERATOR_FEEDBACK_SEED_PATH = Path(
    "docs/evaluation_bootstrap/court_grade_operator_feedback.yaml"
)
DEFAULT_CLAIM_FEEDBACK_SEED_PATH = Path(
    "docs/evaluation_bootstrap/court_grade_claim_feedback.yaml"
)
DEFAULT_REPLAY_ALERT_FIXTURE_SEED_PATH = Path(
    "docs/evaluation_bootstrap/court_grade_replay_alert_fixtures.yaml"
)
DEFAULT_REPLAY_LIMIT = 25
DEFAULT_RETRIEVAL_LEARNING_LIMIT = 50
DEFAULT_HARNESS_NAME = "default_v1"
EXPECTED_BASELINE_BLOCKERS = (
    "operator_feedback_coverage",
    "technical_report_claim_feedback_ledger",
    "claim_support_replay_alert_corpus",
    "all_replay_source_coverage",
    "harness_evaluation_source_coverage",
    "retrieval_learning_materialized",
)


class CourtGradeReadinessBootstrapError(RuntimeError):
    pass


@dataclass(frozen=True)
class ClaimFeedbackExecution:
    seed: dict[str, Any]
    request: SearchRequestRecord
    result: SearchRequestResult | None
    span: SearchRequestResultSpan | None


@dataclass(frozen=True)
class ReplayAlertFixtureExecution:
    seed: dict[str, Any]
    request: SearchRequestRecord
    result: SearchRequestResult | None


def _advanced_state_counts(session: Session) -> dict[str, int]:
    return {
        "search_feedback_rows": count_model_rows(session, SearchFeedback),
        "claim_feedback_rows": count_model_rows(
            session,
            TechnicalReportClaimRetrievalFeedback,
        ),
        "release_readiness_db_gates": count_model_rows(
            session,
            TechnicalReportReleaseReadinessDbGate,
        ),
        "replay_alert_fixture_sets": count_model_rows(session, ClaimSupportFixtureSet),
        "active_replay_alert_snapshots": count_model_rows(
            session,
            ClaimSupportReplayAlertFixtureCorpusSnapshot,
            ClaimSupportReplayAlertFixtureCorpusSnapshot.status == "active",
        ),
        "feedback_replay_runs": count_model_rows(
            session,
            SearchReplayRun,
            SearchReplayRun.source_type == "feedback",
        ),
        "claim_feedback_replay_runs": count_model_rows(
            session,
            SearchReplayRun,
            SearchReplayRun.source_type == "technical_report_claim_feedback",
        ),
        "harness_evaluations": count_model_rows(session, SearchHarnessEvaluation),
        "harness_feedback_sources": count_model_rows(
            session,
            SearchHarnessEvaluationSource,
            SearchHarnessEvaluationSource.source_type == "feedback",
        ),
        "harness_claim_feedback_sources": count_model_rows(
            session,
            SearchHarnessEvaluationSource,
            SearchHarnessEvaluationSource.source_type == "technical_report_claim_feedback",
        ),
        "retrieval_judgment_sets": count_model_rows(session, RetrievalJudgmentSet),
        "retrieval_training_runs": count_model_rows(session, RetrievalTrainingRun),
    }


def assert_regression_baseline_state(
    session: Session,
    *,
    manual_corpus_path: Path,
    auto_corpus_path: Path,
) -> dict[str, Any]:
    readiness = build_evaluation_data_readiness_report(
        session,
        manual_corpus_path=manual_corpus_path,
        auto_corpus_path=auto_corpus_path,
    )
    summary = dict(readiness.get("summary") or {})
    blockers = tuple(summary.get("court_grade_blockers") or [])
    if summary.get("regression_ready") is not True:
        raise CourtGradeReadinessBootstrapError(
            "Court-grade bootstrap requires a regression-ready baseline."
        )
    if summary.get("court_grade_ready") is True:
        raise CourtGradeReadinessBootstrapError(
            "Court-grade bootstrap refuses to rerun on an already court-grade-ready DB."
        )
    if summary.get("regression_blockers"):
        raise CourtGradeReadinessBootstrapError(
            "Court-grade bootstrap requires an empty regression blocker set."
        )
    if set(blockers) != set(EXPECTED_BASELINE_BLOCKERS):
        raise CourtGradeReadinessBootstrapError(
            "Court-grade bootstrap expected the current six blocker keys but found "
            f"{sorted(blockers)}."
        )
    advanced_counts = _advanced_state_counts(session)
    occupied = {key: value for key, value in advanced_counts.items() if value}
    if occupied:
        raise CourtGradeReadinessBootstrapError(
            "Court-grade bootstrap requires the documented regression-only baseline. "
            f"Advanced readiness rows already exist: {occupied}"
        )
    return readiness


def active_bootstrap_document(
    session: Session,
    *,
    expected_source_filename: str,
) -> Document:
    rows = list(
        session.scalars(
            select(Document)
            .where(Document.active_run_id.is_not(None))
            .order_by(Document.updated_at.desc(), Document.created_at.desc())
        )
    )
    if len(rows) != 1:
        raise CourtGradeReadinessBootstrapError(
            "Court-grade bootstrap requires exactly one active document from the "
            f"regression baseline. Found {len(rows)} active documents."
        )
    document = rows[0]
    if document.source_filename != expected_source_filename:
        raise CourtGradeReadinessBootstrapError(
            "Court-grade bootstrap expected the regression baseline source "
            f"{expected_source_filename!r} but found {document.source_filename!r}."
        )
    return document


def _render_template(value: str | None, *, index: int) -> str | None:
    if value is None:
        return None
    return value.format(index=index)


def expand_operator_feedback_seed(seed: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in seed.get("groups") or []:
        count = int(group.get("count") or 0)
        if count <= 0:
            continue
        for index in range(1, count + 1):
            rows.append(
                {
                    "feedback_type": str(group["feedback_type"]),
                    "query_text": _render_template(group.get("query_template"), index=index)
                    or str(group.get("query") or ""),
                    "mode": str(group.get("mode") or "hybrid"),
                    "result_rank": group.get("result_rank"),
                    "note": _render_template(group.get("note_template"), index=index)
                    or group.get("note"),
                }
            )
    return rows


def expand_claim_feedback_seed(seed: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in seed.get("groups") or []:
        count = int(group.get("count") or 0)
        if count <= 0:
            continue
        prefix = str(group.get("claim_id_prefix") or "claim")
        for index in range(1, count + 1):
            rows.append(
                {
                    "claim_id": f"bootstrap:{prefix}:{index:02d}",
                    "claim_text": _render_template(
                        group.get("claim_text_template"),
                        index=index,
                    )
                    or str(group.get("claim_text") or ""),
                    "query_text": _render_template(group.get("query_template"), index=index)
                    or str(group.get("query") or ""),
                    "mode": str(group.get("mode") or "hybrid"),
                    "result_rank": group.get("result_rank"),
                    "support_verdict": str(group.get("support_verdict") or ""),
                    "support_score": group.get("support_score"),
                    "feedback_status": str(group.get("feedback_status") or ""),
                    "learning_label": str(group.get("learning_label") or ""),
                    "hard_negative_kind": group.get("hard_negative_kind"),
                }
            )
    return rows


def load_replay_alert_fixture_seed_rows(seed: dict[str, Any]) -> list[dict[str, Any]]:
    rows = seed.get("fixtures") or []
    if not isinstance(rows, list):
        raise CourtGradeReadinessBootstrapError("Replay-alert fixture seed must define a list.")
    return [dict(row) for row in rows if isinstance(row, dict)]


def execute_bootstrap_search(
    session: Session,
    *,
    query_text: str,
    mode: str,
    document_id: uuid.UUID,
    limit: int = 10,
) -> tuple[SearchRequestRecord, list[SearchRequestResult]]:
    execution = execute_search(
        session,
        SearchRequest.model_validate(
            {
                "query": query_text,
                "mode": mode,
                "limit": limit,
                "filters": {"document_id": str(document_id)},
            }
        ),
        origin="court_grade_bootstrap",
    )
    if execution.request_id is None:
        raise CourtGradeReadinessBootstrapError(
            f"Bootstrap search for {query_text!r} did not persist a search request."
        )
    session.flush()
    request = session.get(SearchRequestRecord, execution.request_id)
    if request is None:
        raise CourtGradeReadinessBootstrapError(
            f"Bootstrap search request disappeared: {execution.request_id}"
        )
    results = list(
        session.scalars(
            select(SearchRequestResult)
            .where(SearchRequestResult.search_request_id == request.id)
            .order_by(SearchRequestResult.rank.asc())
        )
    )
    return request, results


def result_at_rank(
    results: list[SearchRequestResult],
    *,
    result_rank: int | None,
    query_text: str,
) -> SearchRequestResult | None:
    if result_rank is None:
        return None
    for row in results:
        if row.rank == int(result_rank):
            return row
    raise CourtGradeReadinessBootstrapError(
        f"Bootstrap query {query_text!r} did not return rank {result_rank}."
    )


def result_source_id(result: SearchRequestResult) -> uuid.UUID:
    source_id = result.chunk_id if result.result_type == "chunk" else result.table_id
    if source_id is None:
        raise CourtGradeReadinessBootstrapError(
            f"Bootstrap result {result.id} is missing its typed source identifier."
        )
    return source_id


def ensure_bootstrap_result_span(
    session: Session,
    *,
    request: SearchRequestRecord,
    result: SearchRequestResult,
) -> SearchRequestResultSpan:
    existing = session.scalar(
        select(SearchRequestResultSpan)
        .where(SearchRequestResultSpan.search_request_result_id == result.id)
        .order_by(SearchRequestResultSpan.span_rank.asc())
        .limit(1)
    )
    if existing is not None:
        return existing
    row = SearchRequestResultSpan(
        id=uuid.uuid4(),
        search_request_id=request.id,
        search_request_result_id=result.id,
        retrieval_evidence_span_id=None,
        span_rank=1,
        score_kind="bootstrap",
        score=result.score,
        source_type=result.result_type,
        source_id=result_source_id(result),
        span_index=0,
        page_from=result.page_from,
        page_to=result.page_to,
        text_excerpt=result.preview_text or result.label or request.query_text,
        content_sha256=str(
            payload_sha256(
                {
                    "search_request_result_id": str(result.id),
                    "preview_text": result.preview_text,
                    "label": result.label,
                }
            )
        ),
        source_snapshot_sha256=str(
            payload_sha256(
                {
                    "document_id": str(result.document_id),
                    "run_id": str(result.run_id),
                    "result_type": result.result_type,
                }
            )
        ),
        metadata_json={"source": "court_grade_readiness_bootstrap"},
        created_at=utcnow(),
    )
    session.add(row)
    session.flush()
    return row


__all__ = [
    "ClaimFeedbackExecution",
    "CourtGradeReadinessBootstrapError",
    "DEFAULT_AUTO_CORPUS_PATH",
    "DEFAULT_CLAIM_FEEDBACK_SEED_PATH",
    "DEFAULT_HARNESS_NAME",
    "DEFAULT_MANUAL_CORPUS_PATH",
    "DEFAULT_OPERATOR_FEEDBACK_SEED_PATH",
    "DEFAULT_REPLAY_ALERT_FIXTURE_SEED_PATH",
    "DEFAULT_REPLAY_LIMIT",
    "DEFAULT_RETRIEVAL_LEARNING_LIMIT",
    "READINESS_REPORT_FILENAME",
    "ReplayAlertFixtureExecution",
    "active_bootstrap_document",
    "assert_regression_baseline_state",
    "ensure_bootstrap_result_span",
    "execute_bootstrap_search",
    "expand_claim_feedback_seed",
    "expand_operator_feedback_seed",
    "load_bootstrap_yaml_mapping",
    "load_replay_alert_fixture_seed_rows",
    "resolve_existing_bootstrap_path",
    "resolve_readiness_output_path",
    "result_at_rank",
    "result_source_id",
]
