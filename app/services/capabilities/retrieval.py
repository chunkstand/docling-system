from __future__ import annotations

from app.services import search as search
from app.services.capabilities.retrieval_contract import RetrievalCapability
from app.services.capabilities.retrieval_services import ServicesRetrievalCapability

retrieval: RetrievalCapability = ServicesRetrievalCapability()

__all__ = [
    "RetrievalCapability",
    "ServicesRetrievalCapability",
    "retrieval",
    "search",
]
