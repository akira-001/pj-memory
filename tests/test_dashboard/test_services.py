"""Service layer tests for the cogmem dashboard."""

from __future__ import annotations

import sqlite3

from cognitive_memory.dashboard.i18n import t
from cognitive_memory.dashboard.services.memory_service import get_overview_data, get_memory_summary, _empty_data
from cognitive_memory.dashboard.services.logs_service import get_log_dates, get_log_entries
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
        assert len(data["arousal_histogram"]) == 10
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
        assert len(data["arousal_histogram"]) == 10

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

    def test_get_skills_list_returns_list(self, config):
        skills = get_skills_list(config)
        assert isinstance(skills, list)

    def test_get_skills_list_has_required_fields(self, config, project_dir):
        """Each skill must have all fields needed for the full table."""
        from cognitive_memory.dashboard.services import skills_service
        test_dir = project_dir / ".claude" / "skills" / "tdd-test"
        test_dir.mkdir(parents=True)
        (test_dir / "SKILL.md").write_text(
            "---\nname: tdd-test\ndescription: TDD test skill\n---\n",
            encoding="utf-8",
        )
        original = skills_service._CLAUDE_SKILLS_DIRS[:]
        skills_service._CLAUDE_SKILLS_DIRS.append(project_dir / ".claude" / "skills")
        try:
            skills = get_skills_list(config)
            tdd = [s for s in skills if s["name"] == "tdd-test"]
            assert len(tdd) == 1
            s = tdd[0]
            required_fields = [
                "id", "name", "summary", "description",
                "category", "effectiveness", "total_executions",
                "total_events", "last_used_at", "trend",
                "version", "improvements",
            ]
            for field in required_fields:
                assert field in s, f"Missing field: {field}"
        finally:
            skills_service._CLAUDE_SKILLS_DIRS[:] = original

    def test_get_skills_list_matches_db_by_skill_id(self, config, project_dir):
        """When .claude/skills/ dir name matches a DB skill id, stats merge."""
        from cognitive_memory.dashboard.services import skills_service
        # Create .claude/skills/test-skill-001 matching the DB skill
        test_dir = project_dir / ".claude" / "skills" / "test-skill-001"
        test_dir.mkdir(parents=True)
        (test_dir / "SKILL.md").write_text(
            "---\nname: test-skill-001\ndescription: A test skill for dashboard testing\n---\n",
            encoding="utf-8",
        )
        original = skills_service._CLAUDE_SKILLS_DIRS[:]
        skills_service._CLAUDE_SKILLS_DIRS.append(project_dir / ".claude" / "skills")
        try:
            skills = get_skills_list(config)
            matched = [s for s in skills if s["name"] == "test-skill-001"]
            assert len(matched) == 1
            s = matched[0]
            # DB stats should be merged
            assert s["effectiveness"] == 0.75
            assert s["total_executions"] == 10
            assert s["category"] == "conversation-skills"
            assert s["version"] == 2
        finally:
            skills_service._CLAUDE_SKILLS_DIRS[:] = original

    def test_get_skills_list_matches_db_by_hash_id(self, config, project_dir):
        """Real-world case: DB skill id is a hash like 'skill_123_abc'.
        Matching works when DB description title is contained in claude description.
        """
        import sqlite3

        from cognitive_memory.dashboard.services import skills_service

        # Insert a DB skill with hash id — title before colon must appear in claude desc
        db_path = project_dir / "memory" / "skills.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT OR REPLACE INTO skills VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "skill_999_hashid", "データ分析スキル", "meta-skills",
                "データ分析: データを分析して可視化する",
                "data analysis trigger",
                0.85, 15, 12, "2026-03-25T10:00:00",
                "2026-03-01T00:00:00", "2026-03-25T10:00:00", 3,
                "path/to/skill.json", None,
            ),
        )
        conn.commit()
        conn.close()

        # Create .claude/skills/ with description that CONTAINS the DB title
        test_dir = project_dir / ".claude" / "skills" / "data-analysis"
        test_dir.mkdir(parents=True)
        (test_dir / "SKILL.md").write_text(
            "---\nname: data-analysis\n"
            "description: データ分析と可視化を行うスキル\n---\n",
            encoding="utf-8",
        )

        original = skills_service._CLAUDE_SKILLS_DIRS[:]
        skills_service._CLAUDE_SKILLS_DIRS.append(project_dir / ".claude" / "skills")
        try:
            skills = get_skills_list(config)
            matched = [s for s in skills if s["name"] == "data-analysis"]
            assert len(matched) == 1
            s = matched[0]
            assert s["total_executions"] == 15, f"Expected 15, got {s['total_executions']}"
            assert s["effectiveness"] == 0.85
            assert s["category"] == "meta-skills"
            assert s["version"] == 3
        finally:
            skills_service._CLAUDE_SKILLS_DIRS[:] = original

    def test_get_skills_list_sorted_by_executions(self, config, project_dir):
        """Skills should be sorted by total_executions descending."""
        from cognitive_memory.dashboard.services import skills_service
        test_dir = project_dir / ".claude" / "skills" / "test-skill-001"
        test_dir.mkdir(parents=True)
        (test_dir / "SKILL.md").write_text(
            "---\nname: test-skill-001\ndescription: A test skill for dashboard testing\n---\n",
            encoding="utf-8",
        )
        zero_dir = project_dir / ".claude" / "skills" / "zero-skill"
        zero_dir.mkdir(parents=True)
        (zero_dir / "SKILL.md").write_text(
            "---\nname: zero-skill\ndescription: Never used\n---\n",
            encoding="utf-8",
        )
        original = skills_service._CLAUDE_SKILLS_DIRS[:]
        skills_service._CLAUDE_SKILLS_DIRS.append(project_dir / ".claude" / "skills")
        try:
            skills = get_skills_list(config)
            # test-skill-001 has 10 executions, zero-skill has 0
            names = [s["name"] for s in skills]
            idx_matched = names.index("test-skill-001")
            idx_zero = names.index("zero-skill")
            assert idx_matched < idx_zero, "Skills with more executions should come first"
        finally:
            skills_service._CLAUDE_SKILLS_DIRS[:] = original

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
