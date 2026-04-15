"""DOCX content extraction using python-docx."""

from __future__ import annotations

from pathlib import Path

from docx import Document


def extract(path: Path, max_chars: int = 2000) -> str | None:
    """Extract paragraph text from a DOCX file.

    Args:
        path: Path to the .docx file.
        max_chars: Maximum characters to return.

    Returns:
        Concatenated paragraph text, or None if the document is empty.
    """
    doc = Document(str(path))
    parts: list[str] = []
    total = 0

    for para in doc.paragraphs:
        if total >= max_chars:
            break
        text = para.text.strip()
        if text:
            remaining = max_chars - total
            parts.append(text[:remaining])
            total += len(text)

    combined = "\n".join(parts).strip()
    return combined if combined else None
