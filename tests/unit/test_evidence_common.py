from __future__ import annotations

from uuid import UUID

from app.services import evidence
from app.services.evidence_common import (
    clean_mapping,
    id_str_values,
    int_or_none,
    page_spans_overlap,
    payload_sha256,
    source_page_span,
    source_record_key,
    string_values,
    uuid_values,
)


def test_payload_sha256_uses_canonical_json_hash() -> None:
    assert (
        payload_sha256({"b": 2, "a": 1})
        == "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )
    assert payload_sha256(None) is None


def test_uuid_values_filters_invalid_values_and_preserves_first_seen_order() -> None:
    first = UUID("11111111-1111-1111-1111-111111111111")
    second = UUID("22222222-2222-2222-2222-222222222222")

    assert uuid_values([str(first), first, "", "not-a-uuid", None, str(second)]) == [
        first,
        second,
    ]


def test_string_and_id_values_match_legacy_normalization() -> None:
    first = "11111111-1111-1111-1111-111111111111"
    second = "22222222-2222-2222-2222-222222222222"

    assert string_values(["alpha", "alpha", "", None, 2]) == ["alpha", "2"]
    assert id_str_values([first, first, "bad-id", second]) == [first, second]


def test_clean_mapping_is_shallow() -> None:
    assert clean_mapping(
        {"keep": 1, "drop": 2, "nested": {"drop": 3}},
        drop_fields={"drop"},
    ) == {"keep": 1, "nested": {"drop": 3}}


def test_source_record_key_accepts_chunk_and_table_only() -> None:
    assert source_record_key(" Chunk ", "abc") == "source:chunk:abc"
    assert source_record_key("table", "def") == "source:table:def"
    assert source_record_key("figure", "ghi") is None
    assert source_record_key("chunk", "") is None


def test_int_or_none_matches_legacy_coercion() -> None:
    assert int_or_none("7") == 7
    assert int_or_none(8) == 8
    assert int_or_none("") is None
    assert int_or_none("invalid") is None


def test_source_page_span_defaults_missing_page_to_to_page_from() -> None:
    assert source_page_span(
        document_id="doc",
        run_id="run",
        page_from="3",
        page_to="",
    ) == {
        "document_id": "doc",
        "run_id": "run",
        "page_from": 3,
        "page_to": 3,
        "key": "page:doc:run:3:3",
    }
    assert source_page_span(document_id=None, run_id="run", page_from=3, page_to=4) is None
    assert source_page_span(document_id="doc", run_id="run", page_from="", page_to=4) is None


def test_page_spans_overlap_requires_same_document_and_run() -> None:
    span = source_page_span(document_id="doc", run_id="run", page_from=3, page_to=5)
    overlapping = source_page_span(document_id="doc", run_id="run", page_from=5, page_to=7)
    disjoint = source_page_span(document_id="doc", run_id="run", page_from=6, page_to=7)
    other_run = source_page_span(document_id="doc", run_id="other", page_from=4, page_to=4)

    assert span is not None
    assert overlapping is not None
    assert disjoint is not None
    assert other_run is not None
    assert page_spans_overlap(span, overlapping)
    assert not page_spans_overlap(span, disjoint)
    assert not page_spans_overlap(span, other_run)


def test_evidence_facade_preserves_legacy_helper_names() -> None:
    assert evidence.payload_sha256 is payload_sha256
    assert evidence._uuid_values is uuid_values
    assert evidence._string_values is string_values
    assert evidence._source_record_key is source_record_key
