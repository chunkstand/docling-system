from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app


def test_search_harness_list_route_returns_registered_definitions(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routers.search.list_search_harness_definitions",
        lambda: [
            {
                "harness_name": "default_v1",
                "reranker_name": "linear_feature_reranker",
                "reranker_version": "v1",
                "retrieval_profile_name": "default_v1",
                "harness_config": {},
                "is_default": True,
            }
        ],
    )

    client = TestClient(app)
    response = client.get("/search/harnesses")

    assert response.status_code == 200
    assert response.json() == [
        {
            "harness_name": "default_v1",
            "reranker_name": "linear_feature_reranker",
            "reranker_version": "v1",
            "retrieval_profile_name": "default_v1",
            "harness_config": {},
            "is_default": True,
        }
    ]


def test_search_harness_descriptor_route_returns_descriptor_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routers.search.get_search_harness_descriptor",
        lambda harness_name: {
            "schema_name": "search_harness_descriptor",
            "schema_version": "1.0",
            "harness_name": harness_name,
            "base_harness_name": None,
            "is_default": harness_name == "default_v1",
            "config_fingerprint": "abc123",
            "reranker_name": "linear_feature_reranker",
            "reranker_version": "v1",
            "retrieval_profile_name": harness_name,
            "retrieval_stages": ["keyword_candidates"],
            "tunable_knobs": {"retrieval_profile_overrides": []},
            "constraints": [],
            "intended_query_families": [],
            "known_tradeoffs": [],
            "harness_config": {},
            "metadata": {},
        },
    )

    client = TestClient(app)
    response = client.get("/search/harnesses/default_v1/descriptor")

    assert response.status_code == 200
    assert response.json()["schema_name"] == "search_harness_descriptor"
    assert response.json()["harness_name"] == "default_v1"
    assert response.json()["retrieval_profile_name"] == "default_v1"


def test_search_harness_descriptor_route_returns_machine_readable_error(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routers.search.get_search_harness_descriptor",
        lambda harness_name: (_ for _ in ()).throw(ValueError("Unknown search harness")),
    )

    client = TestClient(app)
    response = client.get("/search/harnesses/missing_v1/descriptor")

    assert response.status_code == 404
    assert response.json()["error_code"] == "search_harness_not_found"
