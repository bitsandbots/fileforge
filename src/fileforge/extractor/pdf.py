"""PDF content extraction using pdfplumber."""

from __future__ import annotations

from pathlib import Path

import pdfplumber


def extract(path: Path, max_chars: int = 2000) -> str | None:
    """Extract text from a PDF file.

    Iterates pages until max_chars is reached. Falls back gracefully
    if a page has no extractable text (scanned/image-only pages).

    Args:
        path: Path to the PDF file.
        max_chars: Maximum characters to extract.

    Returns:
        Extracted text snippet, or None if no text found.
    """
    parts: list[str] = []
    total = 0

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            if total >= max_chars:
                break
            text = page.extract_text() or ""
            remaining = max_chars - total
            parts.append(text[:remaining])
            total += len(text)

    combined = "\n".join(parts).strip()
    return combined if combined else None
