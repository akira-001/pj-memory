"""cogmem migrate — upgrade project files from older versions."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SCAFFOLD_DIR = Path(__file__).resolve().parent.parent / "templates"


def run_migrate(target_dir: str = "."):
    target = Path(target_dir).resolve()
    changes = []

    identity_dir = target / "identity"
    identity_dir.mkdir(parents=True, exist_ok=True)

    # 1. Rename identity/agent.md → identity/soul.md
    agent_md = identity_dir / "agent.md"
    soul_md = identity_dir / "soul.md"

    if agent_md.exists() and not soul_md.exists():
        agent_md.rename(soul_md)
        changes.append(f"Renamed {agent_md} → {soul_md}")
    elif agent_md.exists() and soul_md.exists():
        print(
            f"WARNING: Both {agent_md} and {soul_md} exist. "
            "Merge manually and delete agent.md.",
            file=sys.stderr,
        )

    # 2. Create identity/agents.md if missing
    agents_md = identity_dir / "agents.md"
    if not agents_md.exists():
        template = _SCAFFOLD_DIR / "agents.md"
        if template.exists():
            agents_md.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
            changes.append(f"Created {agents_md}")

    # 3. Update cogmem.toml: agent = → soul =
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

    # 4. Update CLAUDE.md: @identity/agent.md → @identity/soul.md
    claude_md = target / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        updated = content

        # Replace agent.md reference with soul.md
        if "@identity/agent.md" in updated:
            if "@identity/soul.md" not in updated:
                updated = updated.replace("@identity/agent.md", "@identity/soul.md")
            else:
                updated = updated.replace("@identity/agent.md\n", "")

        # Add @identity/agents.md reference if missing
        if "@identity/agents.md" not in updated:
            # Insert before @identity/soul.md
            if "@identity/soul.md" in updated:
                updated = updated.replace(
                    "@identity/soul.md",
                    "@identity/agents.md\n\n## Agent Identity\n\n@identity/soul.md",
                )
            else:
                # Append after the title
                updated = updated + "\n@identity/agents.md\n"

        if updated != content:
            claude_md.write_text(updated, encoding="utf-8")
            changes.append(f"Updated {claude_md}")

    if changes:
        print("Migration complete:")
        for c in changes:
            print(f"  - {c}")
    else:
        print("Nothing to migrate — project is up to date.")
