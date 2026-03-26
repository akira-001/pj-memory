# cogmem watch + Wrap 遡及チェック 実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** git 履歴から自動でパターン検知し、エージェントがログを忘れても事実ベースでエラーパターンとスキル改善シグナルを記録する

**Architecture:** `cogmem watch` CLI コマンドが git log をスキャンして [ERROR]/[PATTERN] エントリを自動生成し、ログに追記する。agents.md の Wrap プロセスに遡及チェック Step 0 を追加して、セッション終了時に漏れを補完する。

**Tech Stack:** Python stdlib (subprocess, re, sqlite3), 既存の cogmem CLI フレームワーク

---

## ファイル構成

| ファイル | 役割 |
|---------|------|
| `src/cognitive_memory/cli/watch_cmd.py` (新規) | `cogmem watch` コマンドの実装 |
| `src/cognitive_memory/cli/main.py` (修正) | watch サブコマンドの登録 |
| `src/cognitive_memory/watch.py` (新規) | git 履歴分析ロジック（CLI から分離） |
| `tests/test_watch.py` (新規) | watch のテスト |
| `identity/agents.md` (修正) | Wrap に遡及チェック Step 0 を追加 |

---

### Task 1: watch モジュールのコアロジック — git log パーサー

**Files:**
- Create: `src/cognitive_memory/watch.py`
- Create: `tests/test_watch.py`

- [ ] **Step 1: Write failing test — fix コミットのカウント**

```python
# tests/test_watch.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/akira/workspace/ai-dev/cognitive-memory-lib && python3 -m pytest tests/test_watch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cognitive_memory.watch'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/cognitive_memory/watch.py
"""Git history pattern detection for cogmem watch."""
from __future__ import annotations
import re
from typing import Any


def analyze_git_history(log_lines: list[str]) -> dict[str, Any]:
    """Analyze git log --oneline output for patterns.

    Detects:
    - 3+ fix: commits → [PATTERN] "同じ修正の繰り返し"
    - revert commits → [ERROR] "リバート発生"
    - 3+ commits touching same file → [PATTERN] "同一ファイルへの集中的変更"

    Returns:
        {
            "fix_count": int,
            "revert_count": int,
            "entries": [{"category": str, "title": str, "content": str, "arousal": float}, ...],
        }
    """
    fix_count = 0
    revert_count = 0
    entries: list[dict[str, Any]] = []

    fix_messages: list[str] = []
    for line in log_lines:
        msg = line.split(" ", 1)[1] if " " in line else line
        if msg.startswith("fix:") or msg.startswith("fix(") or msg.startswith("修正:") or msg.startswith("修正("):
            fix_count += 1
            fix_messages.append(msg)
        if msg.startswith("Revert") or msg.startswith("revert"):
            revert_count += 1
            entries.append({
                "category": "ERROR",
                "title": "リバート発生",
                "content": f"コミットがリバートされた: {msg}",
                "arousal": 0.8,
            })

    if fix_count >= 3:
        entries.append({
            "category": "PATTERN",
            "title": f"修正の繰り返し（{fix_count}回）",
            "content": "同一セッションで fix: コミットが3回以上発生。\n"
                       + "\n".join(f"- {m}" for m in fix_messages),
            "arousal": 0.7,
        })

    return {
        "fix_count": fix_count,
        "revert_count": revert_count,
        "entries": entries,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_watch.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cognitive_memory/watch.py tests/test_watch.py
git commit -m "feat: watch module — git history pattern detection"
```

---

### Task 2: revert 検知とログ未記録の検出

**Files:**
- Modify: `src/cognitive_memory/watch.py`
- Modify: `tests/test_watch.py`

- [ ] **Step 1: Write failing test — revert 検知**

```python
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
```

- [ ] **Step 2: Run test — should pass** (already implemented in Task 1)

- [ ] **Step 3: Write failing test — ログ漏れ検知**

```python
from cognitive_memory.watch import detect_log_gaps

def test_detect_log_gaps():
    """Many commits with few log entries should be flagged."""
    result = detect_log_gaps(commit_count=12, log_entry_count=0)
    assert result["has_gap"] is True
    assert result["severity"] == "high"

def test_no_gap_when_logged():
    """Reasonable ratio should not flag."""
    result = detect_log_gaps(commit_count=5, log_entry_count=3)
    assert result["has_gap"] is False
```

