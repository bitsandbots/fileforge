"""Embedding-based similarity detection for near-duplicates."""

from __future__ import annotations

import logging
from collections import defaultdict

import ollama

from fileforge.models import FileRecord

_log = logging.getLogger(__name__)


def generate_embedding(text: str, model: str = "nomic-embed-text") -> list[float]:
    """Generate an embedding for text using Ollama.

    Args:
        text: Text to embed.
        model: Ollama model name.

    Returns:
        List of floats representing the embedding.
        Returns empty list on error (graceful degradation).
    """
    if not text or not text.strip():
        return []

    try:
        response = ollama.embeddings(
            model=model,
            prompt=text,
        )
        return response.get("embedding", [])
    except (ollama.ResponseError, ollama.RequestError, ConnectionError, TimeoutError):
        _log.warning("Ollama unavailable for embedding; skipping")
        return []


def find_near_duplicates(
    records: list[FileRecord],
    threshold: float = 0.92,
) -> list[list[FileRecord]]:
    """Group records with similar embeddings.

    Uses cosine similarity. Records without embeddings are excluded.

    Args:
        records: FileRecords with embeddings.
        threshold: Similarity threshold (0-1). 1.0 = identical, 0.5 = moderate.

    Returns:
        List of groups. Each group has 2+ similar records.
    """
    from scipy.spatial.distance import cosine

    with_embeddings = [r for r in records if r.embedding]
    if len(with_embeddings) < 2:
        return []

    groups: dict[int, list[FileRecord]] = defaultdict(list)
    used: set[int] = set()

    for i, record_a in enumerate(with_embeddings):
        if i in used:
            continue

        group = [record_a]
        used.add(i)

        for j in range(i + 1, len(with_embeddings)):
            if j in used:
                continue
            record_b = with_embeddings[j]

            similarity = 1 - cosine(record_a.embedding, record_b.embedding)
            if similarity >= threshold:
                group.append(record_b)
                used.add(j)

        if len(group) > 1:
            groups[i] = group

    return list(groups.values())
