from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.api.errors import api_error

RETRIEVAL_RERANKER_ARTIFACT_SCHEMA = "retrieval_reranker_artifact"
RETRIEVAL_RERANKER_ARTIFACT_SCHEMA_VERSION = "1.0"
RETRIEVAL_RERANKER_ARTIFACT_KIND = "linear_feature_weight_candidate"


def reranker_artifact_not_found_error(artifact_id: UUID) -> HTTPException:
    return api_error(
        status.HTTP_404_NOT_FOUND,
        "retrieval_reranker_artifact_not_found",
        "Retrieval reranker artifact not found.",
        artifact_id=str(artifact_id),
    )
