from __future__ import annotations

from types import SimpleNamespace

from app.services.evaluation_embedding_cache import prewarm_eval_corpus_query_embeddings


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[0.0] for _ in texts]


def test_prewarm_eval_corpus_query_embeddings_batches_unique_semantic_queries(monkeypatch) -> None:
    provider = FakeProvider()
    fixtures = [
        SimpleNamespace(
            queries=[
                SimpleNamespace(query="shared query", mode="hybrid"),
                SimpleNamespace(query="shared query", mode="semantic"),
                SimpleNamespace(query="keyword only", mode="keyword"),
                SimpleNamespace(query="new query", mode="hybrid"),
            ]
        )
    ]

    monkeypatch.setattr(
        "app.services.evaluation_embedding_cache.load_evaluation_fixtures",
        lambda: fixtures,
    )
    monkeypatch.setattr(
        "app.services.evaluation_embedding_cache.get_embedding_provider",
        lambda: provider,
    )

    summary = prewarm_eval_corpus_query_embeddings()

    assert summary == {"status": "completed", "query_count": 2}
    assert provider.calls == [["shared query", "new query"]]


def test_prewarm_eval_corpus_query_embeddings_reports_provider_failure(monkeypatch) -> None:
    fixtures = [SimpleNamespace(queries=[SimpleNamespace(query="query", mode="hybrid")])]

    monkeypatch.setattr(
        "app.services.evaluation_embedding_cache.load_evaluation_fixtures",
        lambda: fixtures,
    )
    monkeypatch.setattr(
        "app.services.evaluation_embedding_cache.get_embedding_provider",
        lambda: (_ for _ in ()).throw(ValueError("missing key")),
    )

    summary = prewarm_eval_corpus_query_embeddings()

    assert summary == {"status": "failed", "query_count": 1, "error": "missing key"}
