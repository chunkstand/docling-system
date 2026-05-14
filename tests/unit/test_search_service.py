from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.schemas.search import SearchRequest
from app.services import search as search_service
from app.services.search import SearchExecution


def test_execute_search_facade_delegates_to_orchestration(monkeypatch) -> None:
    observed: dict[str, object] = {}
    request = SearchRequest(query="vent stack", mode="hybrid", limit=3)
    expected = SearchExecution(
        results=[],
        request_id=uuid4(),
        harness_name="default_v1",
        reranker_name="linear_feature_reranker",
        reranker_version="v1",
        retrieval_profile_name="default_v1",
        harness_config={"harness_name": "default_v1"},
        embedding_status="completed",
        embedding_error=None,
        candidate_count=0,
        table_hit_count=0,
        duration_ms=1.0,
        details={},
        evidence_operator_run_ids=[],
    )

    def fake_execute_search(
        *,
        session,
        request,
        embedding_provider,
        run_id,
        origin,
        evaluation_id,
        parent_request_id,
        reranker,
        harness_overrides,
        execution_type,
    ):
        observed.update(
            session=session,
            request=request,
            embedding_provider=embedding_provider,
            run_id=run_id,
            origin=origin,
            evaluation_id=evaluation_id,
            parent_request_id=parent_request_id,
            reranker=reranker,
            harness_overrides=harness_overrides,
            execution_type=execution_type,
        )
        return expected

    monkeypatch.setattr(
        search_service._search_execution_orchestration,
        "execute_search",
        fake_execute_search,
    )

    run_id = uuid4()
    evaluation_id = uuid4()
    parent_request_id = uuid4()
    session = object()
    provider = object()
    reranker = object()
    harness_overrides = {"retrieval_profile": {"limit": 12}}

    result = search_service.execute_search(
        session,
        request,
        provider,
        run_id=run_id,
        origin="integration-test",
        evaluation_id=evaluation_id,
        parent_request_id=parent_request_id,
        reranker=reranker,
        harness_overrides=harness_overrides,
    )

    assert result is expected
    assert observed == {
        "session": session,
        "request": request,
        "embedding_provider": provider,
        "run_id": run_id,
        "origin": "integration-test",
        "evaluation_id": evaluation_id,
        "parent_request_id": parent_request_id,
        "reranker": reranker,
        "harness_overrides": harness_overrides,
        "execution_type": SearchExecution,
    }


def test_search_documents_facade_passes_explicit_run_scope(monkeypatch) -> None:
    scoped_run_id = uuid4()
    expected_results = [SimpleNamespace(result_id=uuid4())]
    observed: dict[str, object] = {}

    def fake_execute_search(*args, **kwargs):
        observed["run_id"] = kwargs.get("run_id")
        return SimpleNamespace(results=expected_results)

    monkeypatch.setattr(search_service, "execute_search", fake_execute_search)

    results = search_service.search_documents(
        session=None,
        request=SearchRequest(query="vent stack", mode="hybrid", limit=5),
        run_id=scoped_run_id,
    )

    assert results == expected_results
    assert observed["run_id"] == scoped_run_id
