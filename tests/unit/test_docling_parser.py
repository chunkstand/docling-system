from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.docling_parser import (
    DoclingParser,
    _normalize_chunks,
    _snapshot_items,
    get_fallback_document_converter,
)


class FakeDocument:
    def __init__(self) -> None:
        self.name = "sample"

    def iterate_items(self):
        yield (
            SimpleNamespace(
                text="701.1 Applicability",
                level=1,
                label="section_header",
                prov=[SimpleNamespace(page_no=1)],
            ),
            0,
        )
        yield (
            SimpleNamespace(
                text="First paragraph", label="text", prov=[SimpleNamespace(page_no=1)]
            ),
            1,
        )
        yield (
            SimpleNamespace(
                label="picture", self_ref="#/pictures/0", prov=[SimpleNamespace(page_no=1)]
            ),
            1,
        )
        yield (
            SimpleNamespace(
                text="UpCodes Diagram (1)", label="text", prov=[SimpleNamespace(page_no=1)]
            ),
            1,
        )
        yield (
            SimpleNamespace(
                text="Island Fixture Venting (UPC)", label="text", prov=[SimpleNamespace(page_no=1)]
            ),
            1,
        )
        yield (
            SimpleNamespace(text="TABLE 701.2", label="caption", prov=[SimpleNamespace(page_no=2)]),
            1,
        )
        yield (
            SimpleNamespace(
                text="MATERIALS FOR DRAIN, WASTE, VENT PIPE AND FITTINGS",
                level=1,
                label="section_header",
                prov=[SimpleNamespace(page_no=2)],
            ),
            1,
        )
        yield (SimpleNamespace(label="table", prov=[SimpleNamespace(page_no=2)]), 1)
        yield (SimpleNamespace(label="table", prov=[SimpleNamespace(page_no=3)]), 1)
        yield (
            SimpleNamespace(
                text="701.3 Drainage Fittings",
                level=1,
                label="section_header",
                prov=[SimpleNamespace(page_no=4)],
            ),
            0,
        )
        yield (
            SimpleNamespace(
                text="Second paragraph", label="text", prov=[SimpleNamespace(page_no=4)]
            ),
            1,
        )
        yield (
            SimpleNamespace(
                label="picture", self_ref="#/pictures/1", prov=[SimpleNamespace(page_no=4)]
            ),
            1,
        )

    def export_to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": "docling",
            "texts": [
                {
                    "self_ref": "#/texts/0",
                    "text": "Fixture Venting Diagram",
                }
            ],
            "pictures": [
                {
                    "self_ref": "#/pictures/0",
                    "label": "picture",
                    "captions": [],
                    "references": [],
                    "footnotes": [],
                    "annotations": [],
                    "prov": [
                        {
                            "page_no": 1,
                            "bbox": {
                                "l": 10,
                                "t": 20,
                                "r": 30,
                                "b": 40,
                                "coord_origin": "BOTTOMLEFT",
                            },
                            "charspan": [0, 0],
                        }
                    ],
                },
                {
                    "self_ref": "#/pictures/1",
                    "label": "picture",
                    "captions": ["#/texts/0"],
                    "references": [],
                    "footnotes": [],
                    "annotations": [],
                    "prov": [
                        {
                            "page_no": 4,
                            "bbox": {
                                "l": 11,
                                "t": 21,
                                "r": 31,
                                "b": 41,
                                "coord_origin": "BOTTOMLEFT",
                            },
                            "charspan": [0, 0],
                        }
                    ],
                },
            ],
            "tables": [
                {
                    "self_ref": "#/tables/0",
                    "data": {
                        "num_rows": 2,
                        "num_cols": 2,
                        "grid": [
                            [{"text": "Fixture"}, {"text": "DFU"}],
                            [{"text": "Sink"}, {"text": "2"}],
                        ],
                    },
                },
                {
                    "self_ref": "#/tables/1",
                    "data": {
                        "num_rows": 2,
                        "num_cols": 2,
                        "grid": [
                            [{"text": "Fixture"}, {"text": "DFU"}],
                            [{"text": "Lavatory"}, {"text": "1"}],
                        ],
                    },
                },
            ],
        }

    def num_pages(self) -> int:
        return 4


