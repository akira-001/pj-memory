"""Tests for cogmem watch — git history pattern detection."""
from __future__ import annotations
from cognitive_memory.watch import analyze_git_history


def test_count_fix_commits():
    """3+ fix commits should be detected as a PATTERN."""
    log_lines = [
        "abc1234 fix: column missing from skills table",
        "def5678 fix: sort order wrong in skills list",
        "ghi9012 fix: false positive in skill matching",
        "jkl3456 feat: add dashboard",
    ]
    result = analyze_git_history(log_lines)
    assert result["fix_count"] == 3
    assert any(e["category"] == "PATTERN" for e in result["entries"])


def test_no_pattern_below_threshold():
    """1-2 fix commits should not trigger PATTERN."""
    log_lines = [
        "abc1234 fix: typo",
        "def5678 feat: new feature",
    ]
    result = analyze_git_history(log_lines)
    assert result["fix_count"] == 1
    assert not any(e["category"] == "PATTERN" for e in result["entries"])
