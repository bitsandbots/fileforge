"""Tests for content extractors."""

from __future__ import annotations

from pathlib import Path

from fileforge.extractor import extract_snippet


def test_extract_plain_text(tmp_dir: Path) -> None:
    """Plain .txt file returns its content as snippet."""
    f = tmp_dir / "HARNESS_doc.txt"
    f.write_text("This is a consulting proposal for a nonprofit.")
    snippet = extract_snippet(f, max_chars=2000)
    assert "consulting proposal" in snippet


def test_extract_markdown(tmp_dir: Path) -> None:
    """Markdown file returns text content."""
    f = tmp_dir / "HARNESS_readme.md"
    f.write_text("# Project\n\nThis project handles hydroponics automation.\n")
    snippet = extract_snippet(f, max_chars=2000)
    assert "hydroponics" in snippet


def test_extract_python(tmp_dir: Path) -> None:
    """Python source file returns its content."""
    f = tmp_dir / "HARNESS_main.py"
    f.write_text('def hello():\n    """Greet the user."""\n    return "hello"\n')
    snippet = extract_snippet(f, max_chars=2000)
    assert "def hello" in snippet


def test_extract_truncates_at_max_chars(tmp_dir: Path) -> None:
    """Snippet is capped at max_chars."""
    f = tmp_dir / "HARNESS_long.txt"
    f.write_text("x" * 5000)
    snippet = extract_snippet(f, max_chars=100)
    assert len(snippet) <= 100


def test_extract_unknown_binary_returns_none(tmp_dir: Path) -> None:
    """Unknown binary extension returns None (metadata-only record)."""
    f = tmp_dir / "HARNESS_blob.xyz"
    f.write_bytes(bytes(range(256)))
    snippet = extract_snippet(f, max_chars=2000)
    assert snippet is None


def test_extract_handles_encoding_detection(tmp_dir: Path) -> None:
    """Files with non-UTF-8 encoding are read without raising."""
    f = tmp_dir / "HARNESS_latin.txt"
    f.write_bytes("Résumé professionnel\n".encode("latin-1"))
    snippet = extract_snippet(f, max_chars=2000)
    assert snippet is not None
    assert len(snippet) > 0


def test_extract_docx_error_returns_none(tmp_dir: Path) -> None:
    """DOCX extraction on a non-DOCX file returns None gracefully."""
    f = tmp_dir / "HARNESS_fake.docx"
    f.write_bytes(b"not a real docx file")
    snippet = extract_snippet(f, max_chars=2000)
    assert snippet is None


def test_extract_whitespace_only_returns_none(tmp_dir: Path) -> None:
    """A file containing only whitespace returns None (no useful content)."""
    f = tmp_dir / "HARNESS_blank.txt"
    f.write_text("   \n\t\n   ")
    snippet = extract_snippet(f, max_chars=2000)
    assert snippet is None


def test_extract_pdf_corrupt_returns_none(tmp_dir: Path) -> None:
    """PDF extraction on a corrupt (non-PDF) file returns None gracefully."""
    f = tmp_dir / "HARNESS_corrupt.pdf"
    f.write_bytes(b"this is not a real pdf file")
    snippet = extract_snippet(f, max_chars=2000)
    assert snippet is None
