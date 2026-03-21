"""Context search utilities: SearchCache and flashback filtering."""

from __future__ import annotations

from collections import OrderedDict
from typing import List, Optional

from .scoring import cosine_sim, normalize
from .types import SearchResponse, SearchResult


class SearchCache:
    """Session-scoped in-memory query embedding cache.

    Stores query vectors and their search responses. Cache lookup uses
    cosine similarity to find a stored vector close enough to the query.
    """

    def __init__(self, max_size: int = 20, sim_threshold: float = 0.9) -> None:
        self._max_size = max_size
        self._sim_threshold = sim_threshold
        # OrderedDict preserves insertion order for FIFO eviction
        self._store: OrderedDict[int, tuple[List[float], SearchResponse]] = (
            OrderedDict()
        )
        self._next_id = 0

    def get(self, query_vec: List[float]) -> Optional[SearchResponse]:
        """Find cached response by vector similarity > sim_threshold."""
        query_vec = normalize(query_vec)
        for _key, (stored_vec, response) in self._store.items():
            sim = cosine_sim(query_vec, stored_vec)
            if sim >= self._sim_threshold:
                return response
        return None

    def put(self, query_vec: List[float], response: SearchResponse) -> None:
        """Store result. Evict oldest entry (FIFO) if max_size exceeded."""
        query_vec = normalize(query_vec)
        entry_id = self._next_id
        self._next_id += 1
        self._store[entry_id] = (query_vec, response)

        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def clear(self) -> None:
        """Remove all cached entries."""
        self._store.clear()


def filter_flashbacks(
    results: List[SearchResult],
    sim_threshold: float = 0.65,
    arousal_threshold: float = 0.5,
) -> List[SearchResult]:
    """Filter search results for flashback candidates.

    Keep results where cosine_sim >= sim_threshold AND arousal >= arousal_threshold.
    Skip results where cosine_sim is None (grep results).
    """
    filtered: List[SearchResult] = []
    for r in results:
        if r.cosine_sim is None:
            continue
        if r.cosine_sim >= sim_threshold and r.arousal >= arousal_threshold:
            filtered.append(r)
    return filtered
