from __future__ import annotations

import importlib
from uuid import uuid4

from app.schemas.search import SearchRequest
from app.services.capabilities.retrieval import ServicesRetrievalCapability


def test_retrieval_capability_maps_public_parent_request_name(monkeypatch) -> None:
    captured: dict = {}

    def fake_execute_search(session, request, **kwargs):
        captured.update(kwargs)
        return object()

    retrieval_module = importlib.import_module("app.services.capabilities.retrieval")
    monkeypatch.setattr(retrieval_module.search, "execute_search", fake_execute_search)

    parent_request_id = uuid4()
    capability = ServicesRetrievalCapability()
    result = capability.execute_search(
        object(),
        SearchRequest(query="test", mode="keyword"),
        origin="api",
        parent_search_request_id=parent_request_id,
    )

    assert result is not None
    assert captured["parent_request_id"] == parent_request_id
    assert "parent_search_request_id" not in captured
