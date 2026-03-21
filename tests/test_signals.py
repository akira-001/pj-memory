"""Tests for crystallization signal detection."""

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.signals import check_signals, CrystallizationSignals


class TestCheckSignals:
    """Tests for check_signals function."""

    def test_empty_logs_dir(self, tmp_path):
        """No logs returns all zeros."""
        logs = tmp_path / "memory" / "logs"
        logs.mkdir(parents=True)
        config = CogMemConfig(logs_dir=str(logs), _base_dir=str(tmp_path), last_checkpoint="2026-03-20")
        result = check_signals(config)
        assert result.pattern_count == 0
        assert result.error_count == 0
        assert result.log_days == 0
        assert result.should_crystallize is False

    def test_counts_pattern_entries(self, tmp_path):
        """Counts [PATTERN] entries across logs."""
        logs = tmp_path / "memory" / "logs"
        logs.mkdir(parents=True)
        for i in range(3):
            (logs / f"2026-03-{10+i:02d}.md").write_text(
                f"# Log\n## Log Entries\n### [PATTERN] Theme {i}\n*Arousal: 0.7 | Emotion: Recognition*\nRecurring theme content here.\n---\n"
            )
        config = CogMemConfig(logs_dir=str(logs), _base_dir=str(tmp_path), pattern_threshold=3)
        result = check_signals(config)
        assert result.pattern_count == 3
        assert result.should_crystallize is True

    def test_counts_error_entries(self, tmp_path):
        """Counts [ERROR] entries across logs."""
        logs = tmp_path / "memory" / "logs"
        logs.mkdir(parents=True)
        content = "# Log\n## Log Entries\n"
        for i in range(5):
            content += f"### [ERROR] Mistake {i}\n*Arousal: 0.8 | Emotion: Conflict*\nError content number {i} here.\n---\n"
        (logs / "2026-03-10.md").write_text(content)
        config = CogMemConfig(logs_dir=str(logs), _base_dir=str(tmp_path), error_threshold=5)
        result = check_signals(config)
        assert result.error_count == 5
        assert result.should_crystallize is True

    def test_log_days_count(self, tmp_path):
        """Counts unique log days."""
        logs = tmp_path / "memory" / "logs"
        logs.mkdir(parents=True)
        for i in range(10):
            (logs / f"2026-03-{i+1:02d}.md").write_text(
                f"# Log\n## Log Entries\n### [MILESTONE] Done {i}\n*Arousal: 0.6 | Emotion: Relief*\nCompleted something important.\n---\n"
            )
        config = CogMemConfig(logs_dir=str(logs), _base_dir=str(tmp_path), log_days_threshold=10)
        result = check_signals(config)
        assert result.log_days == 10
        assert result.should_crystallize is True

    def test_days_since_checkpoint(self, tmp_path):
        """Calculates days since last checkpoint."""
        logs = tmp_path / "memory" / "logs"
        logs.mkdir(parents=True)
        (logs / "2026-03-21.md").write_text("# Log\n## Log Entries\n### [INSIGHT] test\n*Arousal: 0.5*\nSome insight content here.\n---\n")
        config = CogMemConfig(
            logs_dir=str(logs), _base_dir=str(tmp_path),
            last_checkpoint="2026-01-01", checkpoint_interval_days=21
        )
        result = check_signals(config)
        assert result.days_since_checkpoint > 21
        assert result.should_crystallize is True

    def test_invalid_checkpoint_date(self, tmp_path):
        """Invalid last_checkpoint defaults to large days_since."""
        logs = tmp_path / "memory" / "logs"
        logs.mkdir(parents=True)
        config = CogMemConfig(
            logs_dir=str(logs), _base_dir=str(tmp_path),
            last_checkpoint="not-a-date", checkpoint_interval_days=21
        )
        result = check_signals(config)
        assert result.days_since_checkpoint == 9999

    def test_no_conditions_met(self, tmp_path):
        """When no conditions are met, should_crystallize is False."""
        logs = tmp_path / "memory" / "logs"
        logs.mkdir(parents=True)
        (logs / "2026-03-21.md").write_text("# Log\n## Log Entries\n### [INSIGHT] test\n*Arousal: 0.5*\nSome insight content here.\n---\n")
        config = CogMemConfig(logs_dir=str(logs), _base_dir=str(tmp_path), last_checkpoint="2026-03-20")
        result = check_signals(config)
        assert result.should_crystallize is False

    def test_excludes_compact_files(self, tmp_path):
        """Compact files are excluded from scanning."""
        logs = tmp_path / "memory" / "logs"
        logs.mkdir(parents=True)
        (logs / "2026-03-10.md").write_text("# Log\n## Log Entries\n### [PATTERN] Real\n*Arousal: 0.7*\nReal entry content here.\n---\n")
        (logs / "2026-03-10.compact.md").write_text("# Compact\n### [PATTERN] Compact\n*Arousal: 0.7*\nCompact entry should be ignored.\n---\n")
        config = CogMemConfig(logs_dir=str(logs), _base_dir=str(tmp_path))
        result = check_signals(config)
        assert result.pattern_count == 1  # Only from .md, not .compact.md
        assert result.log_days == 1


    def test_logs_path_is_file(self, tmp_path):
        """When logs_path is a file (not dir), returns zeros without error."""
        logs_file = tmp_path / "memory" / "logs"
        logs_file.parent.mkdir(parents=True)
        logs_file.write_text("not a directory")
        config = CogMemConfig(logs_dir=str(logs_file), _base_dir=str(tmp_path), last_checkpoint="2026-03-20")
        result = check_signals(config)
        assert result.should_crystallize is False
        assert result.log_days == 0
        assert result.pattern_count == 0

    def test_logs_path_nonexistent(self, tmp_path):
        """When logs_path doesn't exist, returns zeros without error."""
        config = CogMemConfig(logs_dir=str(tmp_path / "nonexistent"), _base_dir=str(tmp_path), last_checkpoint="2026-03-20")
        result = check_signals(config)
        assert result.should_crystallize is False
        assert result.log_days == 0


class TestCrystallizationSignalsDict:
    """Tests for to_dict serialization."""

    def test_to_dict_structure(self):
        signals = CrystallizationSignals(
            pattern_count=3, error_count=2, log_days=5,
            days_since_checkpoint=10, should_crystallize=True
        )
        d = signals.to_dict()
        assert "should_crystallize" in d
        assert "conditions" in d
        assert d["should_crystallize"] is True
        assert d["conditions"]["pattern_threshold"] == 3
