from __future__ import annotations

from pathlib import Path

from tests.integration.portable_ontology_roundtrip_lifecycle_support import (
    run_manual_lifecycle_verification_and_apply_roundtrip,
)
from tests.integration.portable_ontology_roundtrip_support import INTEGRATION_SKIP_MARK

pytestmark = INTEGRATION_SKIP_MARK


def test_manual_ontology_lifecycle_verification_and_apply_roundtrip(
    postgres_integration_harness,
    monkeypatch,
    tmp_path: Path,
) -> None:
    run_manual_lifecycle_verification_and_apply_roundtrip(
        postgres_integration_harness,
        monkeypatch,
        tmp_path,
    )
