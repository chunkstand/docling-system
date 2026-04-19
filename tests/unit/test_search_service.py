from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.db.models import Document, SearchRequestRecord, SearchRequestResult
from app.schemas.search import SearchFilters, SearchRequest
from app.services.search import (
    RankedResult,
    _build_query_feature_set,
    _classify_query_intent,
    _is_tabular_query,
    _looks_like_identifier_lookup,
    _merge_hybrid_results,
    _ranked_metadata_overlap_score,
    _run_prose_metadata_chunk_search,
    _should_run_metadata_supplement,
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


def test_is_tabular_query_matches_table_reference() -> None:
    assert _is_tabular_query("TABLE 701.2")
    assert _is_tabular_query("701.2 drainage piping")
    assert _is_tabular_query("row and column limits")


def test_is_tabular_query_does_not_treat_identifier_like_filename_as_tabular() -> None:
    assert _is_tabular_query("fseprd1091222") is False


def test_classify_query_intent_distinguishes_tabular_lookup_and_broad() -> None:
    assert _classify_query_intent("TABLE 701.2") == "tabular"
    assert _classify_query_intent("What is the main claim of The Bitter Lesson?") == "prose_lookup"
    assert (
        _classify_query_intent(
            "Summarize the major themes across the wildlife report and explain how they connect."
        )
        == "prose_broad"
    )


def test_identifier_lookup_detection_matches_filename_like_queries() -> None:
    assert _looks_like_identifier_lookup("fseprd1091222") is True
    assert _looks_like_identifier_lookup("fseprd1091222.pdf") is True
    assert _looks_like_identifier_lookup("Consolidated BPA MOU 5-1-18") is False
    assert _looks_like_identifier_lookup("What is the main claim of The Bitter Lesson?") is False


def test_metadata_supplement_runs_for_prose_v3_and_identifier_zero_result_queries() -> None:
    assert (
        _should_run_metadata_supplement(
            query="What is the main claim of The Bitter Lesson?",
            query_intent="prose_broad",
            strict_keyword_count=5,
            harness_name="prose_v3",
        )
        is True
    )
    assert (
        _should_run_metadata_supplement(
            query="fseprd1091222",
            query_intent="prose_lookup",
            strict_keyword_count=0,
            harness_name="default_v1",
        )
        is True
    )
    assert (
        _should_run_metadata_supplement(
            query="what does appendix h alternative costs show",
            query_intent="prose_broad",
            strict_keyword_count=0,
            harness_name="default_v1",
        )
        is False
    )
    assert (
        _should_run_metadata_supplement(
            query="TABLE 701.2",
            query_intent="tabular",
            strict_keyword_count=1,
            harness_name="prose_v3",
        )
        is False
    )


def test_ranked_metadata_overlap_score_uses_chunk_text_signal() -> None:
    score_without_chunk = _ranked_metadata_overlap_score(
        "dear interested party chalk buttes",
        document_title="Chalk Buttes Cover Letter",
        heading=None,
        chunk_text=None,
        source_filename="Chalk Buttes Cover Letter.pdf",
    )
    score_with_chunk = _ranked_metadata_overlap_score(
        "dear interested party chalk buttes",
        document_title="Chalk Buttes Cover Letter",
        heading=None,
        chunk_text="Dear Interested Party,",
        source_filename="Chalk Buttes Cover Letter.pdf",
    )

    assert score_with_chunk > score_without_chunk


def test_ranked_metadata_overlap_score_ignores_filename_when_document_scoped() -> None:
    with_document_context = _ranked_metadata_overlap_score(
        "forest habitat types and abies lasiocarpa streptopus amplexifolius",
        document_title="Forest habitat types for northern Idaho",
        heading=None,
        chunk_text=None,
        source_filename="CooperEtAl_1991_ForestHabitatNIDSecondApproximation.pdf",
    )
    scoped_to_document = _ranked_metadata_overlap_score(
        "forest habitat types and abies lasiocarpa streptopus amplexifolius",
        document_title="Forest habitat types for northern Idaho",
        heading=None,
        chunk_text=None,
        source_filename="CooperEtAl_1991_ForestHabitatNIDSecondApproximation.pdf",
        include_document_context=False,
    )

    assert scoped_to_document < with_document_context
    assert scoped_to_document == 0.0


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


def test_table_title_match_features_accept_precomputed_query_features() -> None:
    item = RankedResult(
        result_type="table",
        result_id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        source_filename="doc.pdf",
        page_from=1,
        page_to=2,
        table_title="Table 3",
        table_heading="Fixture Unit Loading",
        table_preview="Fixture | Units",
        row_count=2,
        col_count=2,
    )

    features = _table_title_match_features(item, _build_query_feature_set("fixture unit loading"))

    assert features == {"title_exact_match": 1.0, "title_token_coverage": 1.0}


def test_hybrid_search_resorts_metadata_candidates_before_rrf(monkeypatch) -> None:
    winning_document_id = uuid4()
    losing_document_id = uuid4()

    class FakeEmbeddingProvider:
        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            return [[0.1, 0.2, 0.3] for _ in texts]

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
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=losing_document_id,
                run_id=uuid4(),
                source_filename="20260325_ChalkButtes_Hydro.pdf",
                document_title="Chalk Buttes Hydrology",
                page_from=2,
                page_to=2,
                chunk_text="Hydrology design features overview.",
                heading=None,
                keyword_score=0.8,
                retrieval_sources=("keyword",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_prose_metadata_chunk_search",
        lambda session, request, run_id=None, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=winning_document_id,
                run_id=uuid4(),
                source_filename="April 17 2026 Chalk Buttes Billings Gazette Legal Notice.pdf",
                document_title="April 17 2026 Chalk Buttes Billings Gazette Legal Notice",
                page_from=1,
                page_to=1,
                chunk_text="Published in the Billings Gazette on April 17, 2026.",
                heading=None,
                keyword_score=4.6,
                retrieval_sources=("metadata_supplement",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_chunk_search",
        lambda session, request, query_embedding, candidate_limit=None, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=losing_document_id,
                run_id=uuid4(),
                source_filename="20260325_ChalkButtes_Hydro.pdf",
                document_title="Chalk Buttes Hydrology",
                page_from=3,
                page_to=3,
                chunk_text="Hydrology background discussion.",
                heading=None,
                semantic_score=0.92,
                retrieval_sources=("semantic",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_table_search",
        lambda session, request, query_embedding, candidate_limit=None, run_id=None: [],
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
            query="published in billings gazette on april 17 2026 chalk buttes",
            mode="hybrid",
            limit=5,
            harness_name="prose_v3",
        ),
        origin="test",
    )

    assert execution.results[0].document_id == winning_document_id
    assert execution.results[0].source_filename.endswith("Billings Gazette Legal Notice.pdf")


def test_run_prose_metadata_chunk_search_uses_textsearch_queries_without_ilike() -> None:
    winning_document = SimpleNamespace(
        id=uuid4(),
        title="Chalk Buttes Cover Letter",
        source_filename="Chalk Buttes Cover Letter.pdf",
    )
    losing_document = SimpleNamespace(
        id=uuid4(),
        title="Chalk Buttes Silviculture",
        source_filename="20260407_ChalkButtes_Silviculture.pdf",
    )
    winning_chunk = SimpleNamespace(
        id=uuid4(),
        document_id=winning_document.id,
        run_id=uuid4(),
        page_from=1,
        page_to=1,
        chunk_index=0,
        text="Dear Interested Party, the Chalk Buttes project is available for review.",
        heading=None,
    )
    losing_chunk = SimpleNamespace(
        id=uuid4(),
        document_id=losing_document.id,
        run_id=uuid4(),
        page_from=2,
        page_to=2,
        chunk_index=1,
        text="Chalk Buttes silviculture overview.",
        heading=None,
    )

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return list(self._rows)

        def scalars(self):
            return self

    class FakeSession:
        def __init__(self) -> None:
            self.statements: list[str] = []

        def execute(self, statement):
            self.statements.append(str(statement))
            if len(self.statements) == 1:
                return FakeResult([])
            if len(self.statements) == 2:
                return FakeResult([winning_document, losing_document])
            return FakeResult(
                [
                    (winning_chunk, winning_document),
                    (losing_chunk, losing_document),
                ]
            )

    session = FakeSession()
    results = _run_prose_metadata_chunk_search(
        session,
        SearchRequest(query="Chalk Buttes Cover Letter", mode="keyword", limit=5),
    )

    assert results[0].source_filename == "Chalk Buttes Cover Letter.pdf"
    assert any("metadata_textsearch" in statement for statement in session.statements)
    assert any("@@" in statement for statement in session.statements)
    assert all("ILIKE" not in statement.upper() for statement in session.statements)


def test_document_metadata_textsearch_ddl_uses_valid_generated_column_syntax() -> None:
    ddl = str(CreateTable(Document.__table__).compile(dialect=postgresql.dialect()))

    assert "metadata_textsearch TSVECTOR GENERATED ALWAYS AS" in ddl
    assert "STORED NOT NULL" not in ddl


def test_prose_v3_metadata_supplement_prefers_exact_phrase_cover_letter_probe(
    monkeypatch,
) -> None:
    winning_document_id = uuid4()
    losing_document_id = uuid4()

    class FakeEmbeddingProvider:
        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            return [[0.1, 0.2, 0.3] for _ in texts]

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
        "app.services.search._run_prose_metadata_chunk_search",
        lambda session, request, run_id=None, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=winning_document_id,
                run_id=uuid4(),
                source_filename="Chalk Buttes Cover Letter.pdf",
                document_title="Chalk Buttes Cover Letter",
                page_from=1,
                page_to=1,
                chunk_text=(
                    "Dear Interested Party, the Chalk Buttes project is available for review."
                ),
                heading=None,
                keyword_score=6.5,
                retrieval_sources=("metadata_supplement",),
            ),
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=losing_document_id,
                run_id=uuid4(),
                source_filename="20260407_ChalkButtes_Silviculture.pdf",
                document_title="Chalk Buttes Silviculture",
                page_from=2,
                page_to=2,
                chunk_text="Chalk Buttes silviculture overview.",
                heading=None,
                keyword_score=1.1,
                retrieval_sources=("metadata_supplement",),
            ),
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_chunk_search",
        lambda session, request, query_embedding, candidate_limit=None, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=losing_document_id,
                run_id=uuid4(),
                source_filename="20260407_ChalkButtes_Silviculture.pdf",
                document_title="Chalk Buttes Silviculture",
                page_from=3,
                page_to=3,
                chunk_text="Generic Chalk Buttes report language.",
                heading=None,
                semantic_score=0.92,
                retrieval_sources=("semantic",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_table_search",
        lambda session, request, query_embedding, candidate_limit=None, run_id=None: [],
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
            query="dear interested party chalk buttes",
            mode="keyword",
            limit=5,
            harness_name="prose_v3",
        ),
        origin="test",
    )

    assert execution.results[0].document_id == winning_document_id
    assert execution.results[0].source_filename == "Chalk Buttes Cover Letter.pdf"


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

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [])

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

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [])

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
                    "General methods that leverage computation are ultimately the most effective."
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

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [])

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


