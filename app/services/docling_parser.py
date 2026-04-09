from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter


@dataclass
class ParsedChunk:
    chunk_index: int
    text: str
    heading: str | None
    page_from: int | None
    page_to: int | None
    metadata: dict[str, Any]
    embedding: list[float] | None = None


@dataclass
class ParsedDocument:
    title: str | None
    page_count: int
    markdown: str
    docling_json: str
    chunks: list[ParsedChunk]


@lru_cache(maxsize=1)
def get_document_converter() -> DocumentConverter:
    return DocumentConverter()


def _collect_page_range(item: Any) -> tuple[int | None, int | None]:
    provenances = getattr(item, "prov", None) or []
    if not provenances:
        return None, None

    page_numbers = [prov.page_no for prov in provenances if getattr(prov, "page_no", None) is not None]
    if not page_numbers:
        return None, None
    return min(page_numbers), max(page_numbers)


def _normalize_chunks(docling_document: Any) -> list[ParsedChunk]:
    chunks: list[ParsedChunk] = []
    current_heading: str | None = None

    for item, _level in docling_document.iterate_items():
        text = getattr(item, "text", None)
        if not text:
            continue

        normalized_text = str(text).strip()
        if not normalized_text:
            continue

        page_from, page_to = _collect_page_range(item)
        label = str(getattr(item, "label", ""))
        metadata = {"label": label}

        if hasattr(item, "level"):
            metadata["level"] = getattr(item, "level")
            current_heading = normalized_text
            continue

        chunks.append(
            ParsedChunk(
                chunk_index=len(chunks),
                text=normalized_text,
                heading=current_heading,
                page_from=page_from,
                page_to=page_to,
                metadata=metadata,
            )
        )

    return chunks


class DoclingParser:
    def __init__(self, converter: DocumentConverter | None = None) -> None:
        self.converter = converter or get_document_converter()

    def parse_pdf(self, source_path: Path) -> ParsedDocument:
        result = self.converter.convert(source_path)
        document = result.document
        markdown = document.export_to_markdown()
        docling_json = json.dumps(document.export_to_dict(), indent=2)
        chunks = _normalize_chunks(document)
        title = next((chunk.heading for chunk in chunks if chunk.heading), None) or document.name

        return ParsedDocument(
            title=title,
            page_count=document.num_pages(),
            markdown=markdown,
            docling_json=docling_json,
            chunks=chunks,
        )
