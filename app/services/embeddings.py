from __future__ import annotations

from functools import lru_cache

import structlog
import tiktoken
from openai import OpenAI

from app.core.config import get_settings

EMBEDDING_INPUT_TOKEN_LIMIT = 8191
EMBEDDING_BATCH_SIZE = 128
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
    ) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.embedding_dim = embedding_dim
        self.max_input_tokens = max_input_tokens
        self.batch_size = batch_size
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

        embeddings: list[list[float]] = []
        for start in range(0, len(prepared_texts), self.batch_size):
            response = self.client.embeddings.create(
                model=self.model,
                input=prepared_texts[start : start + self.batch_size],
                encoding_format="float",
            )
            batch_embeddings = [list(item.embedding) for item in response.data]
            self._validate_dimensions(batch_embeddings)
            embeddings.extend(batch_embeddings)
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
