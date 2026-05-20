from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.time import utcnow
from app.db.models import (
    ClaimSupportReplayAlertFixtureCorpusSnapshot,
    RetrievalTrainingRun,
    SearchFeedback,
    SearchHarnessEvaluationSource,
    SearchRequestRecord,
    TechnicalReportClaimRetrievalFeedback,
)
from app.services.court_grade_readiness_bootstrap import (
    CourtGradeReadinessBootstrapError,
    bootstrap_court_grade_readiness,
)
from app.services.regression_readiness_bootstrap import bootstrap_regression_readiness

pytestmark = pytest.mark.skipif(
    not os.getenv("DOCLING_SYSTEM_RUN_INTEGRATION"),
    reason="Set DOCLING_SYSTEM_RUN_INTEGRATION=1 to run Postgres-backed integration tests.",
)


def _bootstrap_paths(storage_root: Path) -> tuple[Path, Path]:
    return (
        storage_root / "evaluation_corpus.auto.yaml",
        storage_root / "evaluation_data_readiness.latest.json",
    )


def test_bootstrap_court_grade_readiness_turns_all_db_blockers_green(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.services.runs.semantics_feature_enabled", lambda settings: False)

    auto_corpus_path, readiness_output_path = _bootstrap_paths(
        postgres_integration_harness.storage_service.storage_root
    )

    with postgres_integration_harness.session_factory() as session:
        regression_payload = bootstrap_regression_readiness(
            session,
            storage_service=postgres_integration_harness.storage_service,
            bootstrap_document_path=Path("docs/evaluation_bootstrap/regression_doc_03.pdf"),
            manual_corpus_path=Path("docs/evaluation_corpus.yaml"),
            auto_corpus_seed_path=Path("docs/evaluation_corpus.auto.bootstrap.yaml"),
            auto_corpus_path=auto_corpus_path,
            output_path=readiness_output_path,
        )
        session.commit()

    assert regression_payload["readiness"]["summary"]["regression_ready"] is True
    assert regression_payload["readiness"]["summary"]["court_grade_ready"] is False

    with postgres_integration_harness.session_factory() as session:
        payload = bootstrap_court_grade_readiness(
            session,
            storage_service=postgres_integration_harness.storage_service,
            manual_corpus_path=Path("docs/evaluation_corpus.yaml"),
            auto_corpus_path=auto_corpus_path,
            output_path=readiness_output_path,
        )

    assert payload["schema_name"] == "court_grade_readiness_bootstrap_result"
    assert payload["operator_feedback"]["created_rows"] == 25
    assert payload["claim_feedback"]["created_rows"] == 25
    assert payload["replay_alert_corpus"]["fixture_count"] == 5
    assert payload["readiness"]["summary"]["regression_ready"] is True
    assert payload["readiness"]["summary"]["court_grade_ready"] is True
    assert payload["readiness"]["summary"]["failed_gate_count"] == 0
    assert payload["readiness"]["summary"]["court_grade_blockers"] == []
    assert readiness_output_path.exists()
    assert json.loads(readiness_output_path.read_text())["summary"]["court_grade_ready"] is True

    with postgres_integration_harness.session_factory() as session:
        feedback_count = int(session.scalar(select(func.count()).select_from(SearchFeedback)) or 0)
        claim_feedback_count = int(
            session.scalar(select(func.count()).select_from(TechnicalReportClaimRetrievalFeedback))
            or 0
        )
        active_snapshot_count = session.scalar(
            select(func.count())
            .select_from(ClaimSupportReplayAlertFixtureCorpusSnapshot)
            .where(ClaimSupportReplayAlertFixtureCorpusSnapshot.status == "active")
        )
        source_types = set(
            session.scalars(select(SearchHarnessEvaluationSource.source_type)).all()
        )
        training_runs = list(
            session.scalars(
                select(RetrievalTrainingRun).where(RetrievalTrainingRun.status == "completed")
            )
        )

    assert feedback_count == 25
    assert claim_feedback_count == 25
    assert active_snapshot_count == 1
    assert {
        "evaluation_queries",
        "feedback",
        "live_search_gaps",
        "cross_document_prose_regressions",
        "technical_report_claim_feedback",
    }.issubset(source_types)
    assert len(training_runs) == 1
    assert int(training_runs[0].example_count or 0) >= 25


def test_bootstrap_court_grade_readiness_refuses_mixed_advanced_state(
    postgres_integration_harness,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.services.runs.semantics_feature_enabled", lambda settings: False)

    auto_corpus_path, readiness_output_path = _bootstrap_paths(
        postgres_integration_harness.storage_service.storage_root
    )

    with postgres_integration_harness.session_factory() as session:
        bootstrap_regression_readiness(
            session,
            storage_service=postgres_integration_harness.storage_service,
            bootstrap_document_path=Path("docs/evaluation_bootstrap/regression_doc_03.pdf"),
            manual_corpus_path=Path("docs/evaluation_corpus.yaml"),
            auto_corpus_seed_path=Path("docs/evaluation_corpus.auto.bootstrap.yaml"),
            auto_corpus_path=auto_corpus_path,
            output_path=readiness_output_path,
        )
        request = session.scalar(
            select(SearchRequestRecord).order_by(SearchRequestRecord.created_at.asc()).limit(1)
        )
        assert request is not None
        session.add(
            SearchFeedback(
                id=uuid4(),
                search_request_id=request.id,
                search_request_result_id=None,
                result_rank=None,
                feedback_type="no_answer",
                note="unexpected pre-seeded feedback row",
                created_at=utcnow(),
            )
        )
        session.commit()

    with postgres_integration_harness.session_factory() as session:
        with pytest.raises(
            CourtGradeReadinessBootstrapError,
            match="Advanced readiness rows already exist",
        ):
            bootstrap_court_grade_readiness(
                session,
                storage_service=postgres_integration_harness.storage_service,
                manual_corpus_path=Path("docs/evaluation_corpus.yaml"),
                auto_corpus_path=auto_corpus_path,
                output_path=readiness_output_path,
            )
