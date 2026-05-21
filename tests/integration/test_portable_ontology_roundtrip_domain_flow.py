from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration.portable_ontology_roundtrip_domain_flow_support import (
    run_domain_agnostic_roundtrip,
)
from tests.integration.portable_ontology_roundtrip_support import INTEGRATION_SKIP_MARK

pytestmark = INTEGRATION_SKIP_MARK


@pytest.mark.parametrize(
    ("title", "source_filename", "phrase", "expected_concept_key"),
    [
        (
            "Incident Review",
            "incident-review.pdf",
            "incident response latency",
            "incident_response_latency",
        ),
        (
            "Vendor Escalation Memo",
            "vendor-escalation.pdf",
            "vendor escalation owner",
            "vendor_escalation_owner",
        ),
    ],
)
def test_portable_ontology_roundtrip_is_domain_agnostic(
    postgres_integration_harness,
    monkeypatch,
    tmp_path: Path,
    title: str,
    source_filename: str,
    phrase: str,
    expected_concept_key: str,
) -> None:
    run_domain_agnostic_roundtrip(
        postgres_integration_harness,
        monkeypatch,
        tmp_path,
        title=title,
        source_filename=source_filename,
        phrase=phrase,
        expected_concept_key=expected_concept_key,
    )
