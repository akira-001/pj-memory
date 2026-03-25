"""Git history pattern detection for cogmem watch."""
from __future__ import annotations
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
    import re as _re
    from collections import Counter

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
            words = _re.findall(r"[a-zA-Z]{3,}", msg.lower())
            word_counts.update(words)
        common = [w for w, c in word_counts.items() if c >= 3 and w not in ("fix", "the", "for")]
        if common:
            skill_signals.append({
                "pattern": f"Repeated fixes related to: {', '.join(common[:3])}",
                "fix_count": fix_count,
                "suggestion": f"Consider creating a skill for {common[0]} handling",
            })

    return {
        "fix_count": fix_count,
        "revert_count": revert_count,
        "entries": entries,
        "skill_signals": skill_signals,
    }


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
