from __future__ import annotations

from sqlalchemy.orm import Session

import app.services.evaluation_fixture_auto_generation as auto_generation_owners
import app.services.evaluation_fixtures as fixture_owners
from app.db.public.ingest import Document, DocumentRun
from app.schemas.search import SearchFilters, SearchRequest


def _filter_retrieval_backed_auto_queries(
    session: Session,
    document: Document,
    run: DocumentRun,
    entries: list[dict[str, object]],
    *,
    expected_result_type: str,
) -> list[dict[str, object]]:
    supported: list[tuple[int, int, dict[str, object]]] = []
    for index, entry in enumerate(entries):
        request = SearchRequest(
            query=str(entry["query"]),
            mode=str(entry.get("mode", "hybrid")),
            filters=SearchFilters(document_id=document.id),
            limit=max(int(entry.get("top_n", auto_generation_owners.AUTO_QUERY_TOP_N)), 10),
        )
        results = fixture_owners.search_documents(
            session,
            request,
            run_id=run.id,
            origin="auto_fixture_generation",
        )
        rank = fixture_owners._matching_rank(
            results,
            expected_result_type,
            expected_source_filename=document.source_filename,
        )
        if rank is None or rank > int(entry.get("top_n", auto_generation_owners.AUTO_QUERY_TOP_N)):
            continue
        supported.append((rank, index, dict(entry)))

    supported.sort(key=lambda item: (item[0], item[1]))
    return [entry for _, _, entry in supported]


def _materialize_retrieval_backed_auto_fixture(
    session: Session,
    document: Document,
    run: DocumentRun,
    fixture_document: dict,
) -> dict:
    thresholds = dict(fixture_document.get("thresholds", {}))
    thresholds["expected_top_n_table_hit_queries"] = _filter_retrieval_backed_auto_queries(
        session,
        document,
        run,
        list(thresholds.get("expected_top_n_table_hit_queries", [])),
        expected_result_type="table",
    )
    thresholds["expected_top_n_chunk_hit_queries"] = _filter_retrieval_backed_auto_queries(
        session,
        document,
        run,
        list(thresholds.get("expected_top_n_chunk_hit_queries", [])),
        expected_result_type="chunk",
    )
    return {**fixture_document, "thresholds": thresholds}
