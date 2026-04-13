from __future__ import annotations

from uuid import uuid4

from app.db.models import SearchRequestRecord, SearchRequestResult
from app.schemas.search import SearchFilters, SearchRequest
from app.services.search import (
    RankedResult,
    _classify_query_intent,
    _is_tabular_query,
    _merge_hybrid_results,
    execute_search,
    search_documents,
)


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

    results = _merge_hybrid_results(
        [keyword_item], [semantic_item], limit=5, filters=None, tabular_query=False
    )

    assert len(results) == 1
    assert results[0].scores.keyword_score == 0.8
    assert results[0].scores.semantic_score == 0.9
    assert results[0].scores.hybrid_score is not None


def test_merge_hybrid_results_keeps_distinct_chunks() -> None:
    keyword_item = _ranked_chunk()
    keyword_item.keyword_score = 0.6
    semantic_item = _ranked_chunk()
    semantic_item.semantic_score = 0.7

    results = _merge_hybrid_results(
        [keyword_item], [semantic_item], limit=5, filters=None, tabular_query=False
    )

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


def test_classify_query_intent_distinguishes_tabular_lookup_and_broad() -> None:
    assert _classify_query_intent("TABLE 701.2") == "tabular"
    assert (
        _classify_query_intent("What is the main claim of The Bitter Lesson?")
        == "prose_lookup"
    )
    assert (
        _classify_query_intent(
            "Summarize the major themes across the wildlife report and explain how they connect."
        )
        == "prose_broad"
    )


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

    results = search_documents(
        session=None, request=SearchRequest(query="table 701.2", mode="keyword", limit=5)
    )
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

    results = search_documents(
        session=None, request=SearchRequest(query="hangers and supports", mode="keyword", limit=5)
    )
    assert results[0].result_type == "table"


def test_prose_query_prefers_document_with_source_title_overlap(monkeypatch) -> None:
    bitter_lesson_document_id = uuid4()

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="UPC_CH_5.pdf",
                document_title="Uniform Plumbing Code Chapter 5",
                page_from=5,
                page_to=5,
                chunk_text="Some unrelated main claim language.",
                heading="UPC",
                keyword_score=0.8,
            ),
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=bitter_lesson_document_id,
                run_id=uuid4(),
                source_filename="The Bitter Lesson.pdf",
                document_title="The Bitter Lesson",
                page_from=2,
                page_to=2,
                chunk_text=(
                    "General methods that leverage computation are ultimately "
                    "the most effective."
                ),
                heading="The Bitter Lesson",
                keyword_score=0.8,
            ),
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [],
    )

    results = search_documents(
        session=None,
        request=SearchRequest(
            query="What is the main claim of The Bitter Lesson?",
            mode="keyword",
            limit=5,
        ),
    )

    assert results[0].document_id == bitter_lesson_document_id
    assert results[0].source_filename == "The Bitter Lesson.pdf"


def test_prose_query_cluster_strength_prefers_document_with_multiple_hits(monkeypatch) -> None:
    clustered_document_id = uuid4()
    singleton_document_id = uuid4()

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=singleton_document_id,
                run_id=uuid4(),
                source_filename="other-essay.pdf",
                document_title="Another Essay",
                page_from=1,
                page_to=1,
                chunk_text="Search and learning require iteration.",
                heading="Essay",
                keyword_score=0.61,
            ),
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=clustered_document_id,
                run_id=uuid4(),
                source_filename="essay-a.pdf",
                document_title="Essay A",
                page_from=2,
                page_to=2,
                chunk_text="Search and learning require scale.",
                heading="Essay A",
                keyword_score=0.60,
            ),
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=clustered_document_id,
                run_id=uuid4(),
                source_filename="essay-a.pdf",
                document_title="Essay A",
                page_from=3,
                page_to=3,
                chunk_text="Learning systems improve with more experience.",
                heading="Essay A",
                keyword_score=0.59,
            ),
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [],
    )

    results = search_documents(
        session=None,
        request=SearchRequest(query="search and learning", mode="keyword", limit=5),
    )

    assert results[0].document_id == clustered_document_id


