"""Embedding provider protocol (duck-typing interface)."""

from __future__ import annotations

from typing import List, Optional, Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for embedding providers. Implement embed and embed_batch."""

    def embed(self, text: str) -> Optional[List[float]]:
        """Embed a single text. Returns None on failure."""
        ...

    def embed_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Embed multiple texts. Returns None on failure."""
        ...