def test_execute_search_uses_metadata_supplement_as_zero_result_fallback(monkeypatch) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value) -> None:
            self.added.append(value)

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [])

        def flush(self) -> None:
            return None

    document_id = uuid4()
    chunk_id = uuid4()

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
        lambda session, request, candidate_limit=None, run_id=None: [],
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
                result_id=chunk_id,
                document_id=document_id,
                run_id=run_id or uuid4(),
                source_filename="fseprd1091222.pdf",
                document_title="Opaque agency document",
                page_from=1,
                page_to=1,
                chunk_index=0,
                chunk_text="Metadata fallback hit",
                heading="Cover",
                keyword_score=0.9,
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
        SearchRequest(query="fseprd1091222", mode="keyword", limit=5, harness_name="prose_v3"),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]

    assert len(execution.results) == 1
    assert execution.results[0].source_filename == "fseprd1091222.pdf"
    assert request_rows[0].details_json["keyword_strategy"] == "metadata_supplement"
    assert request_rows[0].details_json["candidate_source_breakdown"]["metadata_supplement"] == 1


def test_execute_search_default_v1_uses_metadata_supplement_for_identifier_lookup(
    monkeypatch,
) -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value) -> None:
            self.added.append(value)

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [])

        def flush(self) -> None:
            return None

    document_id = uuid4()
    chunk_id = uuid4()

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
        lambda session, request, candidate_limit=None, run_id=None: [],
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
                result_id=chunk_id,
                document_id=document_id,
                run_id=run_id or uuid4(),
                source_filename="fseprd1091222.pdf",
                document_title="Forest Service",
                page_from=1,
                page_to=1,
                chunk_index=0,
                chunk_text="Metadata fallback hit",
                heading="Cover",
                keyword_score=0.9,
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
        SearchRequest(query="fseprd1091222", mode="keyword", limit=5, harness_name="default_v1"),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]

    assert len(execution.results) == 1
    assert execution.results[0].source_filename == "fseprd1091222.pdf"
    assert request_rows[0].details_json["keyword_strategy"] == "metadata_supplement"
    assert request_rows[0].details_json["candidate_source_breakdown"]["metadata_supplement"] == 1


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