def test_result_type_filter_limits_results(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [],
    )
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
        request=SearchRequest(
            query="table", mode="keyword", limit=5, filters=SearchFilters(result_type="table")
        ),
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
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search.get_embedding_provider",
        lambda: (_ for _ in ()).throw(RuntimeError("no embeddings")),
    )

    results = search_documents(
        session=None, request=SearchRequest(query="fallback", mode="semantic", limit=5)
    )

    assert len(results) == 1
    assert results[0].result_type == "chunk"
    assert results[0].chunk_id == chunk_id


def test_search_documents_passes_explicit_run_scope(monkeypatch) -> None:
    scoped_run_id = uuid4()
    observed: dict[str, object] = {}

    def fake_chunk_search(session, request, candidate_limit=None, *, run_id=None):
        observed["chunk_run_id"] = run_id
        return []

    def fake_table_search(session, request, candidate_limit=None, *, run_id=None):
        observed["table_run_id"] = run_id
        return []

    monkeypatch.setattr("app.services.search._run_keyword_chunk_search", fake_chunk_search)
    monkeypatch.setattr("app.services.search._run_keyword_table_search", fake_table_search)

    results = search_documents(
        session=None,
        request=SearchRequest(query="scoped", mode="keyword", limit=5),
        run_id=scoped_run_id,
    )

    assert results == []
    assert observed["chunk_run_id"] == scoped_run_id
    assert observed["table_run_id"] == scoped_run_id


def test_execute_search_persists_request_and_result_snapshots(monkeypatch) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value) -> None:
            self.added.append(value)

        def flush(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="doc.pdf",
                page_from=3,
                page_to=3,
                chunk_text="vent stack content",
                heading="Venting",
                keyword_score=0.6,
            )
        ],
    )
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
                table_heading="Vent stack sizes",
                table_preview="Diameter | Height",
                row_count=2,
                col_count=2,
                keyword_score=0.7,
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search.observe_search_results",
        lambda table_hits, mixed_request: None,
    )

    session = FakeSession()
    execution = execute_search(
        session,
        SearchRequest(query="table 1", mode="keyword", limit=5),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]
    result_rows = [row for row in session.added if isinstance(row, SearchRequestResult)]

    assert execution.request_id is not None
    assert execution.harness_name == "default_v1"
    assert execution.reranker_name == "linear_feature_reranker"
    assert execution.reranker_version == "v1"
    assert execution.retrieval_profile_name == "default_v1"
    assert request_rows[0].origin == "api"
    assert request_rows[0].tabular_query is True
    assert request_rows[0].details_json["served_mode"] == "keyword"
    assert result_rows[0].rerank_features_json["final_score"] >= result_rows[0].score
    assert "source_filename_token_coverage" in result_rows[0].rerank_features_json
    assert "document_title_token_coverage" in result_rows[0].rerank_features_json
    assert "document_cluster_strength" in result_rows[0].rerank_features_json


def test_execute_search_falls_back_to_relaxed_keyword_matching(monkeypatch) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value) -> None:
            self.added.append(value)

        def flush(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_chunk_search",
        lambda session, request, candidate_limit=None, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="essay.pdf",
                page_from=1,
                page_to=1,
                chunk_text=(
                    "General methods that leverage computation are ultimately the most "
                    "effective."
                ),
                heading=None,
                keyword_score=0.4,
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_table_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search.observe_search_results",
        lambda table_hits, mixed_request: None,
    )

    session = FakeSession()
    execution = execute_search(
        session,
        SearchRequest(
            query="What is the main claim of The Bitter Lesson?",
            mode="keyword",
            limit=5,
        ),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]

    assert len(execution.results) == 1
    assert execution.results[0].result_type == "chunk"
    assert request_rows[0].details_json["keyword_strategy"] == "relaxed_or"
    assert request_rows[0].details_json["keyword_strict_candidate_count"] == 0
    assert request_rows[0].details_json["keyword_candidate_count"] == 1


