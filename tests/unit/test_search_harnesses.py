from __future__ import annotations

from app.services import search_harnesses
from app.services.search_harness_reranking import LinearFeatureSearchReranker


def test_search_harness_facade_reexports_registry_helpers() -> None:
    harness = search_harnesses.get_search_harness("wide_v2")

    assert harness.name == "wide_v2"
    assert "default_v1" in {row.name for row in search_harnesses.list_search_harnesses()}


def test_search_harness_facade_builds_default_reranker_from_focused_owner() -> None:
    reranker = search_harnesses.get_default_reranker()

    assert isinstance(reranker, LinearFeatureSearchReranker)
    assert reranker.config.harness_name == "default_v1"
