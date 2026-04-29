from __future__ import annotations

import structlog

from app.services.embeddings import get_embedding_provider
from app.services.evaluations import load_evaluation_fixtures

logger = structlog.get_logger(__name__)


def _semantic_query_texts() -> list[str]:
    texts = [
        str(case.query)
        for fixture in load_evaluation_fixtures()
        for case in fixture.queries
        if str(case.mode or "").lower() != "keyword"
    ]
    return list(dict.fromkeys(text for text in texts if text))


def prewarm_eval_corpus_query_embeddings() -> dict:
    query_texts = _semantic_query_texts()
    if not query_texts:
        return {"status": "skipped", "query_count": 0}
    try:
        provider = get_embedding_provider()
        provider.embed_texts(query_texts)
    except Exception as exc:
        logger.warning(
            "evaluation_query_embedding_prewarm_failed",
            query_count=len(query_texts),
            error=str(exc),
        )
        return {"status": "failed", "query_count": len(query_texts), "error": str(exc)}
    return {"status": "completed", "query_count": len(query_texts)}
