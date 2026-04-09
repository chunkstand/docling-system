from __future__ import annotations

from uuid import uuid4

from app.services.search import RankedChunk, _merge_hybrid_results


def _ranked_chunk() -> RankedChunk:
    return RankedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        chunk_text="chunk text",
        heading="Heading",
        page_from=1,
        page_to=1,
        source_filename="report.pdf",
    )


def test_merge_hybrid_results_combines_scores() -> None:
    keyword_item = _ranked_chunk()
    semantic_item = RankedChunk(**keyword_item.__dict__)
    keyword_item.keyword_score = 0.8
    semantic_item.semantic_score = 0.9

    results = _merge_hybrid_results([keyword_item], [semantic_item], limit=5)

    assert len(results) == 1
    assert results[0].scores.keyword_score == 0.8
    assert results[0].scores.semantic_score == 0.9
    assert results[0].scores.hybrid_score is not None


def test_merge_hybrid_results_keeps_distinct_chunks() -> None:
    keyword_item = _ranked_chunk()
    keyword_item.keyword_score = 0.6
    semantic_item = _ranked_chunk()
    semantic_item.semantic_score = 0.7

    results = _merge_hybrid_results([keyword_item], [semantic_item], limit=5)

    assert len(results) == 2
