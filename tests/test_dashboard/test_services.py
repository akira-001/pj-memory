"""Service layer tests for the cogmem dashboard."""

from __future__ import annotations

import sqlite3

from cognitive_memory.dashboard.i18n import t
from cognitive_memory.dashboard.services.memory_service import get_overview_data, get_memory_summary, _empty_data
from cognitive_memory.dashboard.services.logs_service import get_log_dates, get_log_entries, get_log_summary
from cognitive_memory.dashboard.services.skills_service import (
    _determine_trend,
    get_skills_list,
    get_skill_detail,
    get_skill_trend,
    get_audit_results,
)


class TestMemoryService:
    def test_overview_data_populated(self, config):
        data = get_overview_data(config)
        assert data["total_memories"] == 5
        assert data["date_range"]["min"] == "2026-03-19"
        assert data["date_range"]["max"] == "2026-03-20"
        assert 0 < data["avg_arousal"] <= 1.0

    def test_daily_counts(self, config):
        data = get_overview_data(config)
        dates = [d["date"] for d in data["daily_counts"]]
        assert "2026-03-19" in dates
        assert "2026-03-20" in dates

    def test_arousal_histogram(self, config):
        data = get_overview_data(config)
        assert len(data["arousal_histogram"]) == 6
        total = sum(b["count"] for b in data["arousal_histogram"])
        assert total == 5

    def test_category_counts(self, config):
        data = get_overview_data(config)
        cats = data["category_counts"]
        assert cats.get("INSIGHT", 0) >= 1
        assert cats.get("DECISION", 0) >= 1
        assert cats.get("ERROR", 0) >= 1

    def test_empty_db(self, tmp_path):
        """Empty/missing DB returns zero data."""
        from cognitive_memory.config import CogMemConfig
        config = CogMemConfig(_base_dir=str(tmp_path))
        data = get_overview_data(config)
        assert data["total_memories"] == 0
        assert data["daily_counts"] == []

    def test_empty_data_structure(self):
        data = _empty_data()
        assert data["total_memories"] == 0
        assert len(data["arousal_histogram"]) == 6

    def test_total_days(self, config):
        data = get_overview_data(config)
        assert data["total_days"] == 2  # 2026-03-19, 2026-03-20

    def test_memory_summary(self, config):
        summary = get_memory_summary(config)
        assert summary["total_memories"] == 5
        assert summary["total_days"] == 2
        assert len(summary["daily_counts"]) == 2

    def test_memory_summary_empty(self, tmp_path):
        from cognitive_memory.config import CogMemConfig
        config = CogMemConfig(_base_dir=str(tmp_path))
        summary = get_memory_summary(config)
        assert summary["total_memories"] == 0


class TestI18nService:
    def test_t_en(self):
        assert t("nav.memory", "en") == "Memory Overview"

    def test_t_ja(self):
        assert t("nav.memory", "ja") == "メモリー概要"

    def test_t_missing_key(self):
        assert t("nonexistent.key", "en") == "nonexistent.key"


class TestLogsService:
    def test_get_log_dates(self, config):
        dates = get_log_dates(config)
        assert len(dates) >= 1
        assert dates[0]["date"] == "2026-03-20"
        assert dates[0]["entry_count"] >= 3

    def test_get_log_dates_has_overview(self, config):
        dates = get_log_dates(config)
        assert dates[0]["overview"] == "テストセッションの概要です。"

    def test_get_log_entries(self, config):
        data = get_log_entries(config, "2026-03-20")
        assert data is not None
        assert data["date"] == "2026-03-20"
        assert len(data["entries"]) >= 3
        assert data["overview"] != ""
        assert data["handover"] != ""

    def test_get_log_entries_missing(self, config):
        data = get_log_entries(config, "2099-01-01")
        assert data is None

    def test_path_traversal_blocked(self, config):
        data = get_log_entries(config, "../../etc/passwd")
        assert data is None

    def test_filter_by_category(self, config):
        data = get_log_entries(config, "2026-03-20", category="INSIGHT")
        assert data is not None
        assert all(e["category"] == "INSIGHT" for e in data["entries"])
        assert len(data["entries"]) >= 1

    def test_sort_by_arousal(self, config):
        data = get_log_entries(config, "2026-03-20", sort="arousal")
        assert data is not None
        arousals = [e["arousal"] for e in data["entries"]]
        assert arousals == sorted(arousals, reverse=True)

    def test_text_search(self, config):
        data = get_log_entries(config, "2026-03-20", query="エラー")
        assert data is not None
        assert len(data["entries"]) >= 1
        assert any("エラー" in e["title"] or "エラー" in e["body"] for e in data["entries"])

    def test_get_log_summary_counts(self, config):
        """Verify total/detailed/compacted/retained counts."""
        summary = get_log_summary(config)
        assert summary["total"] == 3  # 2026-03-18, 2026-03-19, 2026-03-20
        assert summary["detailed"] == 1  # 2026-03-20 (.md only)
        assert summary["compacted"] == 1  # 2026-03-18 (.compact.md only)
        assert summary["retained"] == 1  # 2026-03-19 (both .md and .compact.md)

    def test_get_log_summary_categories(self, config):
        """Verify category_counts aggregation across all logs."""
        summary = get_log_summary(config)
        cats = summary["category_counts"]
        # 2026-03-20 has INSIGHT, DECISION, ERROR (from .md)
        assert cats.get("INSIGHT", 0) >= 1
        assert cats.get("DECISION", 0) >= 1
        assert cats.get("ERROR", 0) >= 1
        # 2026-03-18 compact has MILESTONE, INSIGHT, DECISION
        assert cats.get("MILESTONE", 0) >= 1

    def test_get_log_dates_has_status(self, config):
        """Verify status field is present and correct per date."""
        dates = get_log_dates(config)
        date_map = {d["date"]: d for d in dates}
        assert date_map["2026-03-20"]["status"] == "detailed"
        assert date_map["2026-03-18"]["status"] == "compacted"
        assert date_map["2026-03-19"]["status"] == "retained"

    def test_get_log_dates_has_categories(self, config):
        """Verify categories dict per date."""
        dates = get_log_dates(config)
        date_map = {d["date"]: d for d in dates}
        # Full .md date should have parsed categories
        cats_20 = date_map["2026-03-20"]["categories"]
        assert "INSIGHT" in cats_20
        assert "ERROR" in cats_20
        # Compact-only date should have categories from compact format
        cats_18 = date_map["2026-03-18"]["categories"]
        assert "MILESTONE" in cats_18 or "INSIGHT" in cats_18

    def test_get_log_dates_has_max_arousal(self, config):
        """Verify max_arousal value."""
        dates = get_log_dates(config)
        date_map = {d["date"]: d for d in dates}
        # 2026-03-20 has arousal values 0.8, 0.6, 0.9
        assert date_map["2026-03-20"]["max_arousal"] == 0.9
        # Compact-only date has no arousal data
        assert date_map["2026-03-18"]["max_arousal"] is None


