from __future__ import annotations

from types import SimpleNamespace

from app.services.docling_parser import DoclingParser, _normalize_chunks


class FakeDocument:
    def __init__(self) -> None:
        self.name = "sample"

    def iterate_items(self):
        yield (
            SimpleNamespace(text="Section One", level=1, label="section_header", prov=[SimpleNamespace(page_no=1)]),
            0,
        )
        yield (
            SimpleNamespace(text="First paragraph", label="text", prov=[SimpleNamespace(page_no=1)]),
            1,
        )
        yield (
            SimpleNamespace(text="Second paragraph", label="text", prov=[SimpleNamespace(page_no=2)]),
            1,
        )

    def export_to_markdown(self) -> str:
        return "# Section One\n\nFirst paragraph\n\nSecond paragraph"

    def export_to_dict(self) -> dict:
        return {"name": self.name}

    def num_pages(self) -> int:
        return 2


class FakeConverter:
    def convert(self, source_path):
        return SimpleNamespace(document=FakeDocument())


def test_normalize_chunks_tracks_heading_and_pages() -> None:
    chunks = _normalize_chunks(FakeDocument())

    assert len(chunks) == 2
    assert chunks[0].heading == "Section One"
    assert chunks[0].page_from == 1
    assert chunks[1].page_from == 2


def test_docling_parser_returns_serialized_document() -> None:
    parser = DoclingParser(converter=FakeConverter())

    parsed = parser.parse_pdf(source_path=None)  # type: ignore[arg-type]

    assert parsed.title == "Section One"
    assert parsed.page_count == 2
    assert parsed.markdown.startswith("# Section One")
    assert '"name": "sample"' in parsed.docling_json
    assert len(parsed.chunks) == 2
