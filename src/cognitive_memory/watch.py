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
