"""Tests for context module: SearchCache and filter_flashbacks."""

from __future__ import annotations

import pytest

from cognitive_memory.context import SearchCache, filter_flashbacks
from cognitive_memory.scoring import normalize
from cognitive_memory.types import SearchResponse, SearchResult


# ---------------------------------------------------------------------------
# SearchCache tests
# ---------------------------------------------------------------------------


class TestSearchCache:
    """Tests for SearchCache class."""

    def _make_response(self, label: str = "ok") -> SearchResponse:
        return SearchResponse(
            results=[
                SearchResult(
                    score=0.9,
                    date="2026-03-21",
                    content=f"result-{label}",
                    arousal=0.7,
                    source="semantic",
                    cosine_sim=0.85,
                )
            ],
            status="ok",
        )

    def test_put_and_get_exact_match(self):
        cache = SearchCache(max_size=20, sim_threshold=0.9)
        vec = normalize([1.0, 0.0, 0.0, 0.0])
        resp = self._make_response("exact")

        cache.put(vec, resp)
        got = cache.get(vec)

        assert got is not None
        assert got.results[0].content == "result-exact"

    def test_get_similar_vector_hits(self):
        cache = SearchCache(max_size=20, sim_threshold=0.9)
        vec1 = normalize([1.0, 0.0, 0.0, 0.0])
        # Slightly perturbed — still very similar
        vec2 = normalize([1.0, 0.05, 0.0, 0.0])
        resp = self._make_response("similar")

        cache.put(vec1, resp)
        got = cache.get(vec2)

        assert got is not None
        assert got.results[0].content == "result-similar"

    def test_get_dissimilar_vector_misses(self):
        cache = SearchCache(max_size=20, sim_threshold=0.9)
        vec1 = normalize([1.0, 0.0, 0.0, 0.0])
        vec2 = normalize([0.0, 0.0, 0.0, 1.0])
        resp = self._make_response("miss")

        cache.put(vec1, resp)
        got = cache.get(vec2)

        assert got is None

    def test_max_size_eviction(self):
        # Use higher dimension so 21 vectors can all be dissimilar
        dim = 32
        cache = SearchCache(max_size=20, sim_threshold=0.9)

        # Create 21 near-orthogonal vectors using one-hot-like pattern
        vecs = []
        for i in range(21):
            v = [0.0] * dim
            v[i] = 1.0
            vec = normalize(v)
            vecs.append(vec)
            cache.put(vec, self._make_response(str(i)))

        # First entry should be evicted (FIFO)
        assert cache.get(vecs[0]) is None
        # Last entry should still be present
        got = cache.get(vecs[20])
        assert got is not None
        assert got.results[0].content == "result-20"

    def test_clear(self):
        cache = SearchCache(max_size=20, sim_threshold=0.9)
        vec = normalize([1.0, 0.0, 0.0, 0.0])
        cache.put(vec, self._make_response("clear"))

        cache.clear()
        assert cache.get(vec) is None


# ---------------------------------------------------------------------------
# filter_flashbacks tests
# ---------------------------------------------------------------------------


class TestFilterFlashbacks:
    """Tests for filter_flashbacks function."""

    def _result(
        self,
        cosine_sim: float | None = 0.8,
        arousal: float = 0.7,
        source: str = "semantic",
    ) -> SearchResult:
        return SearchResult(
            score=0.9,
            date="2026-03-21",
            content="test entry",
            arousal=arousal,
            source=source,
            cosine_sim=cosine_sim,
        )

    def test_filters_below_sim_threshold(self):
        results = [self._result(cosine_sim=0.5, arousal=0.7)]
        filtered = filter_flashbacks(results)  # default sim_threshold=0.65
        assert len(filtered) == 0

    def test_filters_below_arousal_threshold(self):
        results = [self._result(cosine_sim=0.8, arousal=0.3)]
        filtered = filter_flashbacks(results)  # default arousal_threshold=0.5
        assert len(filtered) == 0

    def test_passes_above_both_thresholds(self):
        results = [self._result(cosine_sim=0.8, arousal=0.7)]
        filtered = filter_flashbacks(results)
        assert len(filtered) == 1
        assert filtered[0].cosine_sim == 0.8

    def test_empty_results_returns_empty(self):
        filtered = filter_flashbacks([])
        assert filtered == []

    def test_grep_results_skipped(self):
        results = [self._result(cosine_sim=None, arousal=0.9, source="grep")]
        filtered = filter_flashbacks(results)
        assert len(filtered) == 0

    def test_custom_thresholds(self):
        results = [self._result(cosine_sim=0.4, arousal=0.3)]
        filtered = filter_flashbacks(
            results, sim_threshold=0.3, arousal_threshold=0.2
        )
        assert len(filtered) == 1

    def test_arousal_above_one_passes(self):
        # arousal > 1.0 is not clamped; values above threshold still pass
        results = [self._result(cosine_sim=0.8, arousal=1.5)]
        filtered = filter_flashbacks(results)
        assert len(filtered) == 1
        assert filtered[0].arousal == 1.5
