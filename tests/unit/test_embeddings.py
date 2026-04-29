from __future__ import annotations

from types import SimpleNamespace

from app.services.embeddings import OpenAIEmbeddingProvider, get_embedding_provider


class FakeEmbeddingsAPI:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def create(self, *, model: str, input: list[str], encoding_format: str):
        self.calls.append(list(input))
        return SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[float(call_index), float(item_index)])
                for item_index, _ in enumerate(input)
                for call_index in [len(self.calls)]
            ]
        )


def test_openai_embedding_provider_truncates_overlong_inputs_and_batches_requests() -> None:
    provider = OpenAIEmbeddingProvider(
        api_key="test",
        model="text-embedding-3-small",
        embedding_dim=2,
        max_input_tokens=4,
        batch_size=2,
    )
    fake_api = FakeEmbeddingsAPI()
    provider.client = SimpleNamespace(embeddings=fake_api)
    texts = [
        "alpha beta gamma delta epsilon zeta",
        "short text",
        "one two three four five six",
    ]

    embeddings = provider.embed_texts(texts)

    assert len(embeddings) == 3
    assert len(fake_api.calls) == 2
    assert fake_api.calls[0][1] == "short text"
    assert fake_api.calls[0][0] != texts[0]
    assert fake_api.calls[1][0] != texts[2]
    for batch in fake_api.calls:
        for text in batch:
            assert len(provider._encoding.encode(text)) <= provider.max_input_tokens


def test_openai_embedding_provider_reuses_cached_query_embeddings() -> None:
    provider = OpenAIEmbeddingProvider(
        api_key="test",
        model="text-embedding-3-small",
        embedding_dim=2,
        cache_size=8,
    )
    fake_api = FakeEmbeddingsAPI()
    provider.client = SimpleNamespace(embeddings=fake_api)

    first = provider.embed_texts(["repeat me"])
    second = provider.embed_texts(["repeat me"])

    assert first == second
    assert len(fake_api.calls) == 1
    assert fake_api.calls[0] == ["repeat me"]


def test_openai_embedding_provider_configures_timeout_and_retries(monkeypatch) -> None:
    captured = {}

    def fake_openai(*, api_key: str, timeout: float, max_retries: int):
        captured["api_key"] = api_key
        captured["timeout"] = timeout
        captured["max_retries"] = max_retries
        return SimpleNamespace(embeddings=SimpleNamespace(create=lambda **kwargs: None))

    monkeypatch.setattr("app.services.embeddings.OpenAI", fake_openai)

    OpenAIEmbeddingProvider(
        api_key="test-key",
        model="text-embedding-3-small",
        embedding_dim=2,
        timeout_seconds=12.5,
        max_retries=4,
    )

    assert captured == {
        "api_key": "test-key",
        "timeout": 12.5,
        "max_retries": 4,
    }


def test_get_embedding_provider_uses_configured_cache_size(monkeypatch) -> None:
    get_embedding_provider.cache_clear()
    monkeypatch.setattr(
        "app.services.embeddings.get_settings",
        lambda: SimpleNamespace(
            openai_api_key="test-key",
            openai_embedding_model="text-embedding-3-small",
            embedding_dim=2,
            embedding_cache_size=32,
            openai_timeout_seconds=12.5,
            openai_max_retries=4,
        ),
    )
    monkeypatch.setattr(
        "app.services.embeddings.OpenAI",
        lambda **_kwargs: SimpleNamespace(embeddings=SimpleNamespace(create=lambda **kwargs: None)),
    )

    provider = get_embedding_provider()

    assert provider.cache_size == 32
    get_embedding_provider.cache_clear()