class FakeConverter:
    def convert(self, source_path, **kwargs):
        return SimpleNamespace(document=FakeDocument())


class FakeTitlelessDocument:
    def __init__(self) -> None:
        self.name = "12345678-1234-1234-1234-1234567890ab"

    def iterate_items(self):
        yield (
            SimpleNamespace(
                text="The Bitter Lesson",
                label="text",
                prov=[SimpleNamespace(page_no=1)],
            ),
            0,
        )
        yield (
            SimpleNamespace(
                text="Rich Sutton",
                label="text",
                prov=[SimpleNamespace(page_no=1)],
            ),
            1,
        )
        yield (
            SimpleNamespace(
                text="General methods that leverage computation are ultimately the most effective.",
                label="text",
                prov=[SimpleNamespace(page_no=1)],
            ),
            2,
        )

    def export_to_dict(self) -> dict:
        return {"name": self.name, "kind": "docling", "texts": [], "pictures": [], "tables": []}

    def num_pages(self) -> int:
        return 1


def test_fallback_document_converter_timeout_is_not_shorter_than_primary(monkeypatch) -> None:
    get_fallback_document_converter.cache_clear()
    captured: dict[str, object] = {}

    class FakeDocumentConverter:
        def __init__(self, *, format_options):
            captured["format_options"] = format_options

    monkeypatch.setattr(
        "app.services.docling_parser.get_settings",
        lambda: SimpleNamespace(
            docling_document_timeout_seconds=120.0,
            docling_fallback_document_timeout_seconds=30.0,
        ),
    )
    monkeypatch.setattr("app.services.docling_parser.DocumentConverter", FakeDocumentConverter)

    converter = get_fallback_document_converter()
    assert isinstance(converter, FakeDocumentConverter)
    options = next(iter(captured["format_options"].values())).pipeline_options

    assert options.document_timeout == 120.0
    get_fallback_document_converter.cache_clear()

    def num_pages(self) -> int:
        return 1


class FakeTitlelessConverter:
    def convert(self, source_path, **kwargs):
        return SimpleNamespace(document=FakeTitlelessDocument())


class FakeNulTableDocument:
    def __init__(self) -> None:
        self.name = "nul-table"

    def iterate_items(self):
        yield (
            SimpleNamespace(
                text="Bridgeport \x00 Southwest",
                label="text",
                prov=[SimpleNamespace(page_no=1)],
            ),
            0,
        )
        yield (
            SimpleNamespace(
                text="TABLE 1",
                label="caption",
                prov=[SimpleNamespace(page_no=1)],
            ),
            1,
        )
        yield (
            SimpleNamespace(
                text="COMMENT MATRIX",
                level=1,
                label="section_header",
                prov=[SimpleNamespace(page_no=1)],
            ),
            1,
        )
        yield (SimpleNamespace(label="table", prov=[SimpleNamespace(page_no=1)]), 1)

    def export_to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": "docling",
            "texts": [],
            "pictures": [],
            "tables": [
                {
                    "self_ref": "#/tables/0",
                    "data": {
                        "num_rows": 2,
                        "num_cols": 2,
                        "grid": [
                            [{"text": "Name"}, {"text": "Value"}],
                            [{"text": "Alpha\x00Beta"}, {"text": "\x00123\x00"}],
                        ],
                    },
                }
            ],
        }

    def num_pages(self) -> int:
        return 1


class FakeNulTableConverter:
    def convert(self, source_path, **kwargs):
        return SimpleNamespace(document=FakeNulTableDocument())


class FakeEmptyDocument:
    def __init__(self) -> None:
        self.name = "12345678-1234-1234-1234-1234567890ab"

    def iterate_items(self):
        if False:
            yield None

    def export_to_dict(self) -> dict:
        return {"name": self.name, "kind": "docling", "texts": [], "pictures": [], "tables": []}

    def num_pages(self) -> int:
        return 6


