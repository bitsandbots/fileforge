"""Content extraction dispatcher — routes files to the right extractor."""

from __future__ import annotations

import logging
from pathlib import Path

_log = logging.getLogger(__name__)

from fileforge.extractor import docx as _docx
from fileforge.extractor import pdf as _pdf
from fileforge.extractor import text as _text

# Map extension → extractor module. Expand as phases add more extractors.
_DISPATCH: dict[str, object] = {}

for ext in _text.TEXT_EXTENSIONS:
    _DISPATCH[ext] = _text

_DISPATCH[".docx"] = _docx
_DISPATCH[".pdf"] = _pdf


def extract_snippet(path: Path, max_chars: int = 2000) -> str | None:
    """Extract a content snippet from a file using the appropriate extractor.

    Args:
        path: Path to the file to extract from.
        max_chars: Maximum characters in the returned snippet.

    Returns:
        Extracted text, or None if the file type is unsupported or unreadable.
    """
    ext = path.suffix.lower()
    module = _DISPATCH.get(ext)
    if module is None:
        return None
    try:
        return module.extract(path, max_chars=max_chars)
    except Exception:
        _log.debug("Extraction failed for %s", path, exc_info=True)
        return None