def test_execute_search_adds_metadata_supplement_when_strict_recall_is_sparse(monkeypatch) -> None:
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
        lambda session, request, candidate_limit=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="Consolidated BPA MOU 5-1-18.pdf",
                document_title="MEMORANDUM OF UNDERSTANDING",
                page_from=3,
                page_to=3,
                chunk_index=3,
                chunk_text="Appendix F IFPL waiver language.",
                heading="APPENDIX F IFPL WAIVER",
                keyword_score=0.3,
                retrieval_sources=("keyword_primary",),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_prose_metadata_chunk_search",
        lambda session, request, run_id=None: [
            RankedResult(
                result_type="chunk",
                result_id=uuid4(),
                document_id=uuid4(),
                run_id=uuid4(),
                source_filename="FEIS_Append H_AltCosts.pdf",
                document_title="Appendix H",
                page_from=1,
                page_to=1,
                chunk_index=0,
                chunk_text="Alternative Cost Comparison for the integrated weed management EIS.",
                heading=None,
                keyword_score=0.25,
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
        SearchRequest(
            query="what does appendix h alternative costs show",
            mode="keyword",
            limit=5,
            harness_name="prose_v3",
        ),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]

    assert execution.results[0].source_filename == "FEIS_Append H_AltCosts.pdf"
    assert request_rows[0].details_json["keyword_strategy"] == "strict_plus_metadata"
    assert request_rows[0].details_json["candidate_source_breakdown"]["metadata_supplement"] == 1


def test_execute_search_default_v1_does_not_run_metadata_supplement(monkeypatch) -> None:
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
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_relaxed_keyword_table_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_prose_metadata_chunk_search",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("default_v1 should not invoke metadata supplement")
        ),
    )
    monkeypatch.setattr(
        "app.services.search.observe_search_results",
        lambda table_hits, mixed_request: None,
    )

    session = FakeSession()
    execution = execute_search(
        session,
        SearchRequest(
            query="what does appendix h alternative costs show",
            mode="keyword",
            limit=5,
            harness_name="default_v1",
        ),
        origin="api",
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]

    assert execution.details["metadata_candidate_count"] == 0
    assert (
        request_rows[0].details_json["candidate_source_breakdown"].get("metadata_supplement", 0)
        == 0
    )


