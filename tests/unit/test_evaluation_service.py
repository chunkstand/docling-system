from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.evaluations import (
    fixture_for_document,
    load_evaluation_fixtures,
    resolve_baseline_run_id,
)


def test_load_evaluation_fixtures_compiles_search_queries() -> None:
    fixtures = load_evaluation_fixtures()

    born_digital = next(fixture for fixture in fixtures if fixture.name == "born_digital_simple")
    assert born_digital.path.endswith("UPC_Appendix_N.pdf")
    assert len(born_digital.queries) >= 1
    assert born_digital.queries[0].expected_result_type == "table"
    assert born_digital.queries[0].expected_top_n >= 1


def test_fixture_for_document_matches_by_source_filename() -> None:
    document = SimpleNamespace(source_filename="UPC_Appendix_N.pdf")

    fixture = fixture_for_document(document)

    assert fixture is not None
    assert fixture.name == "born_digital_simple"


def test_resolve_baseline_run_id_prefers_prior_active_run_for_reprocess() -> None:
    candidate_run_id = uuid4()
    prior_active_run_id = uuid4()

    assert resolve_baseline_run_id(candidate_run_id, prior_active_run_id) == prior_active_run_id


def test_resolve_baseline_run_id_ignores_self_and_honors_explicit_override() -> None:
    candidate_run_id = uuid4()
    active_run_id = candidate_run_id
    explicit_baseline_run_id = uuid4()

    assert resolve_baseline_run_id(candidate_run_id, active_run_id) is None
    assert (
        resolve_baseline_run_id(
            candidate_run_id,
            active_run_id,
            explicit_baseline_run_id=explicit_baseline_run_id,
        )
        == explicit_baseline_run_id
    )
