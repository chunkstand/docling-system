from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.search import (
    SearchFeedbackCreateRequest,
    SearchHarnessEvaluationRequest,
    SearchReplayRunRequest,
)
from app.services.court_grade_readiness_bootstrap_claim_feedback import (
    seed_claim_feedback,
)
from app.services.court_grade_readiness_bootstrap_replay_alerts import (
    seed_replay_alert_fixture_corpus,
)
from app.services.court_grade_readiness_bootstrap_support import (
    DEFAULT_AUTO_CORPUS_PATH,
    DEFAULT_CLAIM_FEEDBACK_SEED_PATH,
    DEFAULT_HARNESS_NAME,
    DEFAULT_MANUAL_CORPUS_PATH,
    DEFAULT_OPERATOR_FEEDBACK_SEED_PATH,
    DEFAULT_REPLAY_ALERT_FIXTURE_SEED_PATH,
    DEFAULT_REPLAY_LIMIT,
    DEFAULT_RETRIEVAL_LEARNING_LIMIT,
    CourtGradeReadinessBootstrapError,
    active_bootstrap_document,
    assert_regression_baseline_state,
    execute_bootstrap_search,
    expand_claim_feedback_seed,
    expand_operator_feedback_seed,
    load_bootstrap_yaml_mapping,
    load_replay_alert_fixture_seed_rows,
    resolve_existing_bootstrap_path,
    resolve_readiness_output_path,
    result_at_rank,
)
from app.services.evaluation_data_readiness import build_evaluation_data_readiness_report
from app.services.retrieval_learning import materialize_retrieval_learning_dataset
from app.services.search_harness_evaluations import evaluate_search_harness
from app.services.search_history import record_search_feedback
from app.services.search_replays import run_search_replay_suite
from app.services.storage import StorageService


