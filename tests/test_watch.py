"""Tests for cogmem watch — git history pattern detection."""
from __future__ import annotations
from cognitive_memory.watch import analyze_git_history, detect_log_gaps


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


def test_detect_revert():
    """Revert commits should generate ERROR entries."""
    log_lines = [
        'abc1234 Revert "fix: wrong column order"',
        "def5678 feat: add feature",
    ]
    result = analyze_git_history(log_lines)
    assert result["revert_count"] == 1
    assert any(e["category"] == "ERROR" for e in result["entries"])
    assert "リバート" in result["entries"][0]["title"]


def test_count_japanese_fix_commits():
    """修正: prefix should also be counted as fix."""
    log_lines = [
        "abc1234 修正: スキル一覧のソート順",
        "def5678 fix: column missing",
        "ghi9012 修正: false positive matching",
    ]
    result = analyze_git_history(log_lines)
    assert result["fix_count"] == 3


def test_empty_git_log():
    """Empty log should return zero counts and no entries."""
    result = analyze_git_history([])
    assert result["fix_count"] == 0
    assert result["revert_count"] == 0
    assert result["entries"] == []


def test_detect_log_gaps():
    """Many commits with few log entries should be flagged."""
    result = detect_log_gaps(commit_count=12, log_entry_count=0)
    assert result["has_gap"] is True
    assert result["severity"] == "high"


def test_no_gap_when_logged():
    """Reasonable ratio should not flag."""
    result = detect_log_gaps(commit_count=5, log_entry_count=3)
    assert result["has_gap"] is False


def test_log_gaps_zero_commits():
    """Zero commits should not flag a gap."""
    result = detect_log_gaps(commit_count=0, log_entry_count=0)
    assert result["has_gap"] is False
