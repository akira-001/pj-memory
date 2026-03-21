"""Tests for scoring module: time_decay, adaptive_half_life, cosine_sim, normalize."""

import math
from datetime import datetime, timedelta

import pytest

from cognitive_memory.scoring import (
    adaptive_half_life,
    cosine_sim,
    normalize,
    time_decay,
)


class TestAdaptiveHalfLife:
    def test_zero_arousal(self):
        assert adaptive_half_life(0.0, 60) == 60.0

    def test_full_arousal(self):
        assert adaptive_half_life(1.0, 60) == 120.0

    def test_half_arousal(self):
        assert adaptive_half_life(0.5, 60) == 90.0

    def test_custom_base(self):
        assert adaptive_half_life(0.0, 30) == 30.0
        assert adaptive_half_life(1.0, 30) == 60.0


class TestTimeDecay:
    def test_recent_entry_no_decay(self):
        today = datetime.now().strftime("%Y-%m-%d")
        assert time_decay(today, 0.5) == 1.0

    def test_old_entry_floors_at_03(self):
        old_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        result = time_decay(old_date, 0.0)
        assert result == 0.3

    def test_high_arousal_decays_slower(self):
        date_90d = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        decay_low = time_decay(date_90d, 0.2)
        decay_high = time_decay(date_90d, 0.8)
        assert decay_high > decay_low

    def test_invalid_date_returns_1(self):
        assert time_decay("not-a-date", 0.5) == 1.0

    def test_custom_floor(self):
        old_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        result = time_decay(old_date, 0.0, floor=0.1)
        assert result == 0.1

    def test_future_date_returns_1(self):
        future = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        assert time_decay(future, 0.5) == 1.0


class TestCosineSim:
    def test_identical_vectors(self):
        v = normalize([1.0, 0.0, 0.0])
        assert abs(cosine_sim(v, v) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        a = normalize([1.0, 0.0])
        b = normalize([0.0, 1.0])
        assert abs(cosine_sim(a, b)) < 1e-6

    def test_opposite_vectors(self):
        a = normalize([1.0, 0.0])
        b = normalize([-1.0, 0.0])
        assert abs(cosine_sim(a, b) - (-1.0)) < 1e-6


class TestNormalize:
    def test_unit_vector_unchanged(self):
        v = [1.0, 0.0, 0.0]
        result = normalize(v)
        assert abs(sum(x * x for x in result) - 1.0) < 1e-6

    def test_normalize_general_vector(self):
        v = [3.0, 4.0]
        result = normalize(v)
        assert abs(result[0] - 0.6) < 1e-6
        assert abs(result[1] - 0.8) < 1e-6

    def test_zero_vector_unchanged(self):
        v = [0.0, 0.0, 0.0]
        result = normalize(v)
        assert result == v


class TestScoringFormula:
    def test_additive_scoring(self):
        sim, arousal, decay = 0.9, 0.0, 1.0
        score = (0.7 * sim + 0.3 * arousal) * decay
        assert abs(score - 0.63) < 0.01

    def test_high_arousal_boosts_score(self):
        sim, arousal, decay = 0.6, 1.0, 1.0
        score = (0.7 * sim + 0.3 * arousal) * decay
        assert abs(score - 0.72) < 0.01

    def test_decay_reduces_score(self):
        sim, arousal = 0.9, 0.5
        score_full = (0.7 * sim + 0.3 * arousal) * 1.0
        score_half = (0.7 * sim + 0.3 * arousal) * 0.5
        assert score_full > score_half
