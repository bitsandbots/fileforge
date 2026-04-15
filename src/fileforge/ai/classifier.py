"""LLM-based file classification via local Ollama."""

from __future__ import annotations

from pathlib import Path

import ollama

_SYSTEM_PROMPT = """\
You are a file classification assistant. Given a file's name, type, \
and content snippet, assign it to a category path (up to 3 levels deep) \
using slash notation. Respond with ONLY the category path, nothing else.

Examples:
- Work/Consulting/Proposals
- Personal/Finance/Tax Returns
- Projects/hydroMazing/Documentation
- Reference/Technical/Networking
- Temporary/Downloads"""

_USER_TEMPLATE = """\
User context hints: {hints}

File: {filename}
Type: {extension}
Content: {snippet}

Category path:"""


def parse_category(raw: str) -> str:
    """Clean and validate a raw LLM category response.

    Args:
        raw: Raw text response from the LLM.

    Returns:
        Trimmed category path, or 'Uncategorized' if empty.
    """
    cleaned = raw.strip()
    return cleaned if cleaned else "Uncategorized"


def classify_file(
    path: Path,
    snippet: str | None,
    model: str,
    hints: str,
) -> str:
    """Classify a file using the local Ollama LLM.

    Args:
        path: Path to the file (used for name and extension).
        snippet: Extracted content snippet, or None for metadata-only.
        model: Ollama model name (e.g. 'qwen3:4b').
        hints: User-provided context hints to guide classification.

    Returns:
        Category path string (e.g. 'Work/Consulting/Proposals').
        Returns 'Uncategorized' on any error.
    """
    user_msg = _USER_TEMPLATE.format(
        hints=hints or "No specific hints provided.",
        filename=path.name,
        extension=path.suffix or "unknown",
        snippet=snippet or "(no extractable content — classify by name/type only)",
    )

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            options={"temperature": 0.1},  # low temp for consistent output
        )
        return parse_category(response.message.content)
    except (ollama.ResponseError, ollama.RequestError):
        return "Uncategorized"
