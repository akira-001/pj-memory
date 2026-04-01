"""cogmem init — scaffold a new project."""

from __future__ import annotations

import getpass
import re
import shutil
import subprocess
import sys
from pathlib import Path

_SCAFFOLD_DIR = Path(__file__).resolve().parent.parent / "templates"


def _validate_hooks_schema(settings: dict) -> None:
    """Validate that hooks in settings follow Claude Code's expected schema.

    Expected: { hooks: { EventName: [{ matcher: str, hooks: [{ type: str, command: str }] }] } }
    Raises ValueError if the structure is invalid.
    """
    hooks = settings.get("hooks")
    if hooks is None:
        return
    if not isinstance(hooks, dict):
        raise ValueError(f"hooks must be a dict, got {type(hooks).__name__}")
    for event_name, entries in hooks.items():
        if not isinstance(entries, list):
            raise ValueError(f"hooks.{event_name} must be a list")
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValueError(f"hooks.{event_name}[{i}] must be a dict")
            if "hooks" not in entry:
                raise ValueError(
                    f"hooks.{event_name}[{i}]: missing 'hooks' array. "
                    f"Got keys: {list(entry.keys())}"
                )
            if not isinstance(entry["hooks"], list):
                raise ValueError(f"hooks.{event_name}[{i}].hooks must be a list")
            for j, hook in enumerate(entry["hooks"]):
                if not isinstance(hook, dict):
                    raise ValueError(f"hooks.{event_name}[{i}].hooks[{j}] must be a dict")
                if hook.get("type") not in ("command",):
                    raise ValueError(
                        f"hooks.{event_name}[{i}].hooks[{j}].type must be 'command', "
                        f"got {hook.get('type')!r}"
                    )
                if "command" not in hook:
                    raise ValueError(f"hooks.{event_name}[{i}].hooks[{j}]: missing 'command'")


def setup_hooks(settings_dir: str) -> None:
    """Register cogmem hooks in .claude/settings.json."""
    import json
    settings_path = Path(settings_dir) / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    settings: dict = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    hooks = settings.setdefault("hooks", {})

    # Add skill-gate hook (PreToolUse)
    pre_hooks = hooks.setdefault("PreToolUse", [])
    if not any(
        "cogmem hook skill-gate" in cmd.get("command", "")
        for h in pre_hooks
        for cmd in h.get("hooks", [])
    ):
        pre_hooks.append({
            "matcher": "Edit|Write",
            "hooks": [{"type": "command", "command": "cogmem hook skill-gate"}],
        })

    # Add failure-breaker hook (PostToolUse)
    post_hooks = hooks.setdefault("PostToolUse", [])
    if not any(
        "cogmem hook failure-breaker" in cmd.get("command", "")
        for h in post_hooks
        for cmd in h.get("hooks", [])
    ):
        post_hooks.append({
            "matcher": "Bash",
            "hooks": [{"type": "command", "command": "cogmem hook failure-breaker"}],
        })

    _validate_hooks_schema(settings)

    settings_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

