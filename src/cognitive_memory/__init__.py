"""Cognitive Memory — human-like cognitive memory for AI agents."""

from __future__ import annotations

from ._version import __version__
from .config import CogMemConfig
from .context import SearchCache, filter_flashbacks
from .store import MemoryStore
from .types import MemoryEntry, SearchResponse, SearchResult


def search(query: str, top_k: int = 5, config: CogMemConfig | None = None) -> SearchResponse:
    """Convenience function: auto-find cogmem.toml and search."""
    if config is None:
        config = CogMemConfig.find_and_load()
    with MemoryStore(config) as store:
        return store.search(query, top_k)


__all__ = [
    "__version__",
    "CogMemConfig",
    "MemoryEntry",
    "MemoryStore",
    "SearchCache",
    "SearchResponse",
    "SearchResult",
    "filter_flashbacks",
    "search",
]
