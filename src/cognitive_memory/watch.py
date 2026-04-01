"""Git history pattern detection for cogmem watch."""
from __future__ import annotations
import re
from collections import Counter
from typing import Any


def analyze_git_history(log_lines: list[str]) -> dict[str, Any]:
    """Analyze git log --oneline output for patterns.

    Detects:
    - 3+ fix: commits → [PATTERN] "同じ修正の繰り返し"
    - revert commits → [ERROR] "リバート発生"

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
    skill_signals: list[dict[str, Any]] = []

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

        # Skill creation signals: group fix commits by common words
        word_counts: Counter[str] = Counter()
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

    # Workflow pattern detection
    workflow_patterns = detect_workflow_patterns(log_lines)

    return {
        "fix_count": fix_count,
        "revert_count": revert_count,
        "entries": entries,
        "skill_signals": skill_signals,
        "workflow_patterns": workflow_patterns,
    }


def detect_workflow_patterns(
    log_lines: list[str],
    threshold: int = 2,
) -> list[dict[str, Any]]:
    """Detect repeated workflow patterns from commit message prefixes.

    Groups commits by their conventional commit prefix (e.g., "release:",
    "session:", "chore:") and flags prefixes that appear >= threshold times.
    Excludes "fix:" and "feat:" which are already tracked separately.

    Args:
        log_lines: git log --oneline output lines
        threshold: minimum occurrences to flag (default: 2)

    Returns:
        List of {"prefix": str, "count": int, "messages": list[str], "suggestion": str}
    """
    EXCLUDED = {"fix:", "fix(", "feat:", "feat(", "修正:", "修正("}

    prefix_groups: dict[str, list[str]] = {}
    for line in log_lines:
        msg = line.split(" ", 1)[1] if " " in line else line
        # Extract conventional commit prefix (word followed by colon)
        match = re.match(r"^([a-zA-Z\-]+[:(])", msg)
        if not match:
            continue
        prefix = match.group(1)
        # Normalize: "chore(" -> "chore:"
        if prefix.endswith("("):
            prefix = prefix[:-1] + ":"
        if prefix in EXCLUDED:
            continue
        prefix_groups.setdefault(prefix, []).append(msg)

    results: list[dict[str, Any]] = []
    for prefix, messages in sorted(prefix_groups.items(), key=lambda x: -len(x[1])):
        if len(messages) >= threshold:
            results.append({
                "prefix": prefix,
                "count": len(messages),
                "messages": messages,
                "suggestion": f"Repeated '{prefix}' workflow ({len(messages)} times) — consider creating a skill",
            })

    return results


def get_changed_files_since(since: str, cwd: str = ".") -> list[str]:
    """Get list of files changed in commits since the given time + staged changes."""
    import subprocess
    files: set[str] = set()

    # Committed changes
    result = subprocess.run(
        ["git", "log", f"--since={since}", "--name-only", "--pretty=format:"],
        capture_output=True, text=True, cwd=cwd,
    )
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                files.add(line.strip())

    # Staged but uncommitted
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True, cwd=cwd,
    )
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                files.add(line.strip())

    return sorted(files)


def detect_log_gaps(commit_count: int, log_entry_count: int) -> dict[str, Any]:
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