# Messages per language
_MSG = {
    "en": {
        "created": "Created {}",
        "exists": "cogmem.toml already exists at {}",
        "claude_skip": "CLAUDE.md already contains Cognitive Memory section, skipping",
        "claude_append": "Appended Cognitive Memory section to {}",
        "updated": "Updated {}",
        "skills_installed": "Installed {} agent skills to ~/.claude/skills/",
        "skills_skipped": "Skipped existing skill: {}",
        "done_title": "Setup complete! Next steps:",
        "step1": "  1. Edit identity/soul.md to define your agent's personality",
        "step2": "  2. Start Claude Code — CLAUDE.md will be loaded automatically",
        "step3": "  3. Your agent now has cognitive memory!",
        "step4": "  4. Skills in .claude/skills/ will be auto-loaded by the agent",
        "optional": "Optional:",
        "opt1": "  - Install Ollama for semantic search: brew install ollama",
        "opt2": "  - Run: ollama pull zylonai/multilingual-e5-large",
        "opt3": "  - Export skills from DB: cogmem skills export",
        "skill_creator_installed": "Installed Anthropic official skill-creator plugin",
        "skill_creator_exists": "skill-creator plugin already installed",
        "skill_creator_skip": "Claude Code not found — install skill-creator manually: claude plugins install skill-creator@claude-plugins-official",
        "skill_creator_fail": "Failed to install skill-creator plugin (install manually: claude plugins install skill-creator@claude-plugins-official)",
        "user_id_prompt": "Enter your user ID for log isolation (default: {}): ",
        "user_id_taken": "User ID '{}' is already in use (logs exist at {}). Choose a different ID.",
        "user_id_set": "User ID set to: {}",
    },
    "ja": {
        "created": "作成しました: {}",
        "exists": "cogmem.toml は既に存在します: {}",
        "claude_skip": "CLAUDE.md には既に Cognitive Memory セクションがあります。スキップします",
        "claude_append": "CLAUDE.md に Cognitive Memory セクションを追記しました: {}",
        "updated": "更新しました: {}",
        "skills_installed": "エージェントスキル {} 件を ~/.claude/skills/ にインストールしました",
        "skills_skipped": "既存スキルをスキップ: {}",
        "done_title": "セットアップ完了！次のステップ:",
        "step1": "  1. identity/soul.md を編集してエージェントの人格を定義してください",
        "step2": "  2. Claude Code を起動 — CLAUDE.md が自動的に読み込まれます",
        "step3": "  3. エージェントに認知的記憶が備わりました！",
        "step4": "  4. .claude/skills/ のスキルがエージェントに自動読み込みされます",
        "optional": "オプション:",
        "opt1": "  - セマンティック検索用に Ollama をインストール: brew install ollama",
        "opt2": "  - 実行: ollama pull zylonai/multilingual-e5-large",
        "opt3": "  - スキルをDBからエクスポート: cogmem skills export",
        "skill_creator_installed": "Anthropic 公式 skill-creator プラグインをインストールしました",
        "skill_creator_exists": "skill-creator プラグインはインストール済みです",
        "skill_creator_skip": "Claude Code が見つかりません — 手動でインストールしてください: claude plugins install skill-creator@claude-plugins-official",
        "skill_creator_fail": "skill-creator プラグインのインストールに失敗しました（手動: claude plugins install skill-creator@claude-plugins-official）",
        "user_id_prompt": "ログ分離用のユーザーIDを入力してください (デフォルト: {}): ",
        "user_id_taken": "ユーザーID '{}' は既に使用されています (ログが {} に存在)。別のIDを選んでください。",
        "user_id_set": "ユーザーIDを設定しました: {}",
    },
}


_DEFAULT_MEMORY_RECALL_SKILL = {
    "en": """# Memory Recall Skill

## Triggers
- User references past conversations ("we talked about", "last time", "remember")
- Ambiguous references that need context

## Steps
1. Check the current conversation context for the answer
2. If not found, search memory with cogmem:
   ```bash
   cogmem search "query" --json --top-k 5
   ```
3. Integrate results naturally into the conversation

## Expression Rules
- When searching: "Let me think back..."
- Forbidden: "Searching", "Checking records", "Looking up history"
- Respond naturally as if recalling from memory

## Notes
- Always search before saying "I don't know"
""",
    "ja": """# 記憶の検索と文脈把握スキル

## トリガー
- ユーザーが過去の会話内容を参照した時（「前に話した」「さっきの」等）
- 曖昧な参照があった時

## 手順
1. まず現在の会話コンテキストから答えを探す
2. 見つからない場合、cogmem searchで記憶を検索する:
   ```bash
   cogmem search "検索クエリ" --json --top-k 5
   ```
3. 検索結果を自然に会話に組み込む

## 表現ルール
- 検索時: 「少し待って、思い出してみる...」
- 禁止: 「検索する」「確認する」「履歴を調べる」等のシステム的表現
- 覚えている体で自然に回答すること

## 注意点
- 「わからない」と答える前に必ず検索すること
""",
}


def _install_agent_skills(tmpl_dir: Path, msg: dict) -> None:
    """Install agent protocol skills to ~/.claude/skills/."""
    global_skills_dir = Path.home() / ".claude" / "skills"
    skills_src = tmpl_dir / "skills"
    if not skills_src.is_dir():
        # Fallback to base template skills dir
        skills_src = _SCAFFOLD_DIR / "skills"
    if not skills_src.is_dir():
        return

    installed = 0
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir():
            continue
        dest_dir = global_skills_dir / skill_dir.name
        dest_skill = dest_dir / "SKILL.md"
        if dest_skill.exists():
            print(msg["skills_skipped"].format(skill_dir.name))
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(skill_dir / "SKILL.md", dest_skill)
        installed += 1

    if installed:
        print(msg["skills_installed"].format(installed))


