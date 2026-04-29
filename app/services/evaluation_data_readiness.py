from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    ClaimSupportReplayAlertFixtureCorpusRow,
    ClaimSupportReplayAlertFixtureCorpusSnapshot,
    Document,
    DocumentRun,
    DocumentRunEvaluation,
    DocumentRunEvaluationQuery,
    RetrievalJudgmentSet,
    RetrievalTrainingRun,
    SearchFeedback,
    SearchHarnessEvaluationSource,
    SearchReplayRun,
    SearchRequestRecord,
    TechnicalReportClaimRetrievalFeedback,
)

REPLAY_SOURCE_TYPES = [
    "evaluation_queries",
    "feedback",
    "live_search_gaps",
    "cross_document_prose_regressions",
    "technical_report_claim_feedback",
]
BASIC_REPLAY_SOURCE_TYPES = [
    "evaluation_queries",
    "live_search_gaps",
    "cross_document_prose_regressions",
]
FEEDBACK_TYPES = ["relevant", "irrelevant", "missing_table", "missing_chunk", "no_answer"]
CLAIM_FEEDBACK_LABELS = ["positive", "negative", "missing"]
CLAIM_FEEDBACK_STATUSES = ["supported", "weak", "missing", "contradicted", "rejected"]
DEFAULT_THRESHOLDS = {
    "min_active_documents": 1,
    "min_completed_evaluations": 1,
    "min_evaluation_queries": 1,
    "min_auto_corpus_documents": 25,
    "min_auto_table_queries": 25,
    "min_auto_chunk_queries": 25,
    "min_gold_corpus_documents": 5,
    "min_gold_table_queries": 10,
    "min_gold_chunk_queries": 20,
    "min_gold_answer_queries": 5,
    "min_search_feedback_rows": 25,
    "min_feedback_rows_per_type": 1,
    "min_claim_feedback_rows": 25,
    "min_claim_feedback_rows_per_label": 1,
    "min_claim_feedback_rows_per_status": 1,
    "min_claim_support_replay_alert_rows": 5,
    "min_completed_replay_runs_per_source": 1,
    "min_harness_evaluation_sources_per_source": 1,
    "min_retrieval_judgment_sets": 1,
    "min_retrieval_training_runs": 1,
    "min_retrieval_training_examples": 25,
}


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def _count(session: Session, model, *criteria) -> int:
    statement = select(func.count()).select_from(model)
    if criteria:
        statement = statement.where(*criteria)
    return int(session.scalar(statement) or 0)


def _group_counts(session: Session, model, column, *criteria) -> dict[str, int]:
    statement = select(column, func.count()).select_from(model)
    if criteria:
        statement = statement.where(*criteria)
    statement = statement.group_by(column)
    return {
        str(key): int(value)
        for key, value in session.execute(statement).all()
        if key is not None
    }


def _load_corpus(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False, "documents": 0}
    data = yaml.safe_load(path.read_text()) or {}
    documents = data.get("documents") if isinstance(data, dict) else []
    if not isinstance(documents, list):
        documents = []
    table_queries = 0
    chunk_queries = 0
    cross_document_queries = 0
    answer_queries = 0
    expected_merged_table_docs = 0
    table_threshold_docs = 0
    figure_threshold_docs = 0
    source_filenames: list[str] = []
    for document in documents:
        if not isinstance(document, dict):
            continue
        source_filename = document.get("source_filename")
        if source_filename:
            source_filenames.append(str(source_filename))
        thresholds = document.get("thresholds") or {}
        if not isinstance(thresholds, dict):
            continue
        table_queries += len(thresholds.get("expected_top_n_table_hit_queries") or [])
        chunk_queries += len(thresholds.get("expected_top_n_chunk_hit_queries") or [])
        cross_document_queries += len(thresholds.get("queries") or [])
        answer_queries += len(thresholds.get("expected_answer_queries") or [])
        expected_merged_table_docs += int(bool(thresholds.get("expected_merged_tables")))
        table_threshold_docs += int(thresholds.get("expected_logical_table_count") is not None)
        figure_threshold_docs += int(thresholds.get("expected_figure_count") is not None)
    return {
        "path": str(path),
        "exists": True,
        "documents": len(documents),
        "table_queries": table_queries,
        "chunk_queries": chunk_queries,
        "cross_document_queries": cross_document_queries,
        "answer_queries": answer_queries,
        "expected_merged_table_docs": expected_merged_table_docs,
        "table_threshold_docs": table_threshold_docs,
        "figure_threshold_docs": figure_threshold_docs,
        "source_filenames": source_filenames,
    }


