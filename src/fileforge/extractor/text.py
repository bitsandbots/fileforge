"""Plain text content extraction (txt, md, code files, etc.)."""

from __future__ import annotations

from pathlib import Path

import chardet

# Extensions handled by this extractor
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".rst",
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".cs",
    ".go",
    ".rb",
    ".php",
    ".sh",
    ".bash",
    ".zsh",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".xml",
    ".css",
    ".scss",
    ".sass",
    ".sql",
    ".r",
    ".swift",
    ".kt",
    ".lua",
}


def extract(path: Path, max_chars: int = 2000) -> str | None:
    """Extract text content from a plain text or code file.

    Args:
        path: Path to the file.
        max_chars: Maximum characters to return.

    Returns:
        Extracted text snippet, or None if unreadable.
    """
    raw = path.read_bytes()
    detected = chardet.detect(raw)
    encoding = detected.get("encoding") or "utf-8"

    try:
        text = raw.decode(encoding, errors="replace")
    except (LookupError, UnicodeDecodeError):
        text = raw.decode("utf-8", errors="replace")

    return text[:max_chars] if text.strip() else None
