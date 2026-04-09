from __future__ import annotations

from functools import lru_cache

from openai import OpenAI

from app.core.config import get_settings


class EmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str, embedding_dim: int) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.embedding_dim = embedding_dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
            encoding_format="float",
        )
        embeddings = [list(item.embedding) for item in response.data]
        for embedding in embeddings:
            if len(embedding) != self.embedding_dim:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {self.embedding_dim}, got {len(embedding)}."
                )
        return embeddings


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("DOCLING_SYSTEM_OPENAI_API_KEY must be set for embeddings.")
    return OpenAIEmbeddingProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_embedding_model,
        embedding_dim=settings.embedding_dim,
    )
