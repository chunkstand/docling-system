from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import (
    Document,
    DocumentRun,
    DocumentRunEvaluation,
    SearchReplayRun,
    SearchRequestRecord,
)
from app.schemas.search import SearchReplayRunRequest, SearchRequest
from app.services.docling_parser import DoclingParser
from app.services.document_ingest import ingest_local_file
from app.services.evaluation_data_readiness import build_evaluation_data_readiness_report
from app.services.evaluations import evaluate_run
from app.services.readiness_bootstrap_support import (
    count_model_rows,
    resolve_existing_bootstrap_path,
    resolve_readiness_output_path,
)
from app.services.runs import claim_next_run, process_run
from app.services.search import execute_search
from app.services.search_replays import run_search_replay_suite
from app.services.storage import StorageService

AUTO_CORPUS_FILENAME = "evaluation_corpus.auto.yaml"
READINESS_REPORT_FILENAME = "evaluation_data_readiness.latest.json"
DEFAULT_BOOTSTRAP_DOCUMENT_PATH = Path("docs/evaluation_bootstrap/regression_doc_03.pdf")
DEFAULT_MANUAL_CORPUS_PATH = Path("docs/evaluation_corpus.yaml")
DEFAULT_AUTO_CORPUS_SEED_PATH = Path("docs/evaluation_corpus.auto.bootstrap.yaml")
DEFAULT_LIVE_GAP_QUERY = "Blue Mesas readiness narrative explains how milestone six"
DEFAULT_REPLAY_LIMIT = 25
DEFAULT_REPLAY_SOURCE_TYPES = (
    "evaluation_queries",
    "live_search_gaps",
    "cross_document_prose_regressions",
)
DEFAULT_WORKER_ID = "regression-readiness-bootstrap"


class RegressionReadinessBootstrapError(RuntimeError):
    pass


def _resolve_auto_corpus_path(path: Path | None, *, storage_service: StorageService) -> Path:
    if path is not None:
        return path.expanduser().resolve()
    return (storage_service.storage_root / AUTO_CORPUS_FILENAME).resolve()


def _assert_empty_bootstrap_state(session: Session) -> None:
    counts = {
        "documents": count_model_rows(session, Document),
        "runs": count_model_rows(session, DocumentRun),
        "evaluations": count_model_rows(session, DocumentRunEvaluation),
        "search_requests": count_model_rows(session, SearchRequestRecord),
        "replay_runs": count_model_rows(session, SearchReplayRun),
    }
    occupied = {key: value for key, value in counts.items() if value}
    if occupied:
        raise RegressionReadinessBootstrapError(
            "Regression-readiness bootstrap requires an empty DB so the outcome stays "
            f"deterministic. Current row counts: {occupied}"
        )


