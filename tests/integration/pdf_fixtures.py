from __future__ import annotations


def valid_test_pdf_bytes(*, marker: str = "integration-test") -> bytes:
    return (
        b"%PDF-1.1\n"
        + f"% {marker}\n".encode("ascii")
        + b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        + b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        + b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]>>endobj\n"
        + b"trailer<</Root 1 0 R>>\n"
        + b"%%EOF\n"
    )
