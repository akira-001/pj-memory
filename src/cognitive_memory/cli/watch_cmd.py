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


def run_watch(since: str = "today", json_output: bool = False, auto_log: bool = False, auto_suggest: bool = False):
    config = CogMemConfig.find_and_load()

    # Get git log
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--oneline"],
            capture_output=True, text=True, cwd=config._base_dir,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            print(result.stderr.strip(), file=sys.stderr)
            sys.exit(1)
        log_lines = [line for line in result.stdout.strip().split("\n") if line]
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

    # Skill gap detection
    from ..watch import get_changed_files_since
    from ..skills.store import SkillsStore
    changed_files = get_changed_files_since(since, config._base_dir)
    skill_gaps = []
    if changed_files:
        try:
            store = SkillsStore(config)
            triggers = store.get_all_triggers(config.skill_triggers)
            skill_gaps = store.check_skill_gaps(changed_files, triggers)
        except Exception:
            pass
    analysis["skill_gaps"] = skill_gaps

    if json_output:
        print(json.dumps(analysis, ensure_ascii=False, indent=2))
    else:
        print(f"Commits: {len(log_lines)} | Log entries: {log_entry_count} | Fix: {analysis['fix_count']} | Revert: {analysis['revert_count']}")
        if gap["has_gap"]:
            print(f"⚠️  Log gap detected (severity: {gap['severity']})")
        for entry in analysis["entries"]:
            print(f"  [{entry['category']}] {entry['title']}")
        if skill_gaps:
            for sg in skill_gaps:
                print(f"  ⚠ Skill gap: [{sg['expected_skill']}] not used (file: {sg['file']})")

    # Auto-log to session log if requested
    if auto_log and analysis["entries"]:
        _append_to_log(config, analysis["entries"])

    # Auto-suggest: record detected patterns as skill suggestions
    if auto_suggest:
        _auto_suggest(config, analysis)


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
    else:
        print(f"No session log for today ({log_file}), skipping auto-log.", file=sys.stderr)


def _auto_suggest(config: CogMemConfig, analysis: dict):
    """Record detected patterns as skill suggestions via SkillsStore."""
    from ..skills.store import SkillsStore

    signals = analysis.get("skill_signals", [])
    patterns = analysis.get("workflow_patterns", [])

    if not signals and not patterns:
        return

    try:
        store = SkillsStore(config)
    except Exception:
        return

    count = 0
    for sig in signals:
        context = sig.get("pattern", "")
        if not context:
            continue
        desc = sig.get("suggestion", "")
        store.add_suggestion(context=context, description=desc)
        count += 1

    for pat in patterns:
        context = pat.get("prefix", "").rstrip(":")
        if not context:
            continue
        desc = f"Repeated '{pat['prefix']}' workflow ({pat['count']} times)"
        store.add_suggestion(context=context, description=desc)
        count += 1

    if count:
        print(f"Auto-suggested {count} pattern(s) for skill creation.", file=sys.stderr)