def test_execute_search_prose_v3_persists_query_intent_and_candidate_breakdown(monkeypatch) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value) -> None:
            self.added.append(value)

        def flush(self) -> None:
            return None

    source_document_id = uuid4()
    source_run_id = uuid4()
    seed_chunk_id = uuid4()
    metadata_chunk_id = uuid4()
    adjacent_chunk_id = uuid4()
    semantic_chunk_id = uuid4()

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=seed_chunk_id,
                document_id=source_document_id,
                run_id=source_run_id,
                source_filename="The Bitter Lesson.pdf",
                document_title="The Bitter Lesson",
                page_from=2,
                page_to=2,
                chunk_index=1,
                chunk_text="General methods that leverage computation keep winning.",
                heading="The Bitter Lesson",
                keyword_score=0.7,
                retrieval_sources=("keyword_primary",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="table",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="UPC_CH_5.pdf",
                page_from=5,
                page_to=5,
                table_title="TABLE 5",
                table_heading="Unrelated",
                table_preview="preview",
                row_count=1,
                col_count=1,
                keyword_score=0.69,
                retrieval_sources=("keyword_primary",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_prose_metadata_chunk_search",
        lambda session, request, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=metadata_chunk_id,
                document_id=source_document_id,
                run_id=source_run_id,
                source_filename="The Bitter Lesson.pdf",
                document_title="The Bitter Lesson",
                page_from=1,
                page_to=1,
                chunk_index=0,
                chunk_text="Metadata match",
                heading="Introduction",
                keyword_score=0.5,
                retrieval_sources=("metadata_supplement",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._expand_adjacent_chunk_context",
        lambda session, request, seed_candidates, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=adjacent_chunk_id,
                document_id=source_document_id,
                run_id=source_run_id,
                source_filename="The Bitter Lesson.pdf",
                document_title="The Bitter Lesson",
                page_from=3,
                page_to=3,
                chunk_index=2,
                chunk_text="Adjacent context",
                heading="Discussion",
                keyword_score=0.45,
                retrieval_sources=("adjacent_context",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_chunk_search",
        lambda session, request, query_embedding, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=semantic_chunk_id,
                document_id=source_document_id,
                run_id=source_run_id,
                source_filename="The Bitter Lesson.pdf",
                document_title="The Bitter Lesson",
                page_from=4,
                page_to=4,
                chunk_index=3,
                chunk_text="Semantic match",
                heading="Conclusion",
                semantic_score=0.8,
                retrieval_sources=("semantic_primary",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_table_search",
        lambda session, request, query_embedding, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search.get_embedding_provider",
        lambda: type("FakeProvider", (), {"embed_texts": lambda self, texts: [[0.1, 0.2]]})(),
    )
    monkeypatch.setattr(
        "app.services.search.observe_search_results",
        lambda table_hits, mixed_request: None,
    )

    session = FakeSession()
    execution = execute_search(
        session,
        SearchRequest(
            query="What is the main claim of The Bitter Lesson?",
            mode="semantic",
            limit=5,
            harness_name="prose_v3",
        ),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]
    result_rows = [row for row in session.added if isinstance(row, SearchRequestResult)]

    assert execution.details["query_intent"] == "prose_lookup"
    assert execution.details["semantic_augmented_with_keyword_context"] is True
    assert execution.details["candidate_source_breakdown"]["keyword_primary"] == 2
    assert execution.details["candidate_source_breakdown"]["metadata_supplement"] == 1
    assert execution.details["candidate_source_breakdown"]["adjacent_context"] == 1
    assert execution.details["candidate_source_breakdown"]["semantic_primary"] == 1
    assert execution.details["metadata_candidate_count"] == 1
    assert execution.details["context_expansion_count"] == 1
    assert request_rows[0].details_json["query_intent"] == "prose_lookup"
    assert request_rows[0].details_json["candidate_source_breakdown"]["metadata_supplement"] == 1
    assert "heading_token_coverage" in result_rows[0].rerank_features_json
    assert "phrase_overlap" in result_rows[0].rerank_features_json
    assert "rare_token_overlap" in result_rows[0].rerank_features_json
    assert "adjacent_chunk_context_signal" in result_rows[0].rerank_features_json