def test_execute_search_does_not_rollback_before_persisting_evaluation_request(monkeypatch) -> None:
    class FakeProvider:
        def embed_texts(self, texts):
            assert texts == ["What is the main claim of The Bitter Lesson?"]
            return [[0.1, 0.2, 0.3]]

    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []
            self.rollback_calls = 0

        def add(self, value) -> None:
            self.added.append(value)

        def execute(self, _statement):
            return SimpleNamespace(all=lambda: [])

        def flush(self) -> None:
            return None

        def rollback(self) -> None:
            self.rollback_calls += 1

    keyword_candidate = RankedResult(
        result_type="chunk",
        result_id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        source_filename="The Bitter Lesson.pdf",
        document_title="The Bitter Lesson",
        page_from=1,
        page_to=1,
        chunk_index=0,
        chunk_text="General methods that leverage computation are ultimately the most effective.",
        heading="The Bitter Lesson",
        keyword_score=0.8,
        retrieval_sources=("keyword_primary",),
    )
    semantic_candidate = RankedResult(
        result_type="chunk",
        result_id=uuid4(),
        document_id=keyword_candidate.document_id,
        run_id=keyword_candidate.run_id,
        source_filename="The Bitter Lesson.pdf",
        document_title="The Bitter Lesson",
        page_from=1,
        page_to=1,
        chunk_index=0,
        chunk_text=keyword_candidate.chunk_text,
        heading="The Bitter Lesson",
        semantic_score=0.9,
        retrieval_sources=("semantic_primary",),
    )

    monkeypatch.setattr(
        "app.services.search._run_keyword_chunk_search",
        lambda session, request, candidate_limit=None, run_id=None: [keyword_candidate],
    )
    monkeypatch.setattr(
        "app.services.search._run_keyword_table_search",
        lambda session, request, candidate_limit=None, run_id=None: [],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_chunk_search",
        lambda session, request, query_embedding, candidate_limit=None, run_id=None: [
            semantic_candidate
        ],
    )
    monkeypatch.setattr(
        "app.services.search._run_semantic_table_search",
        lambda session, request, query_embedding, candidate_limit=None, run_id=None: [],
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
            mode="hybrid",
            limit=5,
            harness_name="default_v1",
        ),
        embedding_provider=FakeProvider(),
        origin="api",
        evaluation_id=uuid4(),
    )

    request_rows = [row for row in session.added if isinstance(row, SearchRequestRecord)]

    assert len(execution.results) >= 1
    assert session.rollback_calls == 0
    assert len(request_rows) == 1
    assert request_rows[0].evaluation_id is not None


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