def summarize_evaluation_corpora(
    *,
    manual_corpus_path: Path = Path("docs/evaluation_corpus.yaml"),
    auto_corpus_path: Path = Path("storage/evaluation_corpus.auto.yaml"),
    db_source_filenames: set[str] | None = None,
) -> dict[str, Any]:
    manual = _load_corpus(manual_corpus_path)
    auto = _load_corpus(auto_corpus_path)
    db_names = db_source_filenames or set()
    for corpus in (manual, auto):
        names = set(corpus.get("source_filenames") or [])
        corpus["document_filename_match_count"] = len(names & db_names) if db_names else 0
        corpus["document_filename_missing_count"] = len(names - db_names) if db_names else None
        corpus.pop("source_filenames", None)
    return {"manual": manual, "auto": auto}


def _claim_feedback_traceability_issue_counts(
    rows: list[TechnicalReportClaimRetrievalFeedback],
) -> dict[str, int]:
    issues: Counter[str] = Counter()
    for row in rows:
        if not row.feedback_payload_sha256:
            issues["feedback_payload_hash_missing"] += 1
        if not row.source_payload_sha256:
            issues["source_payload_hash_missing"] += 1
        if not row.source_search_request_id and not row.source_search_request_ids_json:
            issues["source_search_request_missing"] += 1
        if row.learning_label in {"positive", "negative"} and not row.search_request_result_id:
            issues["target_result_missing"] += 1
        if row.learning_label in {"positive", "negative"} and not row.evidence_refs_json:
            issues["evidence_refs_missing"] += 1
        if not row.evidence_manifest_id:
            issues["evidence_manifest_missing"] += 1
        if not row.prov_export_artifact_id:
            issues["prov_export_artifact_missing"] += 1
        if not row.release_readiness_db_gate_id:
            issues["release_readiness_db_gate_missing"] += 1
        if not row.semantic_governance_event_id:
            issues["semantic_governance_event_missing"] += 1
    return dict(sorted(issues.items()))


def _db_summary(session: Session) -> dict[str, Any]:
    db_source_filenames = set(session.scalars(select(Document.source_filename)).all())
    claim_rows = list(session.scalars(select(TechnicalReportClaimRetrievalFeedback)))
    completed_replay_counts = _group_counts(
        session,
        SearchReplayRun,
        SearchReplayRun.source_type,
        SearchReplayRun.status == "completed",
    )
    replay_query_counts = {
        str(source_type): int(query_count or 0)
        for source_type, query_count in session.execute(
            select(SearchReplayRun.source_type, func.sum(SearchReplayRun.query_count))
            .where(SearchReplayRun.status == "completed")
            .group_by(SearchReplayRun.source_type)
        ).all()
    }
    harness_source_counts = _group_counts(
        session,
        SearchHarnessEvaluationSource,
        SearchHarnessEvaluationSource.source_type,
    )
    training_rows = list(
        session.scalars(
            select(RetrievalTrainingRun).where(RetrievalTrainingRun.status == "completed")
        )
    )
    return {
        "db_source_filenames": db_source_filenames,
        "documents": {
            "total": _count(session, Document),
            "active": _count(session, Document, Document.active_run_id.is_not(None)),
        },
        "runs": {
            "total": _count(session, DocumentRun),
            "completed": _count(session, DocumentRun, DocumentRun.status == "completed"),
        },
        "evaluations": {
            "total": _count(session, DocumentRunEvaluation),
            "completed": _count(
                session,
                DocumentRunEvaluation,
                DocumentRunEvaluation.status == "completed",
            ),
            "queries": _count(session, DocumentRunEvaluationQuery),
            "passed_queries": _count(
                session,
                DocumentRunEvaluationQuery,
                DocumentRunEvaluationQuery.passed.is_(True),
            ),
        },
        "search": {
            "requests": _count(session, SearchRequestRecord),
            "feedback_total": _count(session, SearchFeedback),
            "feedback_by_type": _group_counts(
                session,
                SearchFeedback,
                SearchFeedback.feedback_type,
            ),
        },
        "claim_feedback": {
            "total": len(claim_rows),
            "by_learning_label": _group_counts(
                session,
                TechnicalReportClaimRetrievalFeedback,
                TechnicalReportClaimRetrievalFeedback.learning_label,
            ),
            "by_status": _group_counts(
                session,
                TechnicalReportClaimRetrievalFeedback,
                TechnicalReportClaimRetrievalFeedback.feedback_status,
            ),
            "traceability_issue_counts": _claim_feedback_traceability_issue_counts(claim_rows),
        },
        "claim_support_replay_alert_corpus": {
            "rows": _count(session, ClaimSupportReplayAlertFixtureCorpusRow),
            "active_snapshots": _count(
                session,
                ClaimSupportReplayAlertFixtureCorpusSnapshot,
                ClaimSupportReplayAlertFixtureCorpusSnapshot.status == "active",
            ),
        },
        "replays": {
            "completed_runs_by_source": completed_replay_counts,
            "completed_query_counts_by_source": replay_query_counts,
        },
        "harness_evaluations": {
            "source_rows_by_source": harness_source_counts,
        },
        "retrieval_learning": {
            "judgment_sets": _count(session, RetrievalJudgmentSet),
            "completed_training_runs": len(training_rows),
            "training_examples": sum(int(row.example_count or 0) for row in training_rows),
        },
    }


