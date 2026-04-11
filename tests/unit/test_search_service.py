from __future__ import annotations

from uuid import uuid4

from app.schemas.search import SearchFilters, SearchRequest
from app.services.search import RankedResult, _is_tabular_query, _merge_hybrid_results, search_documents


def _ranked_chunk() -> RankedResult:
    return RankedResult(
        result_type="chunk",
        result_id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        source_filename="report.pdf",
        page_from=1,
        page_to=1,
        chunk_text="chunk text",
        heading="Heading",
    )


def test_merge_hybrid_results_combines_scores() -> None:
    keyword_item = _ranked_chunk()
    semantic_item = RankedResult(**keyword_item.__dict__)
    keyword_item.keyword_score = 0.8
    semantic_item.semantic_score = 0.9

    results = _merge_hybrid_results([keyword_item], [semantic_item], limit=5, filters=None, tabular_query=False)

    assert len(results) == 1
    assert results[0].scores.keyword_score == 0.8
    assert results[0].scores.semantic_score == 0.9
    assert results[0].scores.hybrid_score is not None


def test_merge_hybrid_results_keeps_distinct_chunks() -> None:
    keyword_item = _ranked_chunk()
    keyword_item.keyword_score = 0.6
    semantic_item = _ranked_chunk()
    semantic_item.semantic_score = 0.7

    results = _merge_hybrid_results([keyword_item], [semantic_item], limit=5, filters=None, tabular_query=False)

    assert len(results) == 2


def test_merge_hybrid_results_supports_tables() -> None:
    table_item = RankedResult(
        result_type="table",
        result_id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        source_filename="report.pdf",
        page_from=2,
        page_to=3,
        table_title="TABLE 1",
        table_heading="701.2 Drainage Piping",
        table_preview="Fixture | DFU",
        row_count=10,
        col_count=2,
    )
    table_item.keyword_score = 0.7

    results = _merge_hybrid_results([table_item], [], limit=5, filters=None, tabular_query=True)

    assert results[0].result_type == "table"
    assert results[0].table_title == "TABLE 1"


def test_is_tabular_query_matches_table_reference() -> None:
    assert _is_tabular_query("TABLE 701.2")
    assert _is_tabular_query("row and column limits")


def test_tabular_query_boost_keeps_table_first(monkeypatch) -> None:
    table_id = uuid4()
    chunk_id = uuid4()

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=chunk_id,
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="doc.pdf",
                page_from=5,
                page_to=5,
                chunk_text="table values",
                heading="Heading",
                keyword_score=1.0,
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="table",
                result_id=table_id,
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="doc.pdf",
                page_from=2,
                page_to=2,
                table_title="TABLE 701.2",
                table_heading="Heading",
                table_preview="preview",
                row_count=2,
                col_count=2,
                keyword_score=1.0,
            )
        ],
    )

    results = search_documents(session=None, request=SearchRequest(query="table 701.2", mode="keyword", limit=5))
    assert results[0].result_type == "table"


def test_table_title_match_boost_keeps_table_first_for_title_query(monkeypatch) -> None:
    table_id = uuid4()
    chunk_id = uuid4()

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=chunk_id,
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="doc.pdf",
                page_from=5,
                page_to=5,
                chunk_text="TABLE 313.3 HANGERS AND SUPPORTS",
                heading="313.2 Material",
                keyword_score=0.03,
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="table",
                result_id=table_id,
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="doc.pdf",
                page_from=35,
                page_to=36,
                table_title="TABLE 313.3 HANGERS AND SUPPORTS",
                table_heading="313.2 Material",
                table_preview="Material | Horizontal | Vertical",
                row_count=17,
                col_count=5,
                keyword_score=0.02,
            )
        ],
    )

    results = search_documents(session=None, request=SearchRequest(query="hangers and supports", mode="keyword", limit=5))
    assert results[0].result_type == "table"


def test_result_type_filter_limits_results(monkeypatch) -> None:
    monkeypatch.setattr("app.services.search._run_keyword_chunk_search", lambda session, request, candidate_limit=None: [])
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="table",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="doc.pdf",
                page_from=2,
                page_to=2,
                table_title="TABLE 1",
                table_heading="Heading",
                table_preview="preview",
                row_count=2,
                col_count=2,
                keyword_score=0.8,
            )
        ],
    )

    results = search_documents(
        session=None,
        request=SearchRequest(query="table", mode="keyword", limit=5, filters=SearchFilters(result_type="table")),
    )
    assert all(result.result_type == "table" for result in results)


def test_semantic_mode_falls_back_to_keyword_when_embeddings_unavailable(monkeypatch) -> None:
    chunk_id = uuid4()
    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=chunk_id,
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="doc.pdf",
                page_from=1,
                page_to=1,
                chunk_text="fallback text",
                heading="Heading",
                keyword_score=0.9,
            )
        ],
    )
    monkeypatch.setattr("app.services.search._run_keyword_table_search", lambda session, request, candidate_limit=None: [])
    monkeypatch.setattr("app.services.search.get_embedding_provider", lambda: (_ for _ in ()).throw(RuntimeError("no embeddings")))

    results = search_documents(session=None, request=SearchRequest(query="fallback", mode="semantic", limit=5))

    assert len(results) == 1
    assert results[0].result_type == "chunk"
    assert results[0].chunk_id == chunk_id