class TestSkillsService:
    def test_trend_new(self):
        assert _determine_trend([0.5, 0.6]) == "new"
        assert _determine_trend([]) == "new"

    def test_trend_up(self):
        assert _determine_trend([0.9, 0.8, 0.7, 0.6, 0.5]) == "up"

    def test_trend_down(self):
        assert _determine_trend([0.5, 0.6, 0.7, 0.8, 0.9]) == "down"

    def test_trend_flat(self):
        assert _determine_trend([0.7, 0.6, 0.8, 0.5, 0.7]) == "flat"

    def test_get_skills_list_has_all_4_skills(self, config):
        """Fixture provides 4 skills from .claude/skills/."""
        skills = get_skills_list(config)
        names = [s["name"] for s in skills]
        assert "skill-alpha" in names
        assert "test-skill-001" in names
        assert "skill-beta" in names
        assert "skill-gamma" in names

    def test_get_skills_list_has_required_fields(self, config):
        """Each skill dict must have all fields for the 8-column table."""
        skills = get_skills_list(config)
        required = [
            "id", "name", "summary", "description",
            "category", "effectiveness", "total_executions",
            "total_events", "last_used_at", "trend",
            "version", "improvements",
        ]
        for s in skills:
            for field in required:
                assert field in s, f"Skill {s.get('name')}: missing field '{field}'"

    def test_skill_alpha_matched_by_claude_skill_name(self, config):
        """skill-alpha matches DB via claude_skill_name column, gets DB stats."""
        skills = get_skills_list(config)
        alpha = [s for s in skills if s["name"] == "skill-alpha"][0]
        assert alpha["total_executions"] == 25
        assert alpha["effectiveness"] == 0.92
        assert alpha["category"] == "automation-skills"
        assert alpha["version"] == 3

    def test_skill_001_matched_by_exact_id(self, config):
        """test-skill-001 matches DB by exact id, gets DB stats."""
        skills = get_skills_list(config)
        s001 = [s for s in skills if s["name"] == "test-skill-001"][0]
        assert s001["total_executions"] == 10
        assert s001["effectiveness"] == 0.75
        assert s001["category"] == "conversation-skills"
        assert s001["version"] == 2
        assert s001["total_events"] == 2  # skill_start + extra_step

    def test_skill_beta_matched_by_claude_skill_name(self, config):
        """skill-beta matches DB via claude_skill_name, has low effectiveness."""
        skills = get_skills_list(config)
        beta = [s for s in skills if s["name"] == "skill-beta"][0]
        assert beta["total_executions"] == 5
        assert beta["effectiveness"] == 0.35
        assert beta["category"] == "meta-skills"

    def test_skill_gamma_no_db_match(self, config):
        """skill-gamma has no DB match, only events."""
        skills = get_skills_list(config)
        gamma = [s for s in skills if s["name"] == "skill-gamma"][0]
        assert gamma["total_executions"] == 0
        assert gamma["effectiveness"] == 0.0
        assert gamma["category"] == "—"
        assert gamma["total_events"] == 3
        assert gamma["trend"] == "new"

    def test_sorted_by_executions_desc(self, config):
        """alpha(25) > 001(10) > beta(5) > gamma(0)."""
        skills = get_skills_list(config)
        names = [s["name"] for s in skills]
        assert names.index("skill-alpha") < names.index("test-skill-001")
        assert names.index("test-skill-001") < names.index("skill-beta")
        assert names.index("skill-beta") < names.index("skill-gamma")

    def test_get_skill_detail(self, config):
        detail = get_skill_detail(config, "test-skill-001")
        assert detail is not None
        assert detail["skill"].name == "Test Skill"
        assert len(detail["usage_log"]) >= 5
        assert len(detail["events"]) >= 2

    def test_get_skill_detail_missing(self, config):
        assert get_skill_detail(config, "nonexistent") is None

    def test_get_skill_trend(self, config):
        trend = get_skill_trend(config, "test-skill-001")
        assert len(trend) >= 5
        assert all("timestamp" in t and "effectiveness" in t for t in trend)
        # Should be in chronological order (reversed from DB DESC)
        timestamps = [t["timestamp"] for t in trend]
        assert timestamps == sorted(timestamps)

    def test_get_audit_results(self, config):
        audit = get_audit_results(config)
        assert "recommendations" in audit
        assert "summary" in audit
        assert "total_skills" in audit["summary"]
        assert audit["summary"]["total_skills"] >= 1
