"""Tests for memory decay logic — human-like forgetting mechanism."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from cognitive_memory.decay import DecayAction, evaluate_entry


class TestEvaluateEntry:
    """Test evaluate_entry() decision logic."""

    # --- Rule 1: High arousal → KEEP ---

    def test_high_arousal_keeps(self):
        """High arousal (>= 0.7) memories persist regardless of recall."""
        result = evaluate_entry(arousal=0.9, recall_count=0, last_recalled=None)
        assert result == DecayAction.KEEP

    def test_arousal_at_threshold_keeps(self):
        """Arousal exactly at threshold (0.7) → KEEP."""
        result = evaluate_entry(arousal=0.7, recall_count=0, last_recalled=None)
        assert result == DecayAction.KEEP

    def test_arousal_just_below_threshold_not_keep(self):
        """Arousal just below threshold (0.69) → should NOT be KEEP."""
        result = evaluate_entry(arousal=0.69, recall_count=0, last_recalled=None)
        assert result != DecayAction.KEEP

    # --- Rule 2: Frequently recalled + recent → KEEP ---

    def test_frequent_recent_recall_keeps(self):
        """recall_count >= 2 with recent recall → KEEP."""
        recent = (datetime.now() - timedelta(days=30)).isoformat()
        result = evaluate_entry(arousal=0.5, recall_count=3, last_recalled=recent)
        assert result == DecayAction.KEEP

    def test_recall_at_threshold_recent_keeps(self):
        """recall_count exactly at threshold (2) with recent recall → KEEP."""
        recent = (datetime.now() - timedelta(days=1)).isoformat()
        result = evaluate_entry(arousal=0.4, recall_count=2, last_recalled=recent)
        assert result == DecayAction.KEEP

    # --- Rule 3: Frequently recalled + stale → DELETE ---

    def test_frequent_stale_recall_deletes(self):
        """recall_count >= 2 but last recalled > 18 months ago → DELETE."""
        stale = (datetime.now() - timedelta(days=600)).isoformat()
        result = evaluate_entry(arousal=0.5, recall_count=5, last_recalled=stale)
        assert result == DecayAction.DELETE

    def test_frequent_recall_none_last_recalled_deletes(self):
        """recall_count >= 2 but last_recalled=None → DELETE."""
        result = evaluate_entry(arousal=0.5, recall_count=3, last_recalled=None)
        assert result == DecayAction.DELETE

    # --- Rule 4: Low arousal + low recall → COMPACT ---

    def test_low_arousal_low_recall_compacts(self):
        """Low arousal + low recall count → COMPACT."""
        result = evaluate_entry(arousal=0.4, recall_count=0, last_recalled=None)
        assert result == DecayAction.COMPACT

    def test_recall_count_one_compacts(self):
        """recall_count=1 (below threshold of 2) → COMPACT."""
        recent = datetime.now().isoformat()
        result = evaluate_entry(arousal=0.5, recall_count=1, last_recalled=recent)
        assert result == DecayAction.COMPACT

    # --- Custom thresholds ---

    def test_custom_arousal_threshold(self):
        """Custom arousal_threshold changes the boundary."""
        # 0.5 is below default 0.7 but above custom 0.4
        result = evaluate_entry(
            arousal=0.5,
            recall_count=0,
            last_recalled=None,
            arousal_threshold=0.4,
        )
        assert result == DecayAction.KEEP

    def test_custom_recall_threshold(self):
        """Custom recall_threshold changes the boundary."""
        recent = datetime.now().isoformat()
        # recall_count=1 is below default 2 but meets custom 1
        result = evaluate_entry(
            arousal=0.4,
            recall_count=1,
            last_recalled=recent,
            recall_threshold=1,
        )
        assert result == DecayAction.KEEP

    def test_custom_recall_window(self):
        """Custom recall_window_months changes the staleness boundary."""
        # 400 days ago: within default 18 months (540 days), but outside 6 months (180 days)
        borderline = (datetime.now() - timedelta(days=400)).isoformat()
        result = evaluate_entry(
            arousal=0.4,
            recall_count=2,
            last_recalled=borderline,
            recall_window_months=6,
        )
        assert result == DecayAction.DELETE


class TestDecayAction:
    """Test DecayAction enum values."""

    def test_enum_values(self):
        assert DecayAction.KEEP.value == "keep"
        assert DecayAction.COMPACT.value == "compact"
        assert DecayAction.DELETE.value == "delete"