class FakeEmptyConverter:
    def convert(self, source_path, **kwargs):
        return SimpleNamespace(status="success", errors=[], document=FakeEmptyDocument())


class RecordingConverter:
    def __init__(self, result) -> None:
        self.result = result
        self.calls: list[tuple[object, dict]] = []

    def convert(self, source_path, **kwargs):
        self.calls.append((source_path, kwargs))
        return self.result


def test_normalize_chunks_keeps_structural_heading_not_table_heading() -> None:
    snapshots = _snapshot_items(FakeDocument())
    chunks = _normalize_chunks(snapshots)

    assert len(chunks) == 6
    assert chunks[0].heading == "701.1 Applicability"
    assert chunks[1].heading == "701.1 Applicability"
    assert chunks[-1].heading == "701.3 Drainage Fittings"


def test_docling_parser_returns_serialized_document_and_merged_table() -> None:
    parser = DoclingParser(converter=FakeConverter())

    parsed = parser.parse_pdf(source_path=None)  # type: ignore[arg-type]

    assert parsed.title == "701.1 Applicability"
    assert parsed.page_count == 4
    assert parsed.yaml_text.startswith("name: sample")
    assert "kind: docling" in parsed.yaml_text
    assert '"name": "sample"' in parsed.docling_json
    assert len(parsed.chunks) == 6
    assert len(parsed.tables) == 1
    assert len(parsed.figures) == 2
    assert (
        parsed.tables[0].title == "TABLE 701.2 MATERIALS FOR DRAIN, WASTE, VENT PIPE AND FITTINGS"
    )
    assert parsed.tables[0].row_count == 3
    assert parsed.tables[0].metadata["header_rows_removed_count"] == 1
    assert "Lavatory" in parsed.tables[0].search_text
    assert parsed.figures[0].caption == "UpCodes Diagram (1) Island Fixture Venting (UPC)"
    assert parsed.figures[0].metadata["caption_resolution_source"] == "nearby_group_label"
    assert parsed.figures[0].metadata["provenance"][0]["bbox"]["coord_origin"] == "BOTTOMLEFT"
    assert parsed.figures[1].caption == "Fixture Venting Diagram"
    assert parsed.figures[1].metadata["caption_resolution_source"] == "explicit_ref"


def test_docling_parser_uses_first_meaningful_text_for_title_when_headings_are_absent() -> None:
    parser = DoclingParser(converter=FakeTitlelessConverter())

    parsed = parser.parse_pdf(source_path=None)  # type: ignore[arg-type]

    assert parsed.title == "The Bitter Lesson"


def test_docling_parser_strips_nul_bytes_from_normalized_text_fields() -> None:
    parser = DoclingParser(converter=FakeNulTableConverter())

    parsed = parser.parse_pdf(source_path=None)  # type: ignore[arg-type]

    assert parsed.title == "Bridgeport Southwest"
    assert parsed.chunks[0].text == "Bridgeport Southwest"
    assert parsed.tables[0].rows == [["Name", "Value"], ["Alpha Beta", "123"]]
    assert "\x00" not in parsed.tables[0].search_text
    assert "\x00" not in parsed.tables[0].preview_text
    assert "Alpha Beta" in parsed.tables[0].search_text


def test_docling_parser_uses_fallback_converter_after_non_successful_primary_result() -> None:
    primary = RecordingConverter(
        SimpleNamespace(
            status="partial_success",
            errors=["document timeout"],
            document=FakeDocument(),
        )
    )
    fallback = RecordingConverter(
        SimpleNamespace(
            status="success",
            errors=[],
            document=FakeTitlelessDocument(),
        )
    )
    parser = DoclingParser(converter=primary, fallback_converter=fallback)

    parsed = parser.parse_pdf(Path("/tmp/sample.pdf"))

    assert parsed.title == "The Bitter Lesson"
    assert len(primary.calls) == 1
    assert primary.calls[0][1]["raises_on_error"] is False
    assert len(fallback.calls) == 1
    assert fallback.calls[0][1]["raises_on_error"] is False


