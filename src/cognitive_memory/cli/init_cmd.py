"""cogmem init — scaffold a new project."""

from __future__ import annotations

import sys
from pathlib import Path

_SCAFFOLD_DIR = Path(__file__).resolve().parent.parent / "scaffold"


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

    # Create logs directory
    logs_dir = target / "memory" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = logs_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
    print(f"Created {logs_dir}/")

    # Update .gitignore
    gitignore = target / ".gitignore"
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
    print("  1. Write session logs to memory/logs/YYYY-MM-DD.md")
    print("  2. Run: cogmem index")
    print("  3. Run: cogmem search 'your query'")
    print()
    print("For AI coding tools, add to your tool config:")
    print("  Claude Code: Add to .claude/commands/")
    print("  Cursor:      Add to .cursorrules")
    print("  Cline:       Add to .clinerules")