- [ ] **Step 4: Implement detect_log_gaps**

```python
def detect_log_gaps(commit_count: int, log_entry_count: int) -> dict:
    """Detect if session has too few log entries relative to commits.

    Heuristic: expect at least 1 log entry per 4 commits.
    """
    if commit_count == 0:
        return {"has_gap": False, "severity": "none", "ratio": 0.0}

    expected_min = max(1, commit_count // 4)
    has_gap = log_entry_count < expected_min
    ratio = log_entry_count / commit_count if commit_count > 0 else 1.0

    if has_gap and log_entry_count == 0:
        severity = "high"
    elif has_gap:
        severity = "medium"
    else:
        severity = "none"

    return {"has_gap": has_gap, "severity": severity, "ratio": ratio}
```

- [ ] **Step 5: Write test — 日本語コミット検知**

```python
def test_count_japanese_fix_commits():
    """修正: prefix should also be counted as fix."""
    log_lines = [
        "abc1234 修正: スキル一覧のソート順",
        "def5678 fix: column missing",
        "ghi9012 修正: false positive matching",
    ]
    result = analyze_git_history(log_lines)
    assert result["fix_count"] == 3
```

- [ ] **Step 6: Run test — should pass** (already implemented with 修正: support)

- [ ] **Step 7: Write test — 空の git log**

```python
def test_empty_git_log():
    """Empty log should return zero counts and no entries."""
    result = analyze_git_history([])
    assert result["fix_count"] == 0
    assert result["revert_count"] == 0
    assert result["entries"] == []
```

- [ ] **Step 8: Write test — commit_count == 0 for log gaps**

```python
def test_log_gaps_zero_commits():
    """Zero commits should not flag a gap."""
    result = detect_log_gaps(commit_count=0, log_entry_count=0)
    assert result["has_gap"] is False
```

- [ ] **Step 9: Run all tests and commit**

```bash
python3 -m pytest tests/test_watch.py -v
git add src/cognitive_memory/watch.py tests/test_watch.py
git commit -m "feat: watch — revert detection, log gap analysis, i18n commit support"
```

---

### Task 3: cogmem watch CLI コマンド

**Files:**
- Create: `src/cognitive_memory/cli/watch_cmd.py`
- Modify: `src/cognitive_memory/cli/main.py`
- Modify: `tests/test_watch.py`

- [ ] **Step 1: Write failing test — CLI 出力**

