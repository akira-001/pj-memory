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


def test_watch_cli_text_output(tmp_path, monkeypatch, capsys):
    """cogmem watch (without --json) should print human-readable summary."""
    import subprocess as sp
    monkeypatch.chdir(tmp_path)
    sp.run(["git", "init"], cwd=tmp_path, capture_output=True)
    sp.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
    sp.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
    (tmp_path / "a.txt").write_text("a")
    sp.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    sp.run(["git", "commit", "-m", "feat: init"], cwd=tmp_path, capture_output=True)
    (tmp_path / "cogmem.toml").write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
    (tmp_path / "memory" / "logs").mkdir(parents=True)

    from cognitive_memory.cli.watch_cmd import run_watch
    run_watch(since="today")
    captured = capsys.readouterr()
    assert "Commits:" in captured.out
    assert "Fix:" in captured.out


def test_watch_cli_json_output(tmp_path, monkeypatch, capsys):
    """cogmem watch --json should output valid JSON."""
    import subprocess as sp
    import json
    monkeypatch.chdir(tmp_path)
    sp.run(["git", "init"], cwd=tmp_path, capture_output=True)
    sp.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
    sp.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
    (tmp_path / "a.txt").write_text("a")
    sp.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    sp.run(["git", "commit", "-m", "feat: init"], cwd=tmp_path, capture_output=True)
    for i in range(3):
        (tmp_path / "a.txt").write_text(f"fix {i}")
        sp.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        sp.run(["git", "commit", "-m", f"fix: issue {i}"], cwd=tmp_path, capture_output=True)
    (tmp_path / "cogmem.toml").write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
    (tmp_path / "memory" / "logs").mkdir(parents=True)

    from cognitive_memory.cli.watch_cmd import run_watch
    run_watch(since="today", json_output=True)
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["fix_count"] == 3
    assert len(output["entries"]) >= 1


def test_detect_skill_creation_signal():
    """3+ fix commits with similar file patterns should suggest new skill."""
    log_lines = [
        "abc1234 fix: skills table column missing",
        "def5678 fix: skills sort order wrong",
        "ghi9012 fix: skills matching false positive",
        "jkl3456 feat: add dashboard",
    ]
    result = analyze_git_history(log_lines)
    signals = result.get("skill_signals", [])
    assert len(signals) >= 1
    assert "skill" in signals[0]["pattern"].lower() or "fix" in signals[0]["pattern"].lower()


def test_watch_git_not_found(tmp_path, monkeypatch):
    """Should exit gracefully when git is not available."""
    import subprocess as sp
    monkeypatch.chdir(tmp_path)
    (tmp_path / "cogmem.toml").write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
    (tmp_path / "memory" / "logs").mkdir(parents=True)
    original_run = sp.run
    def mock_run(*args, **kwargs):
        if args[0][0] == "git":
            raise FileNotFoundError("git not found")
        return original_run(*args, **kwargs)
    monkeypatch.setattr(sp, "run", mock_run)

    from cognitive_memory.cli.watch_cmd import run_watch
    import pytest
    with pytest.raises(SystemExit):
        run_watch()


def test_full_watch_with_auto_log(tmp_path, monkeypatch):
    """cogmem watch --auto-log should append entries to session log."""
    import subprocess as sp
    monkeypatch.chdir(tmp_path)
    sp.run(["git", "init"], cwd=tmp_path, capture_output=True)
    sp.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
    sp.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)

    (tmp_path / "cogmem.toml").write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
    logs_dir = tmp_path / "memory" / "logs"
    logs_dir.mkdir(parents=True)

    # Create commits with fix pattern
    for i in range(4):
        (tmp_path / "a.txt").write_text(f"v{i}")
        sp.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        sp.run(["git", "commit", "-m", f"fix: issue {i}"], cwd=tmp_path, capture_output=True)

    # Create existing log file
    from datetime import date
    log_file = logs_dir / f"{date.today().isoformat()}.md"
    log_file.write_text("# Session Log\n\n## ログエントリ\n")

    from cognitive_memory.cli.watch_cmd import run_watch
    run_watch(since="today", auto_log=True)

    content = log_file.read_text()
    assert "[PATTERN]" in content
    assert "auto-detected" in content
