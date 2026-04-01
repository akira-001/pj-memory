"""cogmem hook — Claude Code hook handlers."""
from __future__ import annotations

import json
import os
import sys
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
        pass  # Will be implemented in Task 4
    else:
        pass
