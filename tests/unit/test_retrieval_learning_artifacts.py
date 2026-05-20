from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.services import retrieval_learning_artifacts

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_LEARNING_ARTIFACTS_PATH = (
    PROJECT_ROOT / "app/services/retrieval_learning_artifacts.py"
)

ALLOWED_PUBLIC_FUNCTIONS = {
    "reranker_artifact_not_found_error",
    "candidate_request_from_artifact_request",
    "feature_weight_candidate",
    "change_impact_report",
    "to_reranker_artifact_summary",
    "to_reranker_artifact_response",
    "create_retrieval_reranker_artifact",
    "list_retrieval_reranker_artifacts",
    "get_retrieval_reranker_artifact_detail",
}


def _load_retrieval_learning_artifacts_tree() -> ast.Module:
    return ast.parse(
        RETRIEVAL_LEARNING_ARTIFACTS_PATH.read_text(),
        filename=str(RETRIEVAL_LEARNING_ARTIFACTS_PATH),
    )


def test_retrieval_learning_artifacts_facade_delegates_feature_weight_helpers(
    monkeypatch,
) -> None:
    request = object()
    training_run = object()
    captured: dict[str, object] = {}

    def fake_candidate_request(payload):
        captured["candidate_request_payload"] = payload
        return {"schema_name": "candidate_request"}

    def fake_feature_weight_candidate(**kwargs):
        captured.update(kwargs)
        return (
            {"schema_name": "feature_weights"},
            {"wide_v2": {"override_type": "retrieval_reranker_artifact"}},
            {"override_type": "retrieval_reranker_artifact"},
        )

    monkeypatch.setattr(
        retrieval_learning_artifacts._weights,
        "candidate_request_from_artifact_request",
        fake_candidate_request,
    )
    monkeypatch.setattr(
        retrieval_learning_artifacts._weights,
        "feature_weight_candidate",
        fake_feature_weight_candidate,
    )

    candidate_request = retrieval_learning_artifacts.candidate_request_from_artifact_request(
        request
    )
    feature_weights, harness_overrides, override_spec = (
        retrieval_learning_artifacts.feature_weight_candidate(
            training_run=training_run,
            base_harness_name="default_v1",
            candidate_harness_name="wide_v2",
            artifact_name="artifact",
            get_search_harness_fn=lambda _name: None,
        )
    )

    assert candidate_request == {"schema_name": "candidate_request"}
    assert captured["candidate_request_payload"] is request
    assert captured["training_run"] is training_run
    assert feature_weights["schema_name"] == "feature_weights"
    assert harness_overrides["wide_v2"]["override_type"] == "retrieval_reranker_artifact"
    assert override_spec["override_type"] == "retrieval_reranker_artifact"


def test_retrieval_learning_artifacts_facade_delegates_lifecycle_and_views(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_create(session, request, **kwargs):
        captured["create_session"] = session
        captured["create_request"] = request
        captured.update(kwargs)
        return {"schema_name": "retrieval_reranker_artifact"}

    def fake_list(session, **kwargs):
        captured["list_session"] = session
        captured["list_kwargs"] = kwargs
        return ["summary"]

    def fake_get(session, artifact_id):
        captured["get_session"] = session
        captured["artifact_id"] = artifact_id
        return {"artifact_id": str(artifact_id)}

    monkeypatch.setattr(
        retrieval_learning_artifacts._lifecycle,
        "create_retrieval_reranker_artifact",
        fake_create,
    )
    monkeypatch.setattr(
        retrieval_learning_artifacts._views,
        "list_retrieval_reranker_artifacts",
        fake_list,
    )
    monkeypatch.setattr(
        retrieval_learning_artifacts._views,
        "get_retrieval_reranker_artifact_detail",
        fake_get,
    )

    session = object()
    request = SimpleNamespace(artifact_name="artifact")
    artifact_id = uuid4()

    response = retrieval_learning_artifacts.create_retrieval_reranker_artifact(
        session,
        request,
        get_search_harness_fn=lambda _name: None,
        evaluate_search_harness_fn=lambda *args, **kwargs: None,
        record_search_harness_release_gate_fn=lambda *args, **kwargs: None,
    )
    summaries = retrieval_learning_artifacts.list_retrieval_reranker_artifacts(
        session,
        limit=7,
        candidate_harness_name="wide_v2",
    )
    detail = retrieval_learning_artifacts.get_retrieval_reranker_artifact_detail(
        session,
        artifact_id,
    )

    assert response == {"schema_name": "retrieval_reranker_artifact"}
    assert captured["create_session"] is session
    assert captured["create_request"] is request
    assert summaries == ["summary"]
    assert captured["list_session"] is session
    assert captured["list_kwargs"] == {
        "limit": 7,
        "retrieval_training_run_id": None,
        "candidate_harness_name": "wide_v2",
    }
    assert detail == {"artifact_id": str(artifact_id)}
    assert captured["get_session"] is session
    assert captured["artifact_id"] == artifact_id


def test_retrieval_learning_artifacts_facade_function_surface_is_exact() -> None:
    tree = _load_retrieval_learning_artifacts_tree()
    function_names = {
        node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert function_names == ALLOWED_PUBLIC_FUNCTIONS


def test_retrieval_learning_artifacts_facade_has_no_private_helpers_or_classes() -> None:
    tree = _load_retrieval_learning_artifacts_tree()

    assert [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("_")
    ] == []
    assert [node.name for node in tree.body if isinstance(node, ast.ClassDef)] == []
