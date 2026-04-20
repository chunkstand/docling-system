from __future__ import annotations

from pathlib import Path

import pytest

from app.services.semantic_registry import write_semantic_registry_payload


def test_write_semantic_registry_payload_rejects_invalid_contract(tmp_path: Path) -> None:
    invalid_payload = {
        "registry_name": "semantic_registry",
        "registry_version": "alpha.1",
        "categories": [],
        "concepts": [
            {
                "concept_key": "integration_threshold",
                "preferred_label": "Integration Threshold",
                "category_keys": ["missing_category"],
                "aliases": ["integration threshold"],
            }
        ],
    }

    with pytest.raises(ValueError, match="unknown category_key"):
        write_semantic_registry_payload(invalid_payload, registry_path=tmp_path / "semantic_registry.yaml")

    assert not (tmp_path / "semantic_registry.yaml").exists()