def _install_skill_creator(msg: dict) -> None:
    """Install Anthropic official skill-creator plugin if not present."""
    claude_bin = shutil.which("claude")
    if not claude_bin:
        print(msg["skill_creator_skip"])
        return

    # Check if already installed
    try:
        result = subprocess.run(
            [claude_bin, "plugins", "list"],
            capture_output=True, text=True, timeout=15,
        )
        if "skill-creator" in result.stdout:
            print(msg["skill_creator_exists"])
            return
    except (subprocess.TimeoutExpired, OSError):
        pass

    # Install
    try:
        result = subprocess.run(
            [claude_bin, "plugins", "install", "skill-creator@claude-plugins-official"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            print(msg["skill_creator_installed"])
        else:
            print(msg["skill_creator_fail"])
    except (subprocess.TimeoutExpired, OSError):
        print(msg["skill_creator_fail"])


def _select_language() -> str:
    """Prompt user to select language. Returns 'en' or 'ja'."""
    print()
    print("Select language / 言語を選択してください:")
    print("  1. English")
    print("  2. 日本語")
    print()
    try:
        choice = input("Enter 1 or 2 (default: 1): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = ""
    if choice == "2":
        return "ja"
    return "en"


def _get_existing_user_ids(logs_dir: Path) -> set[str]:
    """Return set of user IDs that already have logs in the logs directory."""
    if not logs_dir.is_dir():
        return set()
    ids = set()
    for child in logs_dir.iterdir():
        if child.is_dir() and not child.name.startswith("."):
            # Check if the subdirectory contains log files
            has_logs = any(f.suffix == ".md" for f in child.iterdir() if f.is_file())
            if has_logs:
                ids.add(child.name)
    return ids


def _prompt_user_id(logs_dir: Path, msg: dict) -> str:
    """Prompt user for their user_id, rejecting IDs already in use."""
    default_id = getpass.getuser()
    existing_ids = _get_existing_user_ids(logs_dir)

    while True:
        try:
            raw = input(msg["user_id_prompt"].format(default_id)).strip()
        except (EOFError, KeyboardInterrupt):
            raw = ""
        user_id = raw or default_id

        # Sanitize: only allow alphanumeric, dash, underscore
        if not re.match(r"^[a-zA-Z0-9_-]+$", user_id):
            print("Invalid ID. Use only letters, numbers, dashes, and underscores.")
            continue

        if user_id in existing_ids:
            print(msg["user_id_taken"].format(user_id, logs_dir / user_id))
            continue

        return user_id


def _get_template_dir(lang: str) -> Path:
    """Return the template directory for the given language."""
    if lang == "ja":
        ja_dir = _SCAFFOLD_DIR / "ja"
        if ja_dir.is_dir():
            return ja_dir
    return _SCAFFOLD_DIR


def run_init(target_dir: str = ".", lang: str | None = None, user_id: str | None = None):
    if not _SCAFFOLD_DIR.is_dir():
        raise RuntimeError(
            f"cogmem templates directory not found at {_SCAFFOLD_DIR}. "
            "The package may be installed incorrectly."
        )

    # Language selection
    if lang is None:
        lang = _select_language()
    if lang not in ("en", "ja"):
        lang = "en"

    msg = _MSG[lang]
    tmpl_dir = _get_template_dir(lang)

    target = Path(target_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)

    # Determine user_id
    logs_dir = target / "memory" / "logs"
    if user_id is None:
        user_id = _prompt_user_id(logs_dir, msg)
    print(msg["user_id_set"].format(user_id))

    # Write cogmem.toml (language-independent, always from base dir)
    toml_path = target / "cogmem.toml"
    if toml_path.exists():
        print(msg["exists"].format(toml_path), file=sys.stderr)
    else:
        template = (_SCAFFOLD_DIR / "cogmem.toml").read_text(encoding="utf-8")
        toml_path.write_text(template, encoding="utf-8")
        print(msg["created"].format(toml_path))

    # Write user_id to cogmem.local.toml (gitignored, per-user)
    local_toml_path = target / "cogmem.local.toml"
    local_toml_path.write_text(
        f'[cogmem]\nuser_id = "{user_id}"\n', encoding="utf-8"
    )
    print(msg["created"].format(local_toml_path))

    # Create identity directory
    identity_dir = target / "identity"
    identity_dir.mkdir(parents=True, exist_ok=True)

    for fname in ("agents.md", "soul.md", "user.md"):
        dest = identity_dir / fname
        if not dest.exists():
            src = tmpl_dir / fname
            if not src.exists():
                src = _SCAFFOLD_DIR / fname
            template = src.read_text(encoding="utf-8")
            dest.write_text(template, encoding="utf-8")
            print(msg["created"].format(dest))

    # Create per-user identity file: identity/users/{user_id}.md
    users_dir = identity_dir / "users"
    users_dir.mkdir(parents=True, exist_ok=True)
    user_identity = users_dir / f"{user_id}.md"
    if not user_identity.exists():
        # Copy from user.md template
        src = tmpl_dir / "user.md"
        if not src.exists():
            src = _SCAFFOLD_DIR / "user.md"
        template = src.read_text(encoding="utf-8")
        user_identity.write_text(template, encoding="utf-8")
        print(msg["created"].format(user_identity))

    # Create logs directory (with user_id subdirectory)
    user_logs_dir = target / "memory" / "logs" / user_id
    user_logs_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = user_logs_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    print(msg["created"].format(str(user_logs_dir) + "/"))

    # Create knowledge directory
    knowledge_dir = target / "memory" / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    for fname in ("summary.md", "error-patterns.md"):
        dest = knowledge_dir / fname
        if not dest.exists():
            src = tmpl_dir / fname
            if not src.exists():
                src = _SCAFFOLD_DIR / fname
            template = src.read_text(encoding="utf-8")
            dest.write_text(template, encoding="utf-8")
            print(msg["created"].format(dest))

    # Create contexts directory (with user_id subdirectory)
    user_contexts_dir = target / "memory" / "contexts" / user_id
    user_contexts_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = user_contexts_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    print(msg["created"].format(str(user_contexts_dir) + "/"))

    # Create .claude/skills/ directory with sample skill
    skills_dir = target / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    sample_skill = skills_dir / "memory-recall.md"
    if not sample_skill.exists():
        src = tmpl_dir / "skill-memory-recall.md"
        if not src.exists():
            src = _SCAFFOLD_DIR / "skill-memory-recall.md"
        if src.exists():
            sample_skill.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            sample_skill.write_text(_DEFAULT_MEMORY_RECALL_SKILL[lang], encoding="utf-8")
        print(msg["created"].format(sample_skill))
    print(msg["created"].format(str(skills_dir) + "/"))

    # CLAUDE.md — append mode
    claude_md = target / "CLAUDE.md"
    cogmem_marker = "# Cognitive Memory Agent"
    src = tmpl_dir / "CLAUDE.md"
    if not src.exists():
        src = _SCAFFOLD_DIR / "CLAUDE.md"
    claude_template = src.read_text(encoding="utf-8")

    if claude_md.exists():
        existing = claude_md.read_text(encoding="utf-8")
        if cogmem_marker in existing:
            print(msg["claude_skip"])
        else:
            with open(claude_md, "a", encoding="utf-8") as f:
                f.write("\n\n" + claude_template)
            print(msg["claude_append"].format(claude_md))
    else:
        claude_md.write_text(claude_template, encoding="utf-8")
        print(msg["created"].format(claude_md))

    # Update .gitignore (language-independent)
    gitignore = target / ".gitignore"
    gitignore_template = _SCAFFOLD_DIR / "gitignore"

    if gitignore_template.exists():
        template_content = gitignore_template.read_text(encoding="utf-8")
        if gitignore.exists():
            existing = gitignore.read_text(encoding="utf-8")
            existing_lines = {l.strip() for l in existing.splitlines()}
            missing_lines = []
            for line in template_content.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and stripped not in existing_lines:
                    missing_lines.append(line)
            if missing_lines:
                with open(gitignore, "a", encoding="utf-8") as f:
                    f.write("\n# Cognitive Memory\n")
                    f.write("\n".join(missing_lines) + "\n")
                print(msg["updated"].format(gitignore))
        else:
            gitignore.write_text(template_content, encoding="utf-8")
            print(msg["created"].format(gitignore))
    else:
        db_entry = "*.db"
        if gitignore.exists():
            content = gitignore.read_text()
            if db_entry not in content:
                with open(gitignore, "a") as f:
                    f.write(f"\n# Cognitive Memory\n{db_entry}\n")
                print(msg["updated"].format(gitignore))
        else:
            gitignore.write_text(f"# Cognitive Memory\n{db_entry}\n")
            print(msg["created"].format(gitignore))

    # Install agent protocol skills to ~/.claude/skills/
    _install_agent_skills(tmpl_dir, msg)

    # Install Anthropic official skill-creator plugin
    _install_skill_creator(msg)

    # Setup Claude Code hooks
    claude_dir = Path(target_dir) / ".claude"
    setup_hooks(str(claude_dir))
    print(f"  hooks → {claude_dir / 'settings.json'}")

    print()
    print(msg["done_title"])
    print()
    print(msg["step1"])
    print(msg["step2"])
    print(msg["step3"])
    print(msg["step4"])
    print()
    print(msg["optional"])
    print(msg["opt1"])
    print(msg["opt2"])
    print(msg["opt3"])
    print()
