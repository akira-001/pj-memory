"""cogmem migrate — upgrade project files from older versions."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def run_migrate(target_dir: str = "."):
    target = Path(target_dir).resolve()
    changes = []

    # 1. Rename identity/agent.md → identity/soul.md
    agent_md = target / "identity" / "agent.md"
    soul_md = target / "identity" / "soul.md"

    if agent_md.exists() and not soul_md.exists():
        agent_md.rename(soul_md)
        changes.append(f"Renamed {agent_md} → {soul_md}")
    elif agent_md.exists() and soul_md.exists():
        print(
            f"WARNING: Both {agent_md} and {soul_md} exist. "
            "Merge manually and delete agent.md.",
            file=sys.stderr,
        )

    # 2. Update cogmem.toml: agent = → soul =
    toml_path = target / "cogmem.toml"
    if toml_path.exists():
        content = toml_path.read_text(encoding="utf-8")
        if re.search(r'^agent\s*=', content, re.MULTILINE):
            updated = re.sub(
                r'^agent\s*=\s*"identity/agent\.md"',
                'soul = "identity/soul.md"',
                content,
                flags=re.MULTILINE,
            )
            if updated != content:
                toml_path.write_text(updated, encoding="utf-8")
                changes.append(f"Updated {toml_path}: agent → soul")

    # 3. Update CLAUDE.md: @identity/agent.md → @identity/soul.md
    claude_md = target / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        if "@identity/agent.md" in content:
            updated = content.replace("@identity/agent.md", "@identity/soul.md")
            # Also add @identity/soul.md if not present
            if "@identity/soul.md" not in content:
                claude_md.write_text(updated, encoding="utf-8")
                changes.append(f"Updated {claude_md}: @identity/agent.md → @identity/soul.md")
            else:
                # Remove duplicate agent.md reference
                updated = content.replace("@identity/agent.md\n", "")
                claude_md.write_text(updated, encoding="utf-8")
                changes.append(f"Updated {claude_md}: removed @identity/agent.md")

    if changes:
        print("Migration complete:")
        for c in changes:
            print(f"  - {c}")
    else:
        print("Nothing to migrate — project is up to date.")