```python
def test_watch_cli_json_output(tmp_path, monkeypatch):
    """cogmem watch --json should output analysis results."""
    import json
    from cognitive_memory.cli.main import main
    from io import StringIO
    import sys

    # Create a minimal git repo with fix commits
    import subprocess
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    (tmp_path / "a.txt").write_text("a")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: init"], cwd=tmp_path, capture_output=True)
    for i in range(3):
        (tmp_path / "a.txt").write_text(f"fix {i}")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"fix: issue {i}"], cwd=tmp_path, capture_output=True)

    # Create cogmem.toml
    (tmp_path / "cogmem.toml").write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
    (tmp_path / "memory" / "logs").mkdir(parents=True)

    captured = StringIO()
    monkeypatch.setattr(sys, "stdout", captured)
    main(["watch", "--json"])
    output = json.loads(captured.getvalue())
    assert output["fix_count"] == 3
    assert len(output["entries"]) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement watch_cmd.py**

```python
# src/cognitive_memory/cli/watch_cmd.py
"""cogmem watch — detect patterns from git history."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date

from ..config import CogMemConfig
from ..watch import analyze_git_history, detect_log_gaps


def run_watch(since: str = "today", json_output: bool = False, auto_log: bool = False):
    config = CogMemConfig.find_and_load()

    # Get git log
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--oneline"],
            capture_output=True, text=True, cwd=config._base_dir,
        )
        log_lines = [l for l in result.stdout.strip().split("\n") if l]
    except FileNotFoundError:
        print("git not found", file=sys.stderr)
        sys.exit(1)

    analysis = analyze_git_history(log_lines)

    # Count today's log entries
    today = date.today().isoformat()
    log_file = config.logs_path / f"{today}.md"
    log_entry_count = 0
    if log_file.exists():
        import re
        text = log_file.read_text(encoding="utf-8")
        log_entry_count = len(re.findall(r"^### ", text, re.MULTILINE))

    gap = detect_log_gaps(len(log_lines), log_entry_count)
    analysis["log_gap"] = gap
    analysis["commit_count"] = len(log_lines)
    analysis["log_entry_count"] = log_entry_count

    if json_output:
        print(json.dumps(analysis, ensure_ascii=False, indent=2))
    else:
        print(f"Commits: {len(log_lines)} | Log entries: {log_entry_count} | Fix: {analysis['fix_count']} | Revert: {analysis['revert_count']}")
        if gap["has_gap"]:
            print(f"⚠️  Log gap detected (severity: {gap['severity']})")
        for entry in analysis["entries"]:
            print(f"  [{entry['category']}] {entry['title']}")

    # Auto-log to session log if requested
    if auto_log and analysis["entries"]:
        _append_to_log(config, analysis["entries"])


def _append_to_log(config: CogMemConfig, entries: list[dict]):
    """Append detected patterns to today's session log."""
    from datetime import date
    today = date.today().isoformat()
    log_file = config.logs_path / f"{today}.md"

    lines = []
    for entry in entries:
        lines.append(f"\n### [{entry['category']}] {entry['title']} (auto-detected)")
        lines.append(f"*Arousal: {entry['arousal']} | Emotion: AutoDetection*")
        lines.append(entry["content"])
        lines.append("\n---\n")

    if log_file.exists():
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))
    # If log file doesn't exist, skip (Wrap will create it)
```

- [ ] **Step 4: Register in main.py**

Add to `main.py`:
```python
# watch
watch_parser = subparsers.add_parser("watch", help="Detect patterns from git history")
watch_parser.add_argument("--since", type=str, default="today", help="Git log --since value")
watch_parser.add_argument("--json", action="store_true", help="JSON output")
watch_parser.add_argument("--auto-log", action="store_true", help="Auto-append detected patterns to session log")
```

And in dispatch:
```python
elif args.command == "watch":
    from .watch_cmd import run_watch
    run_watch(since=args.since, json_output=args.json, auto_log=args.auto_log)
```

- [ ] **Step 5: Write test — テキスト出力モード**

```python
def test_watch_cli_text_output(tmp_path, monkeypatch, capsys):
    """cogmem watch (without --json) should print human-readable summary."""
    import subprocess
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
    (tmp_path / "a.txt").write_text("a")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: init"], cwd=tmp_path, capture_output=True)
    (tmp_path / "cogmem.toml").write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
    (tmp_path / "memory" / "logs").mkdir(parents=True)

    from cognitive_memory.cli.watch_cmd import run_watch
    run_watch(since="today")
    captured = capsys.readouterr()
    assert "Commits:" in captured.out
    assert "Fix:" in captured.out
```

- [ ] **Step 6: Write test — git not found**

```python
def test_watch_git_not_found(tmp_path, monkeypatch):
    """Should exit gracefully when git is not available."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "cogmem.toml").write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
    (tmp_path / "memory" / "logs").mkdir(parents=True)
    # Mock subprocess to raise FileNotFoundError
    import subprocess as sp
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
```

- [ ] **Step 7: Write test — log file does not exist for auto-log**

```python
def test_append_to_log_no_file(tmp_path):
    """_append_to_log should skip when log file doesn't exist."""
    from cognitive_memory.config import CogMemConfig
    from cognitive_memory.cli.watch_cmd import _append_to_log
    config = CogMemConfig(_base_dir=str(tmp_path), logs_dir="memory/logs")
    (tmp_path / "memory" / "logs").mkdir(parents=True)
    entries = [{"category": "PATTERN", "title": "test", "content": "test", "arousal": 0.7}]
    # Should not raise — just skip
    _append_to_log(config, entries)
