from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.db.models import (
    SearchRequestRecord,
)
from app.schemas.search import SearchFilters, SearchRequest
from app.services.search import (
    RankedResult,
    _merge_hybrid_results,
    _table_title_match_features,
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


def test_table_title_match_features_use_table_heading_when_title_is_generic() -> None:
    item = RankedResult(
        result_type="table",
        result_id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        source_filename="doc.pdf",
        page_from=1,
        page_to=2,
        table_title="Table 1 (Con.)",
        table_heading="Forest habitat types and Abies lasiocarpa/Streptopus amplexifolius h.t",
        table_preview="Habitat type | Species",
        row_count=2,
        col_count=2,
    )

    features = _table_title_match_features(
        item,
        "Forest habitat types and Abies lasiocarpa/Streptopus amplexifolius h.t",
    )

    assert features["title_token_coverage"] > 0.0


def test_filtered_hybrid_query_keeps_table_ahead_of_filename_only_metadata_chunks(
    monkeypatch,
) -> None:
    table_document_id = uuid4()

    class FakeEmbeddingProvider:
        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            return [[0.1, 0.2, 0.3] for _ in texts]

    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value) -> None:
            self.added.append(value)

        def execute(self, _statement):
            return SimpleNamespace(
                all=lambda: [
                    (
                        SimpleNamespace(
                            id=uuid4(),
                            document_id=table_document_id,
                            run_id=uuid4(),
                            page_from=1,
                            page_to=1,
                            chunk_index=0,
                            text="General narrative overview.",
                            heading=None,
                        ),
                        SimpleNamespace(
                            source_filename="CooperEtAl_1991_ForestHabitatNIDSecondApproximation.pdf",
                            title="Forest habitat types for northern Idaho",
                        ),
                    )
                ]
            )

        def flush(self) -> None:
            return None

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
                document_id=table_document_id,
                run_id=uuid4(),
                source_filename="CooperEtAl_1991_ForestHabitatNIDSecondApproximation.pdf",
                document_title="Forest habitat types for northern Idaho",
                page_from=2,
                page_to=2,
                table_title="Table 1",
                table_heading=(
                    "Forest habitat types and Abies lasiocarpa/Streptopus amplexifolius h.t"
                ),
                table_preview="Habitat type | Species",
                row_count=2,
                col_count=2,
                keyword_score=0.02,
                retrieval_sources=("keyword_primary",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_chunk_search",
        lambda session, request, query_embedding, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_table_search",
        lambda session, request, query_embedding, candidate_limit=None, run_id=None: [
            RankedResult(
                result_type="table",
                result_id=uuid4(),
                document_id=table_document_id,
                run_id=uuid4(),
                source_filename="CooperEtAl_1991_ForestHabitatNIDSecondApproximation.pdf",
                document_title="Forest habitat types for northern Idaho",
                page_from=2,
                page_to=2,
                table_title="Table 1",
                table_heading=(
                    "Forest habitat types and Abies lasiocarpa/Streptopus amplexifolius h.t"
                ),
                table_preview="Habitat type | Species",
                row_count=2,
                col_count=2,
                semantic_score=0.7,
                retrieval_sources=("semantic_primary",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search.get_embedding_provider", lambda: FakeEmbeddingProvider()
    )
    monkeypatch.setattr(
        "app.services.search.observe_search_results",
        lambda table_hits, mixed_request: None,
    )

    execution = execute_search(
        FakeSession(),
        SearchRequest(
            query="Forest habitat types and Abies lasiocarpa/Streptopus amplexifolius h.t",
            mode="hybrid",
            limit=5,
            filters=SearchFilters(document_id=table_document_id),
        ),
        origin="test",
    )

    assert execution.results[0].result_type == "table"


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
                    "General methods that leverage computation are ultimately the most effective."
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


def test_prose_query_exact_source_filename_match_outranks_noisy_relaxed_table(monkeypatch) -> None:
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
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_table_search",
        lambda session, request, candidate_limit=None, run_id=None: [
            RankedResult(
                result_type="table",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="J2-08_10222025_TK_TSMRSFireGroup.pdf",
                page_from=4,
                page_to=4,
                table_title="A750400020 4.47 4 16 A740100012 28.9 30 16",
                table_heading=None,
                table_preview="noisy numeric table",
                row_count=5,
                col_count=5,
                keyword_score=7.7,
                retrieval_sources=("keyword_relaxed",),
            ),
            RankedResult(
                result_type="table",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="Consolidated BPA MOU 5-1-18.pdf",
                page_from=12,
                page_to=12,
                table_title="FEDERAL HOLDER ACTIVITIES AND PROJECTS",
                table_heading=None,
                table_preview="holder activities by year",
                row_count=8,
                col_count=4,
                keyword_score=4.3,
                retrieval_sources=("keyword_relaxed",),
            ),
        ],
    )

    results = search_documents(
        session=None,
        request=SearchRequest(
            query="Consolidated BPA MOU 5-1-18",
            mode="keyword",
            limit=5,
            harness_name="wide_v2",
        ),
    )

    assert results[0].source_filename == "Consolidated BPA MOU 5-1-18.pdf"


def test_execute_search_uses_camel_case_source_filename_exact_match(monkeypatch) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value) -> None:
            self.added.append(value)

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [])

        def flush(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_chunk_search",
        lambda session, request, candidate_limit=None, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="J3-12_12032025_TK_OverviewMaps.pdf",
                document_title="Overview Maps",
                page_from=6,
                page_to=6,
                chunk_index=6,
                chunk_text="Map label",
                heading="Babcock",
                keyword_score=0.9,
                retrieval_sources=("keyword_relaxed",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_table_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_prose_metadata_chunk_search",
        lambda session, request, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="BabcockLEX.pdf",
                document_title=(
                    "Chapter 1: National Forest Land Exchanges and Land Grant Timber Companies"
                ),
                page_from=1,
                page_to=1,
                chunk_index=0,
                chunk_text="Critical look at land exchanges as viable solutions.",
                heading=None,
                keyword_score=0.2,
                retrieval_sources=("metadata_supplement",),
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
        SearchRequest(query="Babcock LEX", mode="keyword", limit=5, harness_name="prose_v3"),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]

    assert execution.results[0].source_filename == "BabcockLEX.pdf"
    assert request_rows[0].details_json["keyword_strategy"] == "relaxed_or_plus_metadata"
