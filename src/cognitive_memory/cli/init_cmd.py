"""cogmem init — scaffold a new project."""

from __future__ import annotations

import sys
from pathlib import Path

_SCAFFOLD_DIR = Path(__file__).resolve().parent.parent / "templates"

# Messages per language
_MSG = {
    "en": {
        "created": "Created {}",
        "exists": "cogmem.toml already exists at {}",
        "claude_skip": "CLAUDE.md already contains Cognitive Memory section, skipping",
        "claude_append": "Appended Cognitive Memory section to {}",
        "updated": "Updated {}",
        "done_title": "Setup complete! Next steps:",
        "step1": "  1. Edit identity/soul.md to define your agent's personality",
        "step2": "  2. Start Claude Code — CLAUDE.md will be loaded automatically",
        "step3": "  3. Your agent now has cognitive memory!",
        "optional": "Optional:",
        "opt1": "  - Install Ollama for semantic search: brew install ollama",
        "opt2": "  - Run: ollama pull zylonai/multilingual-e5-large",
    },
    "ja": {
        "created": "作成しました: {}",
        "exists": "cogmem.toml は既に存在します: {}",
        "claude_skip": "CLAUDE.md には既に Cognitive Memory セクションがあります。スキップします",
        "claude_append": "CLAUDE.md に Cognitive Memory セクションを追記しました: {}",
        "updated": "更新しました: {}",
        "done_title": "セットアップ完了！次のステップ:",
        "step1": "  1. identity/soul.md を編集してエージェントの人格を定義してください",
        "step2": "  2. Claude Code を起動 — CLAUDE.md が自動的に読み込まれます",
        "step3": "  3. エージェントに認知的記憶が備わりました！",
        "optional": "オプション:",
        "opt1": "  - セマンティック検索用に Ollama をインストール: brew install ollama",
        "opt2": "  - 実行: ollama pull zylonai/multilingual-e5-large",
    },
}


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


def _get_template_dir(lang: str) -> Path:
    """Return the template directory for the given language."""
    if lang == "ja":
        ja_dir = _SCAFFOLD_DIR / "ja"
        if ja_dir.is_dir():
            return ja_dir
    return _SCAFFOLD_DIR


def run_init(target_dir: str = ".", lang: str | None = None):
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

    # Write cogmem.toml (language-independent, always from base dir)
    toml_path = target / "cogmem.toml"
    if toml_path.exists():
        print(msg["exists"].format(toml_path), file=sys.stderr)
    else:
        template = (_SCAFFOLD_DIR / "cogmem.toml").read_text(encoding="utf-8")
        toml_path.write_text(template, encoding="utf-8")
        print(msg["created"].format(toml_path))

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

    # Create logs directory
    logs_dir = target / "memory" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = logs_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    print(msg["created"].format(str(logs_dir) + "/"))

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

    # Create contexts directory
    contexts_dir = target / "memory" / "contexts"
    contexts_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = contexts_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    print(msg["created"].format(str(contexts_dir) + "/"))

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

    print()
    print(msg["done_title"])
    print()
    print(msg["step1"])
    print(msg["step2"])
    print(msg["step3"])
    print()
    print(msg["optional"])
    print(msg["opt1"])
    print(msg["opt2"])
    print()
