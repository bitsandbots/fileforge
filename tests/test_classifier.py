"""Tests for the LLM classifier module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import ollama
import pytest

from fileforge.ai.classifier import classify_file, parse_category


def test_parse_category_clean_path() -> None:
    """A clean slash-path is returned as-is."""
    assert parse_category("Work/Consulting/Proposals") == "Work/Consulting/Proposals"


def test_parse_category_strips_whitespace() -> None:
    """Whitespace around the response is stripped."""
    assert parse_category("  Personal/Finance  \n") == "Personal/Finance"


def test_parse_category_empty_falls_back() -> None:
    """Empty or blank response returns 'Uncategorized'."""
    assert parse_category("") == "Uncategorized"
    assert parse_category("   ") == "Uncategorized"


def test_classify_file_calls_ollama(tmp_dir: Path) -> None:
    """classify_file makes one Ollama chat call and returns a category."""
    f = tmp_dir / "HARNESS_proposal.txt"
    f.write_text("Consulting proposal for a nonprofit.")

    mock_response = MagicMock()
    mock_response.message.content = "Work/Consulting/Proposals"

    with patch("fileforge.ai.classifier.ollama.chat", return_value=mock_response):
        result = classify_file(
            path=f,
            snippet="Consulting proposal for a nonprofit.",
            model="qwen3:4b",
            hints="I am a technology consultant.",
        )

    assert result == "Work/Consulting/Proposals"


def test_classify_file_handles_ollama_error(tmp_dir: Path) -> None:
    """OllamaResponseError returns 'Uncategorized' gracefully."""
    f = tmp_dir / "HARNESS_doc.txt"
    f.write_text("some content")

    with patch(
        "fileforge.ai.classifier.ollama.chat",
        side_effect=ollama.ResponseError("model not found"),
    ):
        result = classify_file(
            path=f,
            snippet="some content",
            model="qwen3:4b",
            hints="",
        )

    assert result == "Uncategorized"


def test_classify_file_handles_connection_error(tmp_dir: Path) -> None:
    """RequestError (Ollama not running) returns 'Uncategorized' gracefully."""
    f = tmp_dir / "HARNESS_doc2.txt"
    f.write_text("some content")

    with patch(
        "fileforge.ai.classifier.ollama.chat",
        side_effect=ollama.RequestError("connection refused"),
    ):
        result = classify_file(
            path=f,
            snippet="some content",
            model="qwen3:4b",
            hints="",
        )

    assert result == "Uncategorized"
