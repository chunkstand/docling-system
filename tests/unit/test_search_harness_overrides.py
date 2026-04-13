from __future__ import annotations

import json

from app.services.search import get_search_harness, list_search_harnesses
from app.services.search_harness_overrides import (
    load_applied_search_harness_overrides,
    upsert_applied_search_harness_override,
)


def test_upsert_applied_search_harness_override_persists_to_json_file(
    monkeypatch,
    tmp_path,
) -> None:
    override_path = tmp_path / "config" / "search_harness_overrides.json"
    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: override_path,
    )

    upsert_applied_search_harness_override(
        "wide_v2_review",
        {
            "base_harness_name": "wide_v2",
            "retrieval_profile_overrides": {"keyword_candidate_multiplier": 9},
            "reranker_overrides": {"result_type_priority_bonus": 0.009},
            "override_type": "applied_harness_config_update",
        },
    )

    payload = json.loads(override_path.read_text())
    assert payload["version"] == 1
    assert payload["harnesses"]["wide_v2_review"]["base_harness_name"] == "wide_v2"
    assert load_applied_search_harness_overrides()["wide_v2_review"]["override_type"] == (
        "applied_harness_config_update"
    )


def test_list_search_harnesses_includes_applied_review_harness(monkeypatch, tmp_path) -> None:
    override_path = tmp_path / "config" / "search_harness_overrides.json"
    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: override_path,
    )
    upsert_applied_search_harness_override(
        "wide_v2_review",
        {
            "base_harness_name": "wide_v2",
            "retrieval_profile_overrides": {"keyword_candidate_multiplier": 9},
            "reranker_overrides": {"result_type_priority_bonus": 0.009},
            "override_type": "applied_harness_config_update",
            "applied_by": "operator@example.com",
        },
    )

    harnesses = list_search_harnesses()
    derived = next(harness for harness in harnesses if harness.name == "wide_v2_review")

    assert derived.base_harness_name == "wide_v2"
    assert derived.metadata["override_type"] == "applied_harness_config_update"
    assert derived.metadata["applied_by"] == "operator@example.com"
    assert derived.retrieval_profile.keyword_candidate_multiplier == 9


def test_get_search_harness_supports_transient_review_override(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "app.services.search_harness_overrides.get_search_harness_override_path",
        lambda: tmp_path / "config" / "search_harness_overrides.json",
    )

    harness = get_search_harness(
        "wide_v2_review",
        {
            "wide_v2_review": {
                "base_harness_name": "wide_v2",
                "retrieval_profile_overrides": {"keyword_candidate_multiplier": 9},
                "reranker_overrides": {"result_type_priority_bonus": 0.009},
                "override_type": "draft_harness_config_update",
            }
        },
    )

    assert harness.name == "wide_v2_review"
    assert harness.base_harness_name == "wide_v2"
    assert harness.retrieval_profile.keyword_candidate_multiplier == 9
    assert harness.reranker_config.result_type_priority_bonus == 0.009
