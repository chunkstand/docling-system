from __future__ import annotations

from types import SimpleNamespace

from app.services import retrieval_learning


def test_retrieval_learning_facade_delegates_dataset_materialization(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_materialize(session, **kwargs):
        captured["session"] = session
        captured.update(kwargs)
        return {"schema_name": "retrieval_learning_dataset"}

    monkeypatch.setattr(
        retrieval_learning._retrieval_learning_datasets,
        "materialize_retrieval_learning_dataset",
        fake_materialize,
    )

    session = object()
    response = retrieval_learning.materialize_retrieval_learning_dataset(
        session,
        limit=7,
        source_types=["feedback"],
        set_name="fixture",
        created_by="operator",
    )

    assert response == {"schema_name": "retrieval_learning_dataset"}
    assert captured["session"] is session
    assert captured["limit"] == 7
    assert captured["source_types"] == ["feedback"]
    assert captured["set_name"] == "fixture"
    assert captured["created_by"] == "operator"


def test_retrieval_learning_facade_delegates_candidate_evaluation_with_runtime_seams(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_evaluate(session, request, **kwargs):
        captured["session"] = session
        captured["request"] = request
        captured.update(kwargs)
        return {"schema_name": "retrieval_learning_candidate_evaluation"}

    monkeypatch.setattr(
        retrieval_learning._retrieval_learning_candidates,
        "evaluate_retrieval_learning_candidate",
        fake_evaluate,
    )

    session = object()
    request = SimpleNamespace(candidate_harness_name="wide_v2")
    response = retrieval_learning.evaluate_retrieval_learning_candidate(session, request)

    assert response == {"schema_name": "retrieval_learning_candidate_evaluation"}
    assert captured["session"] is session
    assert captured["request"] is request
    assert captured["evaluate_search_harness_fn"] is retrieval_learning.evaluate_search_harness
    assert (
        captured["record_search_harness_release_gate_fn"]
        is retrieval_learning.record_search_harness_release_gate
    )


def test_retrieval_learning_facade_delegates_reranker_artifact_creation_with_runtime_seams(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_create(session, request, **kwargs):
        captured["session"] = session
        captured["request"] = request
        captured.update(kwargs)
        return {"schema_name": "retrieval_reranker_artifact"}

    monkeypatch.setattr(
        retrieval_learning._retrieval_learning_artifacts,
        "create_retrieval_reranker_artifact",
        fake_create,
    )

    session = object()
    request = SimpleNamespace(artifact_name="candidate")
    response = retrieval_learning.create_retrieval_reranker_artifact(session, request)

    assert response == {"schema_name": "retrieval_reranker_artifact"}
    assert captured["session"] is session
    assert captured["request"] is request
    assert captured["get_search_harness_fn"] is retrieval_learning.get_search_harness
    assert captured["evaluate_search_harness_fn"] is retrieval_learning.evaluate_search_harness
    assert (
        captured["record_search_harness_release_gate_fn"]
        is retrieval_learning.record_search_harness_release_gate
    )
