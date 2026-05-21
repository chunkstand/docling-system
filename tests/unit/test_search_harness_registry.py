from __future__ import annotations

import pytest

from app.services import search_harness_registry


def test_build_derived_search_harness_rejects_unknown_retrieval_override_field() -> None:
    registry = search_harness_registry.build_search_harness_registry()

    with pytest.raises(ValueError, match="Invalid retrieval override field"):
        search_harness_registry.build_derived_search_harness(
            harness_name="invalid",
            spec={
                "base_harness_name": "default_v1",
                "retrieval_profile_overrides": {"unknown_field": 1},
            },
            registry=registry,
        )


def test_build_search_harness_registry_applies_transient_overrides() -> None:
    registry = search_harness_registry.build_search_harness_registry(
        {
            "wide_v2_review": {
                "base_harness_name": "wide_v2",
                "retrieval_profile_overrides": {"keyword_candidate_multiplier": 9},
                "reranker_overrides": {"result_type_priority_bonus": 0.009},
                "override_type": "draft_harness_config_update",
            }
        }
    )

    derived = registry["wide_v2_review"]

    assert derived.base_harness_name == "wide_v2"
    assert derived.metadata["override_type"] == "draft_harness_config_update"
    assert derived.retrieval_profile.keyword_candidate_multiplier == 9
    assert derived.reranker_config.result_type_priority_bonus == 0.009


def test_get_search_harness_reports_available_names_for_unknown_override() -> None:
    with pytest.raises(ValueError, match="Available: .*default_v1"):
        search_harness_registry.get_search_harness("missing_harness")
