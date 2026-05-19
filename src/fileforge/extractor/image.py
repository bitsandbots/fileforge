"""Image OCR extraction using pytesseract (optional dependency).

Install the ``[ocr]`` extra and the Tesseract binary to enable:

    pip install "fileforge[ocr]"
    # Linux:  sudo apt install tesseract-ocr
    # macOS:  brew install tesseract

When either is unavailable, extract() returns None and scanning continues
normally — images are hashed and classified by filename only.
"""

from __future__ import annotations

import logging
from pathlib import Path

_log = logging.getLogger(__name__)

try:
    from PIL import Image

    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

try:
    import pytesseract

    _PYTESSERACT_AVAILABLE = True
except ImportError:
    _PYTESSERACT_AVAILABLE = False

_AVAILABLE = _PIL_AVAILABLE and _PYTESSERACT_AVAILABLE


# Extensions handled by this extractor
IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
    ".gif",
}


def available() -> bool:
    """Return True if pytesseract and Tesseract binary are both usable."""
    if not _AVAILABLE:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def extract(path: Path, max_chars: int = 2000) -> str | None:
    """Extract text from an image file via OCR.

    Converts the image to grayscale before passing to Tesseract, which
    improves recognition accuracy on most document scans and screenshots.

    Requires the ``[ocr]`` extra (pytesseract + Pillow) and the Tesseract
    binary. Returns None silently when either is unavailable.

    Args:
        path: Path to the image file.
        max_chars: Maximum characters to return.

    Returns:
        OCR text snippet, or None if OCR is unavailable or produces no text.
    """
    if not _AVAILABLE:
        return None

    try:
        with Image.open(path) as img:
            gray = img.convert("L")
            text = pytesseract.image_to_string(gray)
    except pytesseract.TesseractNotFoundError:
        _log.warning(
            "Tesseract binary not found — install tesseract-ocr and add it to PATH"
        )
        return None

    text = text.strip()
    return text[:max_chars] if text else None
