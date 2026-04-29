from __future__ import annotations

from app.db.models import Document, DocumentRun
from app.db.session import get_session_factory
from app.services.evaluation_embedding_cache import prewarm_eval_corpus_query_embeddings
from app.services.evaluations import evaluate_run


def run_eval_corpus_summary() -> list[dict]:
    session_factory = get_session_factory()
    summaries: list[dict] = []
    prewarm_eval_corpus_query_embeddings()
    with session_factory() as session:
        documents = session.query(Document).order_by(Document.updated_at.desc()).all()
        for document in documents:
            if document.active_run_id is None:
                continue
            run = session.get(DocumentRun, document.active_run_id)
            if run is None:
                continue
            evaluation = evaluate_run(session, document, run, refresh_auto_fixture=False)
            summaries.append(
                {
                    "run_id": str(run.id),
                    "document_id": str(document.id),
                    "source_filename": document.source_filename,
                    "status": evaluation.status,
                    "fixture_name": evaluation.fixture_name,
                    "summary": evaluation.summary_json,
                }
            )
    return summaries
