"""Tests for knowledge summary.md health check (size / prior bloat)."""

from cognitive_memory.config import CogMemConfig
from cognitive_memory.summary_health import check_summary_health


def _write_summary(tmp_path, text: str):
    path = tmp_path / "memory" / "knowledge" / "summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestCheckSummaryHealth:
    def test_missing_file(self, tmp_path):
        """Missing summary.md is healthy (nothing to prune)."""
        config = CogMemConfig(_base_dir=str(tmp_path))
        health = check_summary_health(config)
        assert health.exists is False
        assert health.needs_pruning is False
        assert health.warnings == []

    def test_small_file_no_priors(self, tmp_path):
        """Small file with no prior blocks passes."""
        _write_summary(tmp_path, "# Knowledge Summary\n\n## Established Principles\n- rule\n")
        config = CogMemConfig(_base_dir=str(tmp_path))
        health = check_summary_health(config)
        assert health.exists is True
        assert health.needs_pruning is False
        assert health.prior_count == 0

    def test_oversize_warns(self, tmp_path):
        """File over summary_max_kb produces a size warning."""
        _write_summary(tmp_path, "x" * 70 * 1024)
        config = CogMemConfig(_base_dir=str(tmp_path), summary_max_kb=60)
        health = check_summary_health(config)
        assert health.needs_pruning is True
        assert any("60KB" in w for w in health.warnings)

    def test_size_check_disabled_with_zero(self, tmp_path):
        """summary_max_kb = 0 disables the size check."""
        _write_summary(tmp_path, "x" * 200 * 1024)
        config = CogMemConfig(_base_dir=str(tmp_path), summary_max_kb=0)
        health = check_summary_health(config)
        assert not any("KB limit" in w for w in health.warnings)

    def test_prior_blocks_over_cap_warn(self, tmp_path):
        """More *[prior]* blocks than summary_prior_sessions warns."""
        text = "# Summary\n\n## 2026-07-01 *[prior]*\nold\n\n## 2026-06-28 *[PRIOR]*\nolder\n"
        _write_summary(tmp_path, text)
        config = CogMemConfig(_base_dir=str(tmp_path), summary_prior_sessions=0)
        health = check_summary_health(config)
        assert health.prior_count == 2
        assert health.needs_pruning is True
        assert any("*[prior]*" in w for w in health.warnings)

    def test_prior_blocks_within_cap_pass(self, tmp_path):
        """Prior blocks within the configured cap do not warn."""
        text = "# Summary\n\n## 2026-07-01 *[prior]*\nrecent\n"
        _write_summary(tmp_path, text)
        config = CogMemConfig(_base_dir=str(tmp_path), summary_prior_sessions=1)
        health = check_summary_health(config)
        assert health.prior_count == 1
        assert health.needs_pruning is False

    def test_to_dict_structure(self, tmp_path):
        """to_dict exposes all fields for JSON output."""
        _write_summary(tmp_path, "# Summary\n")
        config = CogMemConfig(_base_dir=str(tmp_path))
        d = check_summary_health(config).to_dict()
        for key in ("exists", "size_kb", "max_kb", "prior_count", "prior_cap", "needs_pruning", "warnings"):
            assert key in d
