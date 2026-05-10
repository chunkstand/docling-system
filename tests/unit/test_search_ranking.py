from __future__ import annotations

from uuid import uuid4

from app.services.search_query_features import build_query_feature_set
from app.services.search_ranking import (
    RankedResult,
    RerankedResult,
    merge_hybrid_candidates,
    merge_hybrid_results,
    table_title_match_features,
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


def test_merge_hybrid_candidates_combines_scores() -> None:
    keyword_item = _ranked_chunk()
    semantic_item = RankedResult(**keyword_item.__dict__)
    keyword_item.keyword_score = 0.8
    keyword_item.retrieval_sources = ("keyword_primary",)
    semantic_item.semantic_score = 0.9
    semantic_item.retrieval_sources = ("semantic_primary",)

    merged = merge_hybrid_candidates([keyword_item], [semantic_item])

    assert len(merged) == 1
    assert merged[0].keyword_score == 0.8
    assert merged[0].semantic_score == 0.9
    assert merged[0].hybrid_score is not None
    assert merged[0].retrieval_sources == ("keyword_primary", "semantic_primary")


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

    features = table_title_match_features(item, build_query_feature_set("fixture unit loading"))

    assert features == {"title_exact_match": 1.0, "title_token_coverage": 1.0}


def test_merge_hybrid_results_uses_supplied_reranker() -> None:
    item = _ranked_chunk()
    item.keyword_score = 0.7

    class FakeReranker:
        def rerank(self, items, **_kwargs):
            return [RerankedResult(item=items[0], rank=1, base_rank=1, score=0.77)]

    results = merge_hybrid_results(
        [item],
        [],
        limit=5,
        filters=None,
        tabular_query=False,
        active_reranker=FakeReranker(),
    )

    assert len(results) == 1
    assert results[0].score == 0.77
    assert results[0].scores.keyword_score == 0.7