def _install_auto_corpus_seed(*, seed_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(seed_path.read_text())


def _seed_live_gap_query(session: Session, *, query_text: str) -> str:
    execution = execute_search(
        session,
        SearchRequest.model_validate(
            {
                "query": query_text,
                "mode": "keyword",
                "limit": 10,
            }
        ),
        origin="api",
    )
    session.commit()
    if execution.request_id is None:
        raise RegressionReadinessBootstrapError(
            "Live-gap bootstrap search did not persist a search_request_id."
        )
    return str(execution.request_id)


def _queue_bootstrap_document(
    session: Session,
    *,
    bootstrap_document_path: Path,
    storage_service: StorageService,
) -> tuple[str, str]:
    response, status_code = ingest_local_file(session, bootstrap_document_path, storage_service)
    if status_code != 202 or response.run_id is None:
        raise RegressionReadinessBootstrapError(
            "Bootstrap ingest did not queue a new run for processing."
        )
    return str(response.document_id), str(response.run_id)


def _process_bootstrap_run(
    session: Session,
    *,
    expected_run_id: str,
    storage_service: StorageService,
    parser: DoclingParser,
) -> tuple[Document, DocumentRun]:
    run = claim_next_run(session, DEFAULT_WORKER_ID)
    if run is None:
        raise RegressionReadinessBootstrapError("Bootstrap run was not available for worker claim.")
    if str(run.id) != expected_run_id:
        raise RegressionReadinessBootstrapError(
            "Bootstrap claimed an unexpected run. "
            f"Expected {expected_run_id}, claimed {run.id}."
        )
    process_run(
        session=session,
        run_id=run.id,
        storage_service=storage_service,
        parser=parser,
        embedding_provider=None,
    )
    session.expire_all()
    persisted_run = session.get(DocumentRun, run.id)
    if persisted_run is None:
        raise RegressionReadinessBootstrapError(f"Processed run vanished: {run.id}")
    document = session.get(Document, persisted_run.document_id)
    if document is None:
        raise RegressionReadinessBootstrapError(
            f"Processed document vanished for run: {persisted_run.id}"
        )
    if persisted_run.status != "completed":
        raise RegressionReadinessBootstrapError(
            f"Bootstrap run did not complete successfully: status={persisted_run.status}"
        )
    if document.active_run_id != persisted_run.id:
        raise RegressionReadinessBootstrapError(
            "Bootstrap run completed but was not promoted as the active document run."
        )
    return document, persisted_run


def _manual_evaluation_payload(evaluation: DocumentRunEvaluation) -> dict[str, Any]:
    return {
        "evaluation_id": str(evaluation.id),
        "status": evaluation.status,
        "fixture_name": evaluation.fixture_name,
        "summary": evaluation.summary_json,
        "error_message": evaluation.error_message,
    }


def _run_replay_suites(
    session: Session,
    *,
    replay_limit: int,
) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for source_type in DEFAULT_REPLAY_SOURCE_TYPES:
        replay = run_search_replay_suite(
            session,
            SearchReplayRunRequest(
                source_type=source_type,
                limit=replay_limit,
            ),
        )
        session.commit()
        replay_payload = replay.model_dump(mode="json")
        payloads[source_type] = replay_payload
        if replay_payload.get("status") != "completed":
            raise RegressionReadinessBootstrapError(
                f"Replay suite {source_type} did not complete successfully."
            )
    return payloads


def bootstrap_regression_readiness(
    session: Session,
    *,
    storage_service: StorageService,
    parser: DoclingParser | None = None,
    bootstrap_document_path: Path = DEFAULT_BOOTSTRAP_DOCUMENT_PATH,
    manual_corpus_path: Path = DEFAULT_MANUAL_CORPUS_PATH,
    auto_corpus_seed_path: Path = DEFAULT_AUTO_CORPUS_SEED_PATH,
    auto_corpus_path: Path | None = None,
    output_path: Path | None = None,
    live_gap_query: str = DEFAULT_LIVE_GAP_QUERY,
    replay_limit: int = DEFAULT_REPLAY_LIMIT,
) -> dict[str, Any]:
    bootstrap_document_path = resolve_existing_bootstrap_path(
        bootstrap_document_path,
        error_cls=RegressionReadinessBootstrapError,
    )
    manual_corpus_path = resolve_existing_bootstrap_path(
        manual_corpus_path,
        error_cls=RegressionReadinessBootstrapError,
    )
    auto_corpus_seed_path = resolve_existing_bootstrap_path(
        auto_corpus_seed_path,
        error_cls=RegressionReadinessBootstrapError,
    )
    auto_corpus_path = _resolve_auto_corpus_path(auto_corpus_path, storage_service=storage_service)
    output_path = resolve_readiness_output_path(
        output_path,
        storage_service=storage_service,
        default_filename=READINESS_REPORT_FILENAME,
    )
    parser = parser or DoclingParser()

    _assert_empty_bootstrap_state(session)
    _install_auto_corpus_seed(seed_path=auto_corpus_seed_path, target_path=auto_corpus_path)
    live_gap_request_id = _seed_live_gap_query(session, query_text=live_gap_query)
    document_id, run_id = _queue_bootstrap_document(
        session,
        bootstrap_document_path=bootstrap_document_path,
        storage_service=storage_service,
    )
    document, run = _process_bootstrap_run(
        session,
        expected_run_id=run_id,
        storage_service=storage_service,
        parser=parser,
    )
    manual_evaluation = evaluate_run(
        session,
        document,
        run,
        corpus_path=manual_corpus_path,
        corpus_name="regression_bootstrap_manual",
        refresh_auto_fixture=False,
    )
    if manual_evaluation.status != "completed":
        raise RegressionReadinessBootstrapError(
            "Manual bootstrap evaluation did not complete successfully: "
            f"status={manual_evaluation.status}"
        )
    replay_runs = _run_replay_suites(session, replay_limit=replay_limit)
    readiness = build_evaluation_data_readiness_report(
        session,
        manual_corpus_path=manual_corpus_path,
        auto_corpus_path=auto_corpus_path,
    )
    rendered_readiness = json.dumps(readiness, indent=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered_readiness + "\n")
    if not readiness["summary"]["regression_ready"]:
        raise RegressionReadinessBootstrapError(
            "Regression-readiness bootstrap completed but the readiness gate is still red: "
            f"{readiness['summary']['regression_blockers']}"
        )
    return {
        "schema_name": "regression_readiness_bootstrap_result",
        "bootstrap_document_path": str(bootstrap_document_path),
        "manual_corpus_path": str(manual_corpus_path),
        "auto_corpus_seed_path": str(auto_corpus_seed_path),
        "auto_corpus_path": str(auto_corpus_path),
        "readiness_output_path": str(output_path),
        "document_id": document_id,
        "run_id": run_id,
        "source_filename": document.source_filename,
        "seeded_live_gap_query": live_gap_query,
        "seeded_live_gap_request_id": live_gap_request_id,
        "manual_evaluation": _manual_evaluation_payload(manual_evaluation),
        "replay_runs": replay_runs,
        "readiness": readiness,
    }
