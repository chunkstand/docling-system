from __future__ import annotations

from uuid import uuid4

from app.schemas.search import SearchRequest
from app.services.search_harness_registry import get_search_harness
from app.services.search_harness_reranking import LinearFeatureSearchReranker
from app.services.search_query_features import QUERY_INTENT_PROSE_LOOKUP
from app.services.search_ranking import RankedResult


def _ranked_chunk(
    *,
    source_filename: str = "report.pdf",
    document_title: str | None = "Forest restoration report",
    heading: str | None = "Overview",
    chunk_text: str | None = "Forest restoration overview.",
    keyword_score: float = 0.5,
    retrieval_sources: tuple[str, ...] = ("keyword_primary",),
) -> RankedResult:
    return RankedResult(
        result_type="chunk",
        result_id=uuid4(),
        document_id=uuid4(),
        run_id=uuid4(),
        source_filename=source_filename,
        document_title=document_title,
        page_from=1,
        page_to=1,
        chunk_index=0,
        chunk_text=chunk_text,
        heading=heading,
        keyword_score=keyword_score,
        retrieval_sources=retrieval_sources,
    )


def test_linear_feature_search_reranker_prefers_filename_overlap() -> None:
    reranker = LinearFeatureSearchReranker(get_search_harness("default_v1").reranker_config)
    matching = _ranked_chunk(source_filename="mesa-restoration-outlook.pdf")
    plain = _ranked_chunk(source_filename="appendix.pdf")

    ranked = reranker.rerank(
        [plain, matching],
        request=SearchRequest(query="mesa restoration outlook", mode="hybrid", limit=2),
        score_getter=lambda item: float(item.keyword_score or 0.0),
        tabular_query=False,
        query_intent=QUERY_INTENT_PROSE_LOOKUP,
    )

    assert ranked[0].item.result_id == matching.result_id
    assert ranked[0].features["source_filename_exact_match"] == 1.0
    assert ranked[0].rank == 1


def test_linear_feature_search_reranker_records_late_interaction_signal() -> None:
    reranker = LinearFeatureSearchReranker(get_search_harness("multivector_v1").reranker_config)
    candidate = _ranked_chunk(retrieval_sources=("multivector_late_interaction",))

    ranked = reranker.rerank(
        [candidate],
        request=SearchRequest(query="forest restoration", mode="hybrid", limit=1),
        score_getter=lambda item: float(item.keyword_score or 0.0),
        tabular_query=False,
        query_intent=QUERY_INTENT_PROSE_LOOKUP,
    )

    assert ranked[0].features["late_interaction_signal"] == 1.0
    assert ranked[0].features["retrieval_profile_name"] == "multivector_v1"
