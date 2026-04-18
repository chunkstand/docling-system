from __future__ import annotations

from collections import OrderedDict
from functools import lru_cache
from threading import Lock

import structlog
import tiktoken
from openai import OpenAI

from app.core.config import get_settings

EMBEDDING_INPUT_TOKEN_LIMIT = 8191
EMBEDDING_BATCH_SIZE = 128
EMBEDDING_CACHE_SIZE = 256
logger = structlog.get_logger(__name__)


class EmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        embedding_dim: int,
        *,
        max_input_tokens: int = EMBEDDING_INPUT_TOKEN_LIMIT,
        batch_size: int = EMBEDDING_BATCH_SIZE,
        cache_size: int = EMBEDDING_CACHE_SIZE,
    ) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.embedding_dim = embedding_dim
        self.max_input_tokens = max_input_tokens
        self.batch_size = batch_size
        self.cache_size = cache_size
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._cache_lock = Lock()
        try:
            self._encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self._encoding = tiktoken.get_encoding("cl100k_base")

    def _truncate_text(self, text: str) -> tuple[str, bool]:
        token_ids = self._encoding.encode(text or "")
        if len(token_ids) <= self.max_input_tokens:
            return text, False
        return self._encoding.decode(token_ids[: self.max_input_tokens]), True

    def _validate_dimensions(self, embeddings: list[list[float]]) -> None:
        for embedding in embeddings:
            if len(embedding) != self.embedding_dim:
                raise ValueError(
                    "Embedding dimension mismatch: "
                    f"expected {self.embedding_dim}, got {len(embedding)}."
                )

    def _get_cached_embedding(self, text: str) -> list[float] | None:
        with self._cache_lock:
            embedding = self._cache.get(text)
            if embedding is None:
                return None
            self._cache.move_to_end(text)
            return list(embedding)

    def _store_cached_embedding(self, text: str, embedding: list[float]) -> None:
        with self._cache_lock:
            self._cache[text] = list(embedding)
            self._cache.move_to_end(text)
            while len(self._cache) > self.cache_size:
                self._cache.popitem(last=False)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        prepared_texts: list[str] = []
        clipped_input_count = 0
        for text in texts:
            prepared_text, was_clipped = self._truncate_text(text)
            prepared_texts.append(prepared_text)
            clipped_input_count += int(was_clipped)

        if clipped_input_count:
            logger.info(
                "embedding_inputs_truncated",
                model=self.model,
                clipped_input_count=clipped_input_count,
                max_input_tokens=self.max_input_tokens,
            )

        embeddings: list[list[float] | None] = [None] * len(prepared_texts)
        missing: list[tuple[int, str]] = []
        for index, text in enumerate(prepared_texts):
            cached = self._get_cached_embedding(text)
            if cached is not None:
                embeddings[index] = cached
            else:
                missing.append((index, text))

        for start in range(0, len(missing), self.batch_size):
            batch = missing[start : start + self.batch_size]
            response = self.client.embeddings.create(
                model=self.model,
                input=[text for _, text in batch],
                encoding_format="float",
            )
            batch_embeddings = [list(item.embedding) for item in response.data]
            self._validate_dimensions(batch_embeddings)
            for (index, text), embedding in zip(batch, batch_embeddings, strict=True):
                self._store_cached_embedding(text, embedding)
                embeddings[index] = embedding

        return [list(embedding) for embedding in embeddings if embedding is not None]


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
