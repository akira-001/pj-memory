"""cogmem init — scaffold a new project."""

from __future__ import annotations

import sys
from pathlib import Path

_SCAFFOLD_DIR = Path(__file__).resolve().parent.parent / "templates"


def run_init(target_dir: str = "."):
    target = Path(target_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)

    # Write cogmem.toml
    toml_path = target / "cogmem.toml"
    if toml_path.exists():
        print(f"cogmem.toml already exists at {toml_path}", file=sys.stderr)
    else:
        template = (_SCAFFOLD_DIR / "cogmem.toml").read_text(encoding="utf-8")
        toml_path.write_text(template, encoding="utf-8")
        print(f"Created {toml_path}")

    # Create identity directory
    identity_dir = target / "identity"
    identity_dir.mkdir(parents=True, exist_ok=True)

    for fname in ("agent.md", "user.md"):
        dest = identity_dir / fname
        if not dest.exists():
            template = (_SCAFFOLD_DIR / fname).read_text(encoding="utf-8")
            dest.write_text(template, encoding="utf-8")
            print(f"Created {dest}")

    # Create logs directory
    logs_dir = target / "memory" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = logs_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    print(f"Created {logs_dir}/")

    # Create knowledge directory
    knowledge_dir = target / "memory" / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    for fname, template_name in (
        ("summary.md", "summary.md"),
        ("error-patterns.md", "error-patterns.md"),
    ):
        dest = knowledge_dir / fname
        if not dest.exists():
            template = (_SCAFFOLD_DIR / template_name).read_text(encoding="utf-8")
            dest.write_text(template, encoding="utf-8")
            print(f"Created {dest}")

    # Create contexts directory
    contexts_dir = target / "memory" / "contexts"
    contexts_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = contexts_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    print(f"Created {contexts_dir}/")

    # CLAUDE.md — append mode
    claude_md = target / "CLAUDE.md"
    cogmem_marker = "# Cognitive Memory Agent"
    claude_template = (_SCAFFOLD_DIR / "CLAUDE.md").read_text(encoding="utf-8")

    if claude_md.exists():
        existing = claude_md.read_text(encoding="utf-8")
        if cogmem_marker in existing:
            print("CLAUDE.md already contains Cognitive Memory section, skipping")
        else:
            with open(claude_md, "a", encoding="utf-8") as f:
                f.write("\n\n" + claude_template)
            print(f"Appended Cognitive Memory section to {claude_md}")
    else:
        claude_md.write_text(claude_template, encoding="utf-8")
        print(f"Created {claude_md}")

    # Update .gitignore
    gitignore = target / ".gitignore"
    gitignore_template = _SCAFFOLD_DIR / "gitignore"

    if gitignore_template.exists():
        template_content = gitignore_template.read_text(encoding="utf-8")
        if gitignore.exists():
            existing = gitignore.read_text(encoding="utf-8")
            # Collect lines from template that are missing in existing
            missing_lines = []
            for line in template_content.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and stripped not in existing:
                    missing_lines.append(line)
            if missing_lines:
                with open(gitignore, "a", encoding="utf-8") as f:
                    f.write("\n# Cognitive Memory\n")
                    f.write("\n".join(missing_lines) + "\n")
                print(f"Updated {gitignore}")
        else:
            gitignore.write_text(template_content, encoding="utf-8")
            print(f"Created {gitignore}")
    else:
        # Fallback: ensure *.db is in .gitignore
        db_entry = "*.db"
        if gitignore.exists():
            content = gitignore.read_text()
            if db_entry not in content:
                with open(gitignore, "a") as f:
                    f.write(f"\n# Cognitive Memory\n{db_entry}\n")
                print(f"Updated {gitignore}")
        else:
            gitignore.write_text(f"# Cognitive Memory\n{db_entry}\n")
            print(f"Created {gitignore}")

    print()
    print("Setup complete! Next steps:")
    print()
    print("  1. Edit identity/agent.md to customize your agent's personality")
    print("  2. Start Claude Code — CLAUDE.md will be loaded automatically")
    print("  3. Your agent now has cognitive memory!")
    print()
    print("Optional:")
    print("  - Install Ollama for semantic search: brew install ollama")
    print("  - Run: ollama pull zylonai/multilingual-e5-large")
    print()
