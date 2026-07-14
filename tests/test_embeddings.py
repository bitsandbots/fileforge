"""Tests for embedding generation and near-duplicate detection."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import openai

from fileforge.analysis.embeddings import find_near_duplicates, generate_embedding
from fileforge.models import FileRecord


def _make_record(name: str, embedding: list[float] | None = None) -> FileRecord:
    now = datetime.now(UTC)
    return FileRecord(
        path=Path(name),
        name=name,
        extension=Path(name).suffix,
        size_bytes=100,
        modified_at=now,
        created_at=now,
        embedding=embedding,
    )


def test_generate_embedding_returns_vector() -> None:
    """generate_embedding returns a list of floats (mocked)."""
    mock_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    mock_data = MagicMock()
    mock_data.embedding = mock_embedding
    mock_response = MagicMock()
    mock_response.data = [mock_data]

    with patch("fileforge.analysis.embeddings.openai.OpenAI") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.embeddings.create.return_value = mock_response
        result = generate_embedding("test text", model="mxbai-embed-large-v1-F16")
        assert result == mock_embedding
        mock_client.embeddings.create.assert_called_once()


def test_generate_embedding_empty_text_returns_empty() -> None:
    """generate_embedding returns [] for blank input without calling llama-server."""
    with patch("fileforge.analysis.embeddings.openai.OpenAI") as mock_client_cls:
        assert generate_embedding("") == []
        assert generate_embedding("   ") == []
        mock_client_cls.assert_not_called()


def test_generate_embedding_graceful_on_connection_error() -> None:
    """generate_embedding returns [] when llama-server is unreachable."""
    with patch("fileforge.analysis.embeddings.openai.OpenAI") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.embeddings.create.side_effect = ConnectionError("refused")
        result = generate_embedding("some text")
        assert result == []


def test_find_near_duplicates() -> None:
    """Near-duplicate detection finds similar content."""
    record1 = _make_record("doc1.txt", [0.9, 0.85, 0.8, 0.75, 0.7])
    record2 = _make_record("doc2.txt", [0.89, 0.84, 0.79, 0.74, 0.69])  # very similar
    record3 = _make_record("unrelated.txt", [0.0, 0.0, 0.0, 0.0, 1.0])  # orthogonal

    groups = find_near_duplicates([record1, record2, record3], threshold=0.85)

    assert len(groups) == 1
    assert len(groups[0]) == 2
    assert record1 in groups[0]
    assert record2 in groups[0]


def test_find_near_duplicates_skips_missing_embeddings() -> None:
    """Records without embeddings are excluded from grouping."""
    with_emb = _make_record("doc1.txt", [0.5, 0.5, 0.5])
    without_emb = _make_record("doc2.txt", None)

    groups = find_near_duplicates([with_emb, without_emb], threshold=0.9)
    assert groups == []


def test_find_near_duplicates_below_threshold_not_grouped() -> None:
    """Records below the similarity threshold stay separate."""
    record_a = _make_record("a.txt", [1.0, 0.0, 0.0])
    record_b = _make_record("b.txt", [0.0, 1.0, 0.0])

    groups = find_near_duplicates([record_a, record_b], threshold=0.9)
    assert groups == []
