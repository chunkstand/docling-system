from __future__ import annotations

import pytest

from app.services import evidence, evidence_search_packages


@pytest.mark.parametrize(
    "name",
    [
        "get_search_evidence_package",
        "persist_search_evidence_package_export",
        "export_search_evidence_package",
        "get_search_evidence_package_export_trace",
    ],
)
def test_evidence_facade_reexports_search_package_functions(name: str) -> None:
    assert getattr(evidence, name) is getattr(evidence_search_packages, name)