```

- [ ] **Step 8: Run all tests and commit**

```bash
python3 -m pytest tests/test_watch.py -v
git add src/cognitive_memory/cli/watch_cmd.py src/cognitive_memory/cli/main.py tests/test_watch.py
git commit -m "feat: cogmem watch CLI command with full test coverage"
```

---

### Task 4: スキル自動生成シグナルの検知

**Files:**
- Modify: `src/cognitive_memory/watch.py`
- Modify: `tests/test_watch.py`

- [ ] **Step 1: Write failing test — スキル生成シグナル**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Add skill signal detection to analyze_git_history**

同じキーワードを含む fix コミットが3回以上 → `skill_signals` に追加。

```python
# In analyze_git_history, after fix counting:
# Group fix commits by common words
from collections import Counter
if fix_count >= 3:
    word_counts = Counter()
    for msg in fix_messages:
        words = re.findall(r"[a-zA-Z]{3,}", msg.lower())
        word_counts.update(words)
    common = [w for w, c in word_counts.items() if c >= 3 and w not in ("fix", "the", "for")]
    if common:
        skill_signals.append({
            "pattern": f"Repeated fixes related to: {', '.join(common[:3])}",
            "fix_count": fix_count,
            "suggestion": f"Consider creating a skill for {common[0]} handling",
        })
```

- [ ] **Step 4: Run tests and commit**

```bash
python3 -m pytest tests/test_watch.py -v
git commit -am "feat: watch — skill creation signal detection"
```

---

### Task 5: agents.md に Wrap 遡及チェックを追加

**Files:**
- Modify: `identity/agents.md` (open-claude プロジェクト)

- [ ] **Step 1: agents.md の Wrap セクションに Step 0 を追加**

```markdown
## Wrap（セッションクローズ）

### Step 0: 遡及チェック（Wrap 最初に実行）

`cogmem watch --since "8 hours ago" --json` を実行する。

結果に基づいて:
- `fix_count >= 3` → [PATTERN] エントリをログに追記（まだ記録されていなければ）
- `revert_count >= 1` → [ERROR] エントリをログに追記（まだ記録されていなければ）
- `log_gap.has_gap == true` → ログ漏れ警告をユーザーに通知
- `skill_signals` がある → スキル自動生成の候補をユーザーに通知
- 上記いずれかに該当した場合、`cogmem watch --auto-log` で自動追記

その後、通常の Wrap ステップ（1〜5）を実行する。
```

- [ ] **Step 2: Commit**

```bash
cd /Users/akira/workspace/open-claude
git add identity/agents.md
git commit -m "feat: add Wrap Step 0 — retroactive check via cogmem watch"
```

---

### Task 6: 統合テストと全テスト実行

**Files:**
- Modify: `tests/test_watch.py`

- [ ] **Step 1: 統合テスト追加**

```python
def test_full_watch_with_auto_log(tmp_path, monkeypatch):
    """cogmem watch --auto-log should append entries to session log."""
    import subprocess
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)

    (tmp_path / "cogmem.toml").write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
    logs_dir = tmp_path / "memory" / "logs"
    logs_dir.mkdir(parents=True)

    # Create commits with fix pattern
    for i in range(4):
        (tmp_path / "a.txt").write_text(f"v{i}")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"fix: issue {i}"], cwd=tmp_path, capture_output=True)

    # Create existing log file
    from datetime import date
    log_file = logs_dir / f"{date.today().isoformat()}.md"
    log_file.write_text("# Session Log\n\n## ログエントリ\n")

    from cognitive_memory.cli.watch_cmd import run_watch
    run_watch(since="today", auto_log=True)

    content = log_file.read_text()
    assert "[PATTERN]" in content
    assert "auto-detected" in content
```

- [ ] **Step 2: 全テスト実行**

```bash
python3 -m pytest tests/ -v
```

- [ ] **Step 3: Commit**

```bash
git commit -am "test: integration test for cogmem watch --auto-log"
```

---

## 検証方法

1. `cogmem watch` を open-claude ディレクトリで実行し、今日のセッションの fix コミットが検知されることを確認
2. `cogmem watch --json` で JSON 出力が正しいことを確認
3. `cogmem watch --auto-log` でログファイルにエントリが追記されることを確認
4. `python3 -m pytest tests/test_watch.py -v` で全テスト通過
5. `python3 -m pytest tests/ -v` で既存テストにリグレッションがないことを確認
