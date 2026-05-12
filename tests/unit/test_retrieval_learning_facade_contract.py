from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from app.services import retrieval_learning

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_LEARNING_PATH = PROJECT_ROOT / "app/services/retrieval_learning.py"

ALLOWED_PUBLIC_FUNCTIONS = {
    "materialize_retrieval_learning_dataset",
    "evaluate_retrieval_learning_candidate",
    "list_retrieval_learning_candidate_evaluations",
    "get_retrieval_learning_candidate_evaluation_detail",
    "create_retrieval_reranker_artifact",
    "list_retrieval_reranker_artifacts",
    "get_retrieval_reranker_artifact_detail",
}


def _load_retrieval_learning_tree() -> ast.Module:
    return ast.parse(RETRIEVAL_LEARNING_PATH.read_text(), filename=str(RETRIEVAL_LEARNING_PATH))


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


def test_retrieval_learning_facade_function_surface_is_exact() -> None:
    tree = _load_retrieval_learning_tree()
    function_names = {
        node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert function_names == ALLOWED_PUBLIC_FUNCTIONS


def test_retrieval_learning_facade_has_no_private_helpers_or_classes() -> None:
    tree = _load_retrieval_learning_tree()

    assert [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("_")
    ] == []
    assert [node.name for node in tree.body if isinstance(node, ast.ClassDef)] == []
