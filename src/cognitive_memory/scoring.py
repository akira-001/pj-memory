"""Scoring functions: time decay, adaptive half-life, cosine similarity."""

from __future__ import annotations

import math
from datetime import datetime
from typing import List


def adaptive_half_life(arousal: float, base_half_life: float = 60.0) -> float:
    """High-arousal memories decay slower. arousal 1.0 → half-life doubles."""
    return base_half_life * (1 + arousal)


def time_decay(
    entry_date: str,
    arousal: float,
    base_half_life: float = 60.0,
    floor: float = 0.3,
) -> float:
    """Forgetting curve with arousal-adaptive half-life and floor."""
    try:
        days_old = (datetime.now() - datetime.fromisoformat(entry_date)).days
    except ValueError:
        days_old = 0
    if days_old <= 0:
        return 1.0
    half_life = adaptive_half_life(arousal, base_half_life)
    decay = math.pow(0.5, days_old / half_life)
    return max(decay, floor)


def cosine_sim(a: List[float], b: List[float]) -> float:
    """Cosine similarity for pre-normalized vectors (dot product)."""
    return sum(x * y for x, y in zip(a, b))


def normalize(vec: List[float]) -> List[float]:
    """L2-normalize a vector."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]
