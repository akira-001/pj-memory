"""Tests for crystallization dashboard page."""

from __future__ import annotations

import pytest

from cognitive_memory.dashboard.services.consolidation_service import (
    get_crystallization_data,
    parse_error_patterns,
    parse_principles,
)
from cognitive_memory.signals import check_signals


class TestSignals:
    """Signal computation from log files."""

    def test_signals_rich(self, crystal_rich_config):
        signals = check_signals(crystal_rich_config)
        assert signals.pattern_count == 3
        assert signals.error_count == 6  # 2 (3/18) + 3 (3/19) + 1 (3/20)
        assert signals.log_days == 3
        assert signals.should_crystallize is True

    def test_signals_empty(self, crystal_empty_config):
        signals = check_signals(crystal_empty_config)
        assert signals.pattern_count == 0
        assert signals.error_count == 0
        assert signals.log_days == 0
        # should_crystallize=True because days_since_checkpoint=9999
        assert signals.should_crystallize is True
        assert any("Days since checkpoint" in c for c in signals.triggered_conditions)

    def test_signals_boundary_not_triggered(self, crystal_boundary_config):
        signals = check_signals(crystal_boundary_config)
        assert signals.pattern_count == 2  # < threshold 3
        assert signals.error_count == 4  # < threshold 5
        assert signals.log_days == 2  # < threshold 10
        # Only check PATTERN and ERROR are NOT in triggered conditions
        assert not any("[PATTERN]" in c for c in signals.triggered_conditions)
        assert not any("[ERROR]" in c for c in signals.triggered_conditions)


class TestParseErrorPatterns:
    """Parse EP-NNN entries from error-patterns.md."""

    def test_three_entries(self, crystal_rich_config):
        patterns = parse_error_patterns(crystal_rich_config.knowledge_error_patterns_path)
        assert len(patterns) == 3
        assert patterns[0]["id"] == "EP-001"
        assert patterns[0]["title"] == "浅い探索で存在するリソースを見落とす"
        assert patterns[0]["date"] == "2026-03-25"
        assert patterns[1]["id"] == "EP-002"
        assert patterns[2]["id"] == "EP-003"

    def test_single_entry(self, crystal_boundary_config):
        patterns = parse_error_patterns(crystal_boundary_config.knowledge_error_patterns_path)
        assert len(patterns) == 1
        assert patterns[0]["id"] == "EP-001"

    def test_empty_template(self, crystal_empty_config):
        patterns = parse_error_patterns(crystal_empty_config.knowledge_error_patterns_path)
        assert patterns == []

    def test_missing_file(self, tmp_path):
        patterns = parse_error_patterns(tmp_path / "nonexistent.md")
        assert patterns == []


class TestParsePrinciples:
    """Parse principles from knowledge summary."""

    def test_three_principles(self, crystal_rich_config):
        principles = parse_principles(crystal_rich_config.knowledge_summary_path)
        assert len(principles) == 3
        assert "探索は網羅的に" in principles[0]["title"]
        assert "環境要因を先に排除" in principles[1]["title"]
        assert "プロトコルを忘れる" in principles[2]["title"]

    def test_single_principle(self, crystal_boundary_config):
        principles = parse_principles(crystal_boundary_config.knowledge_summary_path)
        assert len(principles) == 1
        assert "探索は網羅的に" in principles[0]["title"]

    def test_empty_template(self, crystal_empty_config):
        principles = parse_principles(crystal_empty_config.knowledge_summary_path)
        assert principles == []

    def test_missing_file(self, tmp_path):
        principles = parse_principles(tmp_path / "nonexistent.md")
        assert principles == []


class TestGetCrystallizationData:
    """Integration: get_crystallization_data returns complete structure."""

    def test_rich_data(self, crystal_rich_config):
        data = get_crystallization_data(crystal_rich_config)
        assert data["signals"].should_crystallize is True
        assert len(data["error_patterns"]) == 3
        assert len(data["principles"]) == 3
        assert data["checkpoint"]["last"] == "2026-03-26"
        assert data["checkpoint"]["count"] == 1

    def test_empty_data(self, crystal_empty_config):
        data = get_crystallization_data(crystal_empty_config)
        assert data["error_patterns"] == []
        assert data["principles"] == []
        assert data["checkpoint"]["last"] == ""
        assert data["checkpoint"]["count"] == 0


class TestCrystallizationRoute:
    """HTTP route tests with HTML content verification."""

    def test_page_returns_200(self, crystal_rich_client):
        resp = crystal_rich_client.get("/consolidation")
        assert resp.status_code == 200

    def test_signals_in_html(self, crystal_rich_client):
        resp = crystal_rich_client.get("/consolidation")
        html = resp.text
        # Pattern count and error count in signal-value spans
        assert 'class="signal-value">3<' in html  # pattern_count
        assert 'class="signal-value">6<' in html  # error_count

    def test_error_patterns_in_html(self, crystal_rich_client):
        resp = crystal_rich_client.get("/consolidation")
        html = resp.text
        assert "EP-001" in html
        assert "EP-002" in html
        assert "EP-003" in html
        assert "浅い探索で存在するリソースを見落とす" in html

    def test_principles_in_html(self, crystal_rich_client):
        resp = crystal_rich_client.get("/consolidation")
        html = resp.text
        assert "探索は網羅的に" in html
        assert "環境要因を先に排除" in html
        assert "プロトコルを忘れる" in html

    def test_checkpoint_in_html(self, crystal_rich_client):
        resp = crystal_rich_client.get("/consolidation")
        html = resp.text
        assert "2026-03-26" in html
        assert 'class="checkpoint-count">1<' in html  # checkpoint_count

    def test_empty_state(self, crystal_empty_client):
        resp = crystal_empty_client.get("/consolidation")
        assert resp.status_code == 200
        html = resp.text
        # No EP entries
        assert "EP-001" not in html
        # Should show zero values
        assert 'class="signal-value">0<' in html  # pattern_count = 0

    def test_boundary_state(self, crystal_boundary_client):
        resp = crystal_boundary_client.get("/consolidation")
        assert resp.status_code == 200
        html = resp.text
        assert 'class="signal-value">2<' in html  # pattern_count = 2
        assert 'class="signal-value">4<' in html  # error_count = 4
        assert "EP-001" in html  # 1 error pattern
        assert "EP-002" not in html  # only 1 EP

    def test_i18n_japanese(self, crystal_rich_client):
        crystal_rich_client.cookies.set("lang", "ja")
        resp = crystal_rich_client.get("/consolidation")
        html = resp.text
        assert "記憶の定着" in html
        assert "エラーパターン" in html