def test_docling_parser_uses_timeout_rescue_converter_after_timeout_failures() -> None:
    primary = RecordingConverter(
        SimpleNamespace(
            status="partial_success",
            errors=["document timeout exceeded"],
            document=FakeDocument(),
        )
    )
    fallback = RecordingConverter(
        SimpleNamespace(
            status="partial_success",
            errors=["Page 153: document timeout exceeded"],
            document=FakeDocument(),
        )
    )
    timeout_rescue = RecordingConverter(
        SimpleNamespace(
            status="success",
            errors=[],
            document=FakeTitlelessDocument(),
        )
    )
    parser = DoclingParser(
        converter=primary,
        fallback_converter=fallback,
        timeout_rescue_converter=timeout_rescue,
    )

    parsed = parser.parse_pdf(Path("/tmp/sample.pdf"))

    assert parsed.title == "The Bitter Lesson"
    assert len(primary.calls) == 1
    assert len(fallback.calls) == 1
    assert len(timeout_rescue.calls) == 1
    assert timeout_rescue.calls[0][1]["raises_on_error"] is False


def test_docling_parser_uses_timeout_rescue_after_partial_success() -> None:
    primary = RecordingConverter(
        SimpleNamespace(
            status="partial_success",
            errors=["Page 220: document timeout exceeded"],
            document=FakeDocument(),
        )
    )
    fallback = RecordingConverter(
        SimpleNamespace(
            status="partial_success",
            errors=[],
            document=FakeDocument(),
        )
    )
    timeout_rescue = RecordingConverter(
        SimpleNamespace(
            status="success",
            errors=[],
            document=FakeTitlelessDocument(),
        )
    )
    parser = DoclingParser(
        converter=primary,
        fallback_converter=fallback,
        timeout_rescue_converter=timeout_rescue,
    )

    parsed = parser.parse_pdf(Path("/tmp/sample.pdf"))

    assert parsed.title == "The Bitter Lesson"
    assert len(primary.calls) == 1
    assert len(fallback.calls) == 1
    assert len(timeout_rescue.calls) == 1
    assert timeout_rescue.calls[0][1]["raises_on_error"] is False


def test_docling_parser_raises_when_primary_and_fallback_conversion_fail() -> None:
    primary = RecordingConverter(
        SimpleNamespace(
            status="partial_success",
            errors=["document timeout"],
            document=FakeDocument(),
        )
    )
    fallback = RecordingConverter(
        SimpleNamespace(
            status="failure",
            errors=["backend text extraction failed"],
            document=FakeDocument(),
        )
    )
    parser = DoclingParser(converter=primary, fallback_converter=fallback)

    with pytest.raises(
        ValueError,
        match=(
            "Docling conversion failed after fallback for sample.pdf: "
            "status=failure; backend text extraction failed"
        ),
    ):
        parser.parse_pdf(Path("/tmp/sample.pdf"))


def test_docling_parser_creates_synthetic_title_chunk_for_zero_text_documents() -> None:
    parser = DoclingParser(converter=FakeEmptyConverter())

    parsed = parser.parse_pdf(
        Path("/tmp/Chalk Buttes All Maps.pdf"),
        source_filename="Chalk Buttes All Maps.pdf",
    )

    assert parsed.title == "Chalk Buttes All Maps"
    assert len(parsed.chunks) == 1
    assert parsed.chunks[0].text == "Chalk Buttes All Maps"
    assert parsed.chunks[0].heading == "Chalk Buttes All Maps"
    assert parsed.chunks[0].page_from == 1
    assert parsed.chunks[0].metadata["synthetic"] is True
    assert parsed.chunks[0].metadata["synthetic_source"] == "document_title_fallback"
