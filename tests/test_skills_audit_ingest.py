"""Tests for skill audit and benchmark ingest."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.skills.store import SkillsStore
from cognitive_memory.skills.audit import SkillAuditor
from cognitive_memory.skills.ingest import BenchmarkIngestor
from cognitive_memory.skills.types import (
    Skill, UsageStats, SuccessMetric, PerformanceMetric,
)


def _make_skill(**overrides) -> Skill:
    defaults = dict(
        id="skill_test_001",
        name="Test Skill",
        category="meta-skills",
        description="A test skill",
        execution_pattern="1. Do something",
        success_metrics=[
            SuccessMetric(
                name="Effectiveness",
                description="test",
                measurement_method="test",
                target_value=0.8,
                current_value=0.5,
            )
        ],
        improvement_history=[],
        usage_stats=UsageStats(
            total_executions=5,
            successful_executions=2,
            average_effectiveness=0.4,
            last_used_at=datetime.now().isoformat(),
            frequency=0.5,
        ),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        version=1,
    )
    defaults.update(overrides)
    return Skill(**defaults)


@pytest.fixture
def store(tmp_path):
    config = CogMemConfig(
        logs_dir=str(tmp_path / "memory" / "logs"),
        db_path=str(tmp_path / "memory" / "vectors.db"),
        _base_dir=str(tmp_path),
    )
    (tmp_path / "memory" / "logs").mkdir(parents=True, exist_ok=True)
    return SkillsStore(config)


# --- skill_usage_log tests ---


class TestUsageLog:
    def test_log_usage_inserts_row(self, store):
        store.log_usage("test context", "skill_1", 0.8)
        rows = store.get_recent_usage_log("skill_1", limit=10)
        assert len(rows) == 1
        assert rows[0]["context"] == "test context"
        assert rows[0]["effectiveness"] == 0.8

    def test_log_usage_null_skill(self, store):
        store.log_usage("no skill used", None, 0.5)
        patterns = store.get_unmatched_patterns(min_frequency=1)
        assert len(patterns) == 1
        assert patterns[0]["context"] == "no skill used"

    def test_unmatched_patterns_threshold(self, store):
        for _ in range(3):
            store.log_usage("repeated pattern", None, 0.6)
        store.log_usage("single pattern", None, 0.7)

        patterns = store.get_unmatched_patterns(min_frequency=3)
        assert len(patterns) == 1
        assert patterns[0]["context"] == "repeated pattern"
        assert patterns[0]["frequency"] == 3


# --- SkillAuditor tests ---


class TestSkillAuditor:
    def test_audit_empty_db(self, store):
        auditor = SkillAuditor(store)
        result = auditor.audit()
        assert result["recommendations"] == []
        assert result["summary"]["total_skills"] == 0

    def test_audit_detects_low_effectiveness(self, store):
        skill = _make_skill(
            usage_stats=UsageStats(
                total_executions=5,
                successful_executions=1,
                average_effectiveness=0.3,
                last_used_at=datetime.now().isoformat(),
                frequency=0.5,
            ),
        )
        store.save_skill(skill)
        auditor = SkillAuditor(store)
        result = auditor.audit()

        improve_recs = [r for r in result["recommendations"] if r["type"] == "improve"]
        assert len(improve_recs) >= 1
        assert improve_recs[0]["skill_name"] == "Test Skill"
        assert improve_recs[0]["priority"] == "medium"  # 0.3 is not < 0.3

    def test_audit_detects_declining_trend(self, store):
        skill = _make_skill(
            id="skill_decline_001",
            usage_stats=UsageStats(
                total_executions=5,
                successful_executions=3,
                average_effectiveness=0.6,
                last_used_at=datetime.now().isoformat(),
                frequency=0.5,
            ),
        )
        store.save_skill(skill)

        # Insert declining usage log entries (5+ points, drop >= 0.15)
        store.log_usage("task", "skill_decline_001", 0.9)  # oldest
        store.log_usage("task", "skill_decline_001", 0.8)
        store.log_usage("task", "skill_decline_001", 0.7)
        store.log_usage("task", "skill_decline_001", 0.6)
        store.log_usage("task", "skill_decline_001", 0.5)  # newest

        auditor = SkillAuditor(store)
        result = auditor.audit()

        decline_recs = [
            r for r in result["recommendations"]
            if r["type"] == "improve" and "declining" in r.get("reason", "")
        ]
        assert len(decline_recs) == 1

    def test_audit_ignores_minor_decline(self, store):
        """Small fluctuations (< 0.15 total drop) should not trigger declining."""
        skill = _make_skill(
            id="skill_minor_001",
            usage_stats=UsageStats(
                total_executions=5,
                successful_executions=4,
                average_effectiveness=0.85,
                last_used_at=datetime.now().isoformat(),
                frequency=0.5,
            ),
        )
        store.save_skill(skill)

        # Insert slight decline (total drop = 0.10 < 0.15 threshold)
        store.log_usage("task", "skill_minor_001", 0.95)
        store.log_usage("task", "skill_minor_001", 0.93)
        store.log_usage("task", "skill_minor_001", 0.91)
        store.log_usage("task", "skill_minor_001", 0.89)
        store.log_usage("task", "skill_minor_001", 0.85)

        auditor = SkillAuditor(store)
        result = auditor.audit()

        decline_recs = [
            r for r in result["recommendations"]
            if r["type"] == "improve" and "declining" in r.get("reason", "")
        ]
        assert len(decline_recs) == 0

    def test_audit_detects_unmatched_patterns(self, store):
        for _ in range(4):
            store.log_usage("academic paper summary", None, 0.6)

        auditor = SkillAuditor(store)
        result = auditor.audit()

        create_recs = [r for r in result["recommendations"] if r["type"] == "create"]
        assert len(create_recs) == 1
        assert create_recs[0]["frequency"] == 4

    def test_audit_brief_skips_patterns(self, store):
        for _ in range(4):
            store.log_usage("pattern", None, 0.5)

        auditor = SkillAuditor(store)
        result = auditor.audit(brief=True)

        create_recs = [r for r in result["recommendations"] if r["type"] == "create"]
        assert len(create_recs) == 0

    def test_audit_detects_stale_skills(self, store):
        old_date = (datetime.now() - timedelta(days=90)).isoformat()
        skill = _make_skill(
            id="skill_stale_001",
            usage_stats=UsageStats(
                total_executions=5,
                successful_executions=4,
                average_effectiveness=0.8,
                last_used_at=old_date,
                frequency=0.1,
            ),
        )
        store.save_skill(skill)

        auditor = SkillAuditor(store)
        result = auditor.audit()

        stale_recs = [r for r in result["recommendations"] if r["type"] == "stale"]
        assert len(stale_recs) == 1

    def test_audit_priority_ordering(self, store):
        # High priority: low effectiveness
        store.save_skill(_make_skill(
            id="skill_high",
            name="High Priority",
            usage_stats=UsageStats(
                total_executions=5, successful_executions=1,
                average_effectiveness=0.2,
                last_used_at=datetime.now().isoformat(), frequency=0.5,
            ),
        ))
        # Low priority: stale
        old_date = (datetime.now() - timedelta(days=90)).isoformat()
        store.save_skill(_make_skill(
            id="skill_low",
            name="Low Priority",
            usage_stats=UsageStats(
                total_executions=5, successful_executions=4,
                average_effectiveness=0.8,
                last_used_at=old_date, frequency=0.1,
            ),
        ))

        auditor = SkillAuditor(store)
        result = auditor.audit()

        assert len(result["recommendations"]) >= 2
        # High priority should come first
        assert result["recommendations"][0]["priority"] == "high"


# --- BenchmarkIngestor tests ---


class TestBenchmarkIngestor:
    def test_ingest_benchmark_json(self, store, tmp_path):
        workspace = tmp_path / "eval-workspace"
        workspace.mkdir()

        benchmark = {
            "run_summary": {
                "with_skill": {
                    "pass_rate": {"mean": 0.85, "stddev": 0.05},
                    "time_seconds": {"mean": 42.5, "stddev": 5.0},
                }
            },
            "runs": [
                {"result": {"errors": 1, "tool_calls": 20}},
                {"result": {"errors": 0, "tool_calls": 15}},
            ],
        }
        (workspace / "benchmark.json").write_text(json.dumps(benchmark))

        ingestor = BenchmarkIngestor(store)
        result = ingestor.ingest(str(workspace), "test-skill")

        assert result["status"] == "ingested"
        assert result["metrics"]["effectiveness"] == 0.85
        assert result["metrics"]["execution_time"] == 42500.0
        assert result["metrics"]["error_rate"] == pytest.approx(1 / 35, abs=0.01)
        assert result["source"] == "benchmark.json"

    def test_ingest_grading_json(self, store, tmp_path):
        workspace = tmp_path / "eval-workspace"
        workspace.mkdir()

        grading = {
            "summary": {"pass_rate": 0.75, "passed": 3, "failed": 1, "total": 4},
            "timing": {"total_seconds": 30.0},
            "execution_metrics": {"errors": 2, "tool_calls": 10},
        }
        (workspace / "grading.json").write_text(json.dumps(grading))

        ingestor = BenchmarkIngestor(store)
        result = ingestor.ingest(str(workspace), "test-skill")

        assert result["status"] == "ingested"
        assert result["metrics"]["effectiveness"] == 0.75
        assert result["source"] == "grading.json"

    def test_ingest_no_files(self, store, tmp_path):
        workspace = tmp_path / "empty"
        workspace.mkdir()

        ingestor = BenchmarkIngestor(store)
        result = ingestor.ingest(str(workspace), "test")
        assert "error" in result

    def test_ingest_nonexistent_dir(self, store):
        ingestor = BenchmarkIngestor(store)
        result = ingestor.ingest("/nonexistent/path", "test")
        assert "error" in result

    def test_ingest_matches_existing_skill(self, store, tmp_path):
        skill = _make_skill(id="skill_match_001", name="Morning Briefing")
        store.save_skill(skill)

        workspace = tmp_path / "eval"
        workspace.mkdir()
        grading = {
            "summary": {"pass_rate": 0.9},
            "timing": {"total_seconds": 10.0},
            "execution_metrics": {"errors": 0, "tool_calls": 5},
        }
        (workspace / "grading.json").write_text(json.dumps(grading))

        ingestor = BenchmarkIngestor(store)
        result = ingestor.ingest(str(workspace), "morning-briefing")

        assert result["skill_id"] == "skill_match_001"

    def test_ingest_logs_usage(self, store, tmp_path):
        workspace = tmp_path / "eval"
        workspace.mkdir()
        grading = {
            "summary": {"pass_rate": 0.8},
            "timing": {"total_seconds": 5.0},
            "execution_metrics": {"errors": 0, "tool_calls": 3},
        }
        (workspace / "grading.json").write_text(json.dumps(grading))

        ingestor = BenchmarkIngestor(store)
        ingestor.ingest(str(workspace), "test-skill")

        # Verify usage was logged (skill_id=None since no match)
        import sqlite3
        with sqlite3.connect(store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM skill_usage_log WHERE context LIKE '%skill-creator%'"
            ).fetchall()
            assert len(rows) == 1
            assert rows[0]["effectiveness"] == 0.8

    def test_ingest_malformed_benchmark(self, store, tmp_path):
        workspace = tmp_path / "eval"
        workspace.mkdir()
        (workspace / "benchmark.json").write_text("not json")

        # Should fall through to grading.json, which also doesn't exist
        ingestor = BenchmarkIngestor(store)
        result = ingestor.ingest(str(workspace), "test")
        assert "error" in result


# --- Skill Session Event Tracking tests ---


class TestSkillTracking:
    def test_track_event_inserts(self, store):
        store.track_event("2026-03-25", "morning-briefing", "extra_step",
                          "Added weather API fallback", "Step 3")
        events = store.get_session_events("2026-03-25")
        assert len(events) == 1
        assert events[0]["skill_name"] == "morning-briefing"
        assert events[0]["event_type"] == "extra_step"
        assert events[0]["step_ref"] == "Step 3"

    def test_track_event_invalid_type(self, store):
        with pytest.raises(ValueError, match="Invalid event_type"):
            store.track_event("2026-03-25", "test", "invalid_type", "desc")

    def test_track_event_no_step_ref(self, store):
        store.track_event("2026-03-25", "recall", "user_correction",
                          "Calendar name was wrong")
        events = store.get_session_events("2026-03-25")
        assert events[0]["step_ref"] is None

    def test_get_session_events_filters_by_date(self, store):
        store.track_event("2026-03-25", "skill-a", "extra_step", "desc1")
        store.track_event("2026-03-26", "skill-b", "extra_step", "desc2")
        events = store.get_session_events("2026-03-25")
        assert len(events) == 1
        assert events[0]["skill_name"] == "skill-a"

    def test_track_summary_no_events(self, store):
        summary = store.get_track_summary("2026-03-25")
        assert summary["skills_used"] == []
        assert summary["skills_ok"] == []

    def test_track_summary_user_correction_triggers_improve(self, store):
        store.track_event("2026-03-25", "schedule-registration",
                          "user_correction", "Calendar name wrong")
        summary = store.get_track_summary("2026-03-25")
        assert len(summary["skills_used"]) == 1
        assert summary["skills_used"][0]["needs_improvement"] is True
        assert "user_correction" in summary["skills_used"][0]["reason"]

    def test_track_summary_error_recovery_triggers_improve(self, store):
        store.track_event("2026-03-25", "cron-automation",
                          "error_recovery", "pm2 not running")
        summary = store.get_track_summary("2026-03-25")
        assert len(summary["skills_used"]) == 1
        assert summary["skills_used"][0]["needs_improvement"] is True

    def test_track_summary_single_extra_step_ok(self, store):
        """One extra_step should NOT trigger improvement."""
        store.track_event("2026-03-25", "paper-summary",
                          "extra_step", "Added related work section")
        summary = store.get_track_summary("2026-03-25")
        assert summary["skills_used"] == []
        assert "paper-summary" in summary["skills_ok"]

    def test_track_summary_two_extra_steps_triggers(self, store):
        """Two extra_steps SHOULD trigger improvement."""
        store.track_event("2026-03-25", "paper-summary",
                          "extra_step", "Added related work", "Step 3")
        store.track_event("2026-03-25", "paper-summary",
                          "extra_step", "Added limitations", "Step 4")
        summary = store.get_track_summary("2026-03-25")
        assert len(summary["skills_used"]) == 1
        assert "extra_step" in summary["skills_used"][0]["reason"]

    def test_track_summary_mixed_skills(self, store):
        """Multiple skills: one needs improvement, one is OK."""
        store.track_event("2026-03-25", "skill-bad",
                          "user_correction", "Wrong output")
        store.track_event("2026-03-25", "skill-good",
                          "extra_step", "Minor addition")
        summary = store.get_track_summary("2026-03-25")
        assert len(summary["skills_used"]) == 1
        assert summary["skills_used"][0]["skill_name"] == "skill-bad"
        assert "skill-good" in summary["skills_ok"]