def _seed_operator_feedback(
    session: Session,
    *,
    document_id,
    seed_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    feedback_ids: list[str] = []
    for row in seed_rows:
        request, results = execute_bootstrap_search(
            session,
            query_text=row["query_text"],
            mode=row["mode"],
            document_id=document_id,
        )
        result = result_at_rank(
            results,
            result_rank=row.get("result_rank"),
            query_text=row["query_text"],
        )
        payload = SearchFeedbackCreateRequest(
            feedback_type=row["feedback_type"],
            result_rank=result.rank if result is not None else None,
            note=row.get("note"),
        )
        response = record_search_feedback(session, request.id, payload)
        feedback_ids.append(str(response.feedback_id))
        counts[row["feedback_type"]] += 1
    session.flush()
    return {
        "created_rows": len(seed_rows),
        "feedback_ids": feedback_ids,
        "counts_by_type": dict(sorted(counts.items())),
    }


def _run_required_replay_suites(
    session: Session,
    *,
    replay_limit: int,
) -> dict[str, Any]:
    payloads: dict[str, Any] = {}
    for source_type in ("feedback", "technical_report_claim_feedback"):
        replay = run_search_replay_suite(
            session,
            SearchReplayRunRequest(source_type=source_type, limit=replay_limit),
        )
        if replay.status != "completed":
            raise CourtGradeReadinessBootstrapError(
                f"Court-grade replay suite {source_type} did not complete successfully."
            )
        payloads[source_type] = replay.model_dump(mode="json")
    return payloads


def _run_harness_evaluation(
    session: Session,
    *,
    harness_name: str,
    replay_limit: int,
) -> dict[str, Any]:
    evaluation = evaluate_search_harness(
        session,
        SearchHarnessEvaluationRequest(
            baseline_harness_name=harness_name,
            candidate_harness_name=harness_name,
            source_types=[
                "evaluation_queries",
                "feedback",
                "live_search_gaps",
                "cross_document_prose_regressions",
                "technical_report_claim_feedback",
            ],
            limit=replay_limit,
        ),
    )
    if evaluation.status != "completed":
        raise CourtGradeReadinessBootstrapError(
            "Court-grade bootstrap harness evaluation did not complete successfully."
        )
    return evaluation.model_dump(mode="json")


def _materialize_retrieval_learning(
    session: Session,
    *,
    limit: int,
) -> dict[str, Any]:
    payload = materialize_retrieval_learning_dataset(
        session,
        limit=limit,
        source_types=[
            "feedback",
            "replay",
            "claim_support_replay_alert_corpus",
            "technical_report_claim_feedback",
        ],
        set_name="court-grade-ready-seed",
        created_by="court_grade_bootstrap",
    )
    summary = payload.get("summary") or {}
    if int(summary.get("training_example_count") or 0) < 25:
        raise CourtGradeReadinessBootstrapError(
            "Court-grade bootstrap retrieval-learning materialization stayed below 25 "
            "training examples."
        )
    return payload


def bootstrap_court_grade_readiness(
    session: Session,
    *,
    storage_service: StorageService,
    manual_corpus_path: Path = DEFAULT_MANUAL_CORPUS_PATH,
    auto_corpus_path: Path = DEFAULT_AUTO_CORPUS_PATH,
    operator_feedback_seed_path: Path = DEFAULT_OPERATOR_FEEDBACK_SEED_PATH,
    claim_feedback_seed_path: Path = DEFAULT_CLAIM_FEEDBACK_SEED_PATH,
    replay_alert_fixture_seed_path: Path = DEFAULT_REPLAY_ALERT_FIXTURE_SEED_PATH,
    output_path: Path | None = None,
    replay_limit: int = DEFAULT_REPLAY_LIMIT,
    retrieval_learning_limit: int = DEFAULT_RETRIEVAL_LEARNING_LIMIT,
    harness_name: str = DEFAULT_HARNESS_NAME,
) -> dict[str, Any]:
    manual_corpus_path = resolve_existing_bootstrap_path(
        manual_corpus_path,
        error_cls=CourtGradeReadinessBootstrapError,
    )
    auto_corpus_path = resolve_existing_bootstrap_path(
        auto_corpus_path,
        error_cls=CourtGradeReadinessBootstrapError,
    )
    operator_feedback_seed_path = resolve_existing_bootstrap_path(
        operator_feedback_seed_path,
        error_cls=CourtGradeReadinessBootstrapError,
    )
    claim_feedback_seed_path = resolve_existing_bootstrap_path(
        claim_feedback_seed_path,
        error_cls=CourtGradeReadinessBootstrapError,
    )
    replay_alert_fixture_seed_path = resolve_existing_bootstrap_path(
        replay_alert_fixture_seed_path,
        error_cls=CourtGradeReadinessBootstrapError,
    )
    output_path = resolve_readiness_output_path(
        output_path,
        storage_service=storage_service,
        default_filename="evaluation_data_readiness.latest.json",
    )

    operator_seed = load_bootstrap_yaml_mapping(
        operator_feedback_seed_path,
        error_cls=CourtGradeReadinessBootstrapError,
    )
    claim_seed = load_bootstrap_yaml_mapping(
        claim_feedback_seed_path,
        error_cls=CourtGradeReadinessBootstrapError,
    )
    replay_alert_seed = load_bootstrap_yaml_mapping(
        replay_alert_fixture_seed_path,
        error_cls=CourtGradeReadinessBootstrapError,
    )
    expected_source_filename = str(operator_seed.get("source_filename") or "")
    if not expected_source_filename:
        raise CourtGradeReadinessBootstrapError(
            "Court-grade operator feedback seed is missing source_filename."
        )
    if claim_seed.get("source_filename") != expected_source_filename:
        raise CourtGradeReadinessBootstrapError(
            "Court-grade claim feedback seed does not match the operator feedback source."
        )
    if replay_alert_seed.get("source_filename") != expected_source_filename:
        raise CourtGradeReadinessBootstrapError(
            "Court-grade replay-alert seed does not match the operator feedback source."
        )

    baseline_readiness = assert_regression_baseline_state(
        session,
        manual_corpus_path=manual_corpus_path,
        auto_corpus_path=auto_corpus_path,
    )
    document = active_bootstrap_document(
        session,
        expected_source_filename=expected_source_filename,
    )
    operator_feedback = _seed_operator_feedback(
        session,
        document_id=document.id,
        seed_rows=expand_operator_feedback_seed(operator_seed),
    )
    claim_feedback = seed_claim_feedback(
        session,
        document_id=document.id,
        seed_rows=expand_claim_feedback_seed(claim_seed),
        storage_service=storage_service,
    )
    replay_alert_corpus = seed_replay_alert_fixture_corpus(
        session,
        document_id=document.id,
        seed_rows=load_replay_alert_fixture_seed_rows(replay_alert_seed),
        storage_service=storage_service,
    )
    replay_runs = _run_required_replay_suites(session, replay_limit=replay_limit)
    harness_evaluation = _run_harness_evaluation(
        session,
        harness_name=harness_name,
        replay_limit=replay_limit,
    )
    retrieval_learning = _materialize_retrieval_learning(
        session,
        limit=retrieval_learning_limit,
    )
    session.commit()
    session.expire_all()
    readiness = build_evaluation_data_readiness_report(
        session,
        manual_corpus_path=manual_corpus_path,
        auto_corpus_path=auto_corpus_path,
    )
    summary = readiness.get("summary") or {}
    if summary.get("court_grade_ready") is not True or summary.get("failed_gate_count") != 0:
        raise CourtGradeReadinessBootstrapError(
            "Court-grade bootstrap completed but the readiness gate is still red: "
            f"{summary.get('court_grade_blockers')}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(readiness, indent=2) + "\n")
    return {
        "schema_name": "court_grade_readiness_bootstrap_result",
        "schema_version": "1.0",
        "baseline_readiness": baseline_readiness.get("summary") or {},
        "operator_feedback": operator_feedback,
        "claim_feedback": claim_feedback,
        "replay_alert_corpus": replay_alert_corpus,
        "replay_runs": replay_runs,
        "harness_evaluation": harness_evaluation,
        "retrieval_learning": retrieval_learning,
        "readiness": readiness,
    }
