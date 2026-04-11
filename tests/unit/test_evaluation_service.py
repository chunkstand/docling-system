from __future__ import annotations

from types import SimpleNamespace

from app.services.evaluations import fixture_for_document, load_evaluation_fixtures


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
