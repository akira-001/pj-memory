"""cogmem hook — Claude Code hook handlers."""
from __future__ import annotations

import json
import os
import sys
from datetime import date as _date
from pathlib import Path


def _get_state_file() -> Path:
    """Get the state file path for failure counter."""
    override = os.environ.get("COGMEM_HOOK_STATE")
    if override:
        return Path(override)
    ppid = os.getppid()
    return Path(f"/tmp/cogmem-failure-count-{ppid}")


def run_failure_breaker(hook_input: dict, threshold: int = 2) -> None:
    """Handle PostToolUse Bash — detect consecutive failures."""
    exit_code = hook_input.get("tool_result", {}).get("exit_code", 0)

    state_file = _get_state_file()

    if exit_code == 0:
        if state_file.exists():
            state_file.unlink()
        return

    count = 0
    if state_file.exists():
        try:
            count = int(state_file.read_text().strip())
        except (ValueError, OSError):
            count = 0
    count += 1
    state_file.write_text(str(count))

    if count >= threshold and count % threshold == 0:
        msg = (
            f"\u26a0 コマンドが{count}回連続で失敗しています。\n"
            "1. 同じアプローチを繰り返さず、エラーメッセージを読んで根本原因を特定してください\n"
            "2. 環境要因（パス、権限、プロセス状態）を先に排除してください\n"
            "3. 解決後、再発防止策を検討してください:\n"
            "   - 既存スキルに手順追加が必要 → cogmem skills track で extra_step を記録\n"
            "   - 新しいパターン → cogmem skills suggest で記録"
        )
        print(msg, file=sys.stderr)


def run_skill_gate(hook_input: dict, base_dir: str | None = None) -> None:
    """Handle PreToolUse Edit|Write — check skill usage for the file."""
    file_path = hook_input.get("tool_input", {}).get("file_path", "")
    if not file_path:
        return

    try:
        from ..config import CogMemConfig
        from ..skills.store import SkillsStore

        config = CogMemConfig.find_and_load(start_dir=base_dir)
        store = SkillsStore(config)

        # Make file_path relative to base_dir for matching
        try:
            rel_path = str(Path(file_path).relative_to(config._base_dir))
        except ValueError:
            rel_path = file_path

        triggers = store.get_all_triggers(config.skill_triggers)
        matched_skills = store.match_triggers(rel_path, triggers)

        if not matched_skills:
            return

        # Check which matched skills have skill_start today
        gaps = store.check_skill_gaps([rel_path], triggers)
        for gap in gaps:
            msg = (
                f"\u26a0 このファイルに関連するスキル [{gap['expected_skill']}] "
                "が未使用です。先にスキルを確認してください。"
            )
            print(msg, file=sys.stderr)
    except Exception:
        pass  # Hook must never break the editor


def run_pre_compress(hook_input: dict, logs_dir: str | None = None) -> None:
    """Handle PreToolUse Task -- save delegation intent before context compression.

    Called when Claude Code is about to spawn a subagent (Task tool).
    Extracts the task prompt and appends it as a DELEGATION memory entry
    to today's log file, so the intent is persisted before context may be
    compressed by the subagent launch.

    Returns None always (hook must never block the tool call).
    """
    # Only act on Task tool
    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Task":
        return None

    prompt = hook_input.get("tool_input", {}).get("prompt", "").strip()
    # Ignore trivial prompts
    if len(prompt) < 20:
        return None

    # Resolve logs_dir
    if logs_dir is None:
        try:
            from ..config import CogMemConfig
            config = CogMemConfig.find_and_load()
            logs_dir = str(config.logs_path)
        except Exception:
            return None

    try:
        logs_path = Path(logs_dir)
        logs_path.mkdir(parents=True, exist_ok=True)

        today = _date.today().isoformat()
        log_file = logs_path / f"{today}.md"

        # Truncate prompt to 200 chars to avoid log bloat
        summary = prompt[:200].replace("\n", " ")

        entry = (
            f"\n### [DELEGATION] Task delegated to subagent\n"
            f"*Arousal: 0.5*\n"
            f"{summary}\n"
        )

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)

    except Exception:
        pass  # Hook must never block the tool call

    return None


def run_hook(args) -> None:
    """Entry point for cogmem hook subcommands."""
    hook_input = json.load(sys.stdin)

    if args.hook_command == "failure-breaker":
        try:
            from ..config import CogMemConfig
            config = CogMemConfig.find_and_load()
            threshold = config.consecutive_failure_threshold
        except Exception:
            threshold = 2
        run_failure_breaker(hook_input, threshold=threshold)
    elif args.hook_command == "skill-gate":
        run_skill_gate(hook_input)
    elif args.hook_command == "pre-compress":
        run_pre_compress(hook_input)
    else:
        pass