def _gate(
    key: str,
    passed: bool,
    *,
    metric: Any,
    threshold: Any,
    required_for: list[str],
    next_action: str,
) -> dict[str, Any]:
    return {
        "key": key,
        "passed": bool(passed),
        "metric": metric,
        "threshold": threshold,
        "required_for": required_for,
        "next_action": next_action,
    }


def _missing_keys(counts: dict[str, int], keys: list[str], minimum: int) -> list[str]:
    return [key for key in keys if int(counts.get(key) or 0) < minimum]


def build_readiness_gates(
    *,
    db: dict[str, Any],
    corpora: dict[str, Any],
    thresholds: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    t = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    auto = corpora["auto"]
    manual = corpora["manual"]
    feedback_by_type = db["search"]["feedback_by_type"]
    claim_by_label = db["claim_feedback"]["by_learning_label"]
    claim_by_status = db["claim_feedback"]["by_status"]
    replay_counts = db["replays"]["completed_runs_by_source"]
    harness_source_counts = db["harness_evaluations"]["source_rows_by_source"]
    missing_feedback_types = _missing_keys(
        feedback_by_type,
        FEEDBACK_TYPES,
        t["min_feedback_rows_per_type"],
    )
    missing_claim_labels = _missing_keys(
        claim_by_label,
        CLAIM_FEEDBACK_LABELS,
        t["min_claim_feedback_rows_per_label"],
    )
    missing_claim_statuses = _missing_keys(
        claim_by_status,
        CLAIM_FEEDBACK_STATUSES,
        t["min_claim_feedback_rows_per_status"],
    )
    missing_replay_sources = _missing_keys(
        replay_counts,
        REPLAY_SOURCE_TYPES,
        t["min_completed_replay_runs_per_source"],
    )
    missing_basic_replay_sources = _missing_keys(
        replay_counts,
        BASIC_REPLAY_SOURCE_TYPES,
        t["min_completed_replay_runs_per_source"],
    )
    missing_harness_sources = _missing_keys(
        harness_source_counts,
        REPLAY_SOURCE_TYPES,
        t["min_harness_evaluation_sources_per_source"],
    )
    claim_traceability_issues = db["claim_feedback"]["traceability_issue_counts"]
    return [
        _gate(
            "active_document_corpus",
            db["documents"]["active"] >= t["min_active_documents"],
            metric=db["documents"]["active"],
            threshold=t["min_active_documents"],
            required_for=["regression", "court_grade"],
            next_action="Ingest and validate at least one active document run.",
        ),
        _gate(
            "persisted_run_evaluations",
            db["evaluations"]["completed"] >= t["min_completed_evaluations"]
            and db["evaluations"]["queries"] >= t["min_evaluation_queries"],
            metric={
                "completed_evaluations": db["evaluations"]["completed"],
                "evaluation_queries": db["evaluations"]["queries"],
            },
            threshold={
                "completed_evaluations": t["min_completed_evaluations"],
                "evaluation_queries": t["min_evaluation_queries"],
            },
            required_for=["regression", "court_grade"],
            next_action="Run docling-system-eval-corpus or evaluate active document runs.",
        ),
        _gate(
            "auto_generated_regression_corpus",
            auto.get("documents", 0) >= t["min_auto_corpus_documents"]
            and auto.get("table_queries", 0) >= t["min_auto_table_queries"]
            and auto.get("chunk_queries", 0) >= t["min_auto_chunk_queries"],
            metric={
                "documents": auto.get("documents", 0),
                "table_queries": auto.get("table_queries", 0),
                "chunk_queries": auto.get("chunk_queries", 0),
            },
            threshold={
                "documents": t["min_auto_corpus_documents"],
                "table_queries": t["min_auto_table_queries"],
                "chunk_queries": t["min_auto_chunk_queries"],
            },
            required_for=["regression"],
            next_action="Ingest representative PDFs so auto fixtures cover table and chunk recall.",
        ),
        _gate(
            "hand_verified_gold_corpus",
            manual.get("documents", 0) >= t["min_gold_corpus_documents"]
            and manual.get("table_queries", 0) >= t["min_gold_table_queries"]
            and manual.get("chunk_queries", 0) >= t["min_gold_chunk_queries"]
            and manual.get("answer_queries", 0) >= t["min_gold_answer_queries"],
            metric={
                "documents": manual.get("documents", 0),
                "table_queries": manual.get("table_queries", 0),
                "chunk_queries": manual.get("chunk_queries", 0),
                "answer_queries": manual.get("answer_queries", 0),
            },
            threshold={
                "documents": t["min_gold_corpus_documents"],
                "table_queries": t["min_gold_table_queries"],
                "chunk_queries": t["min_gold_chunk_queries"],
                "answer_queries": t["min_gold_answer_queries"],
            },
            required_for=["court_grade"],
            next_action="Add hand-verified fixtures with exact source-page/span expectations.",
        ),
        _gate(
            "operator_feedback_coverage",
            db["search"]["feedback_total"] >= t["min_search_feedback_rows"]
            and not missing_feedback_types,
            metric={
                "total": db["search"]["feedback_total"],
                "by_type": feedback_by_type,
                "missing_types": missing_feedback_types,
            },
            threshold={
                "total": t["min_search_feedback_rows"],
                "per_type": t["min_feedback_rows_per_type"],
            },
            required_for=["court_grade"],
            next_action=(
                "Label real searches as relevant, irrelevant, missing_table, "
                "missing_chunk, and no_answer."
            ),
        ),
        _gate(
            "technical_report_claim_feedback_ledger",
            db["claim_feedback"]["total"] >= t["min_claim_feedback_rows"]
            and not missing_claim_labels
            and not missing_claim_statuses
            and not claim_traceability_issues,
            metric={
                "total": db["claim_feedback"]["total"],
                "by_learning_label": claim_by_label,
                "by_status": claim_by_status,
                "missing_labels": missing_claim_labels,
                "missing_statuses": missing_claim_statuses,
                "traceability_issue_counts": claim_traceability_issues,
            },
            threshold={
                "total": t["min_claim_feedback_rows"],
                "per_label": t["min_claim_feedback_rows_per_label"],
                "per_status": t["min_claim_feedback_rows_per_status"],
                "traceability_issues": 0,
            },
            required_for=["court_grade"],
            next_action=(
                "Run technical-report verification and generate supported, weak, "
                "missing, contradicted, and rejected claim-feedback rows with audit links."
            ),
        ),
        _gate(
            "claim_support_replay_alert_corpus",
            db["claim_support_replay_alert_corpus"]["rows"]
            >= t["min_claim_support_replay_alert_rows"]
            and db["claim_support_replay_alert_corpus"]["active_snapshots"] >= 1,
            metric=db["claim_support_replay_alert_corpus"],
            threshold={
                "rows": t["min_claim_support_replay_alert_rows"],
                "active_snapshots": 1,
            },
            required_for=["court_grade"],
            next_action=(
                "Promote governed claim-support hard cases into an active "
                "replay-alert corpus snapshot."
            ),
        ),
        _gate(
            "basic_replay_source_coverage",
            not missing_basic_replay_sources,
            metric={
                "completed_runs_by_source": replay_counts,
                "completed_query_counts_by_source": db["replays"][
                    "completed_query_counts_by_source"
                ],
                "required_sources": BASIC_REPLAY_SOURCE_TYPES,
                "missing_sources": missing_basic_replay_sources,
            },
            threshold={"completed_runs_per_source": t["min_completed_replay_runs_per_source"]},
            required_for=["regression"],
            next_action=(
                "Run replay suites for evaluation_queries, live_search_gaps, "
                "and cross_document_prose_regressions."
            ),
        ),
        _gate(
            "all_replay_source_coverage",
            not missing_replay_sources,
            metric={
                "completed_runs_by_source": replay_counts,
                "completed_query_counts_by_source": db["replays"][
                    "completed_query_counts_by_source"
                ],
                "required_sources": REPLAY_SOURCE_TYPES,
                "missing_sources": missing_replay_sources,
            },
            threshold={"completed_runs_per_source": t["min_completed_replay_runs_per_source"]},
            required_for=["court_grade"],
            next_action=(
                "Run replay suites for every source, including "
                "technical_report_claim_feedback after claim feedback exists."
            ),
        ),
        _gate(
            "harness_evaluation_source_coverage",
            not missing_harness_sources,
            metric={
                "source_rows_by_source": harness_source_counts,
                "missing_sources": missing_harness_sources,
            },
            threshold={
                "harness_evaluation_source_rows_per_source": (
                    t["min_harness_evaluation_sources_per_source"]
                )
            },
            required_for=["court_grade"],
            next_action="Run a harness evaluation that includes all replay source types.",
        ),
        _gate(
            "retrieval_learning_materialized",
            db["retrieval_learning"]["judgment_sets"] >= t["min_retrieval_judgment_sets"]
            and db["retrieval_learning"]["completed_training_runs"]
            >= t["min_retrieval_training_runs"]
            and db["retrieval_learning"]["training_examples"]
            >= t["min_retrieval_training_examples"],
            metric=db["retrieval_learning"],
            threshold={
                "judgment_sets": t["min_retrieval_judgment_sets"],
                "completed_training_runs": t["min_retrieval_training_runs"],
                "training_examples": t["min_retrieval_training_examples"],
            },
            required_for=["court_grade"],
            next_action=(
                "Materialize retrieval-learning data from feedback, replay, "
                "and claim-feedback sources."
            ),
        ),
    ]


def summarize_readiness(gates: list[dict[str, Any]]) -> dict[str, Any]:
    regression_failed = [
        gate["key"]
        for gate in gates
        if "regression" in gate["required_for"] and not gate["passed"]
    ]
    court_failed = [
        gate["key"]
        for gate in gates
        if "court_grade" in gate["required_for"] and not gate["passed"]
    ]
    return {
        "regression_ready": not regression_failed,
        "court_grade_ready": not court_failed,
        "regression_blockers": regression_failed,
        "court_grade_blockers": court_failed,
        "passed_gate_count": sum(1 for gate in gates if gate["passed"]),
        "failed_gate_count": sum(1 for gate in gates if not gate["passed"]),
    }


def build_evaluation_data_readiness_report(
    session: Session,
    *,
    manual_corpus_path: Path = Path("docs/evaluation_corpus.yaml"),
    auto_corpus_path: Path = Path("storage/evaluation_corpus.auto.yaml"),
    thresholds: dict[str, int] | None = None,
) -> dict[str, Any]:
    db = _db_summary(session)
    db_source_filenames = db.pop("db_source_filenames")
    corpora = summarize_evaluation_corpora(
        manual_corpus_path=manual_corpus_path,
        auto_corpus_path=auto_corpus_path,
        db_source_filenames=db_source_filenames,
    )
    gates = build_readiness_gates(db=db, corpora=corpora, thresholds=thresholds)
    summary = summarize_readiness(gates)
    return {
        "schema_name": "evaluation_data_readiness_report",
        "schema_version": "1.0",
        "generated_at": _utc_iso(),
        "summary": summary,
        "thresholds": {**DEFAULT_THRESHOLDS, **(thresholds or {})},
        "database": db,
        "corpora": corpora,
        "gates": gates,
        "next_actions": [gate["next_action"] for gate in gates if not gate["passed"]],
    }
