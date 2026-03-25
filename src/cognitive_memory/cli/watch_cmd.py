# src/cognitive_memory/cli/watch_cmd.py
"""cogmem watch — detect patterns from git history."""
from __future__ import annotations

import json
import re
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
