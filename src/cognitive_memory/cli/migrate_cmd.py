"""cogmem migrate — upgrade project files from older versions."""

from __future__ import annotations

import getpass
import re
import shutil
import sys
from pathlib import Path

_SCAFFOLD_DIR = Path(__file__).resolve().parent.parent / "templates"


def _ensure_gitignore_entry(gitignore: Path, entry: str) -> None:
    """Add *entry* to .gitignore if it is not already present."""
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if entry in content:
            return
        with open(gitignore, "a", encoding="utf-8") as f:
            f.write(f"\n{entry}\n")
    else:
        gitignore.write_text(f"{entry}\n", encoding="utf-8")


def run_migrate(
    target_dir: str = ".",
    user_id: str | None = None,
    lang: str = "en",
    no_skills: bool = False,
    auto_yes_skills: bool = False,
):
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

    # 5. Migrate user_id: add to cogmem.toml and move logs/contexts
    changes.extend(_migrate_user_id(target, user_id=user_id))

    # 6. Setup Claude Code hooks
    from .init_cmd import setup_hooks
    claude_dir = target / ".claude"
    if claude_dir.exists() or (target / "CLAUDE.md").exists():
        setup_hooks(str(claude_dir))
        changes.append(f"Registered hooks → {claude_dir / 'settings.json'}")

    if changes:
        print("Migration complete:")
        for c in changes:
            print(f"  - {c}")
    else:
        print("Nothing to migrate — project is up to date.")

    # 7. Sync installed skill templates with packaged versions (drift detection)
    if not no_skills:
        try:
            from argparse import Namespace
            from .skills_update_cmd import detect_diffs, run_skills_update_templates
            drift = detect_diffs(lang=lang)
            if drift:
                print()
                run_skills_update_templates(Namespace(
                    lang=lang,
                    dry_run=False,
                    auto_yes=auto_yes_skills,
                    skill=None,
                    json=False,
                ))
        except Exception as exc:
            # Fail-open: skill sync should never block migration
            print(f"  (skill template sync skipped: {exc})", file=sys.stderr)


def _prompt_user_id_for_migrate(logs_dir: Path) -> str:
    """Prompt user for their user_id during migration."""
    default_id = getpass.getuser()
    while True:
        try:
            raw = input(
                f"Enter your user ID for log isolation (default: {default_id}): "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            raw = ""
        user_id = raw or default_id
        if not re.match(r"^[a-zA-Z0-9_-]+$", user_id):
            print("Invalid ID. Use only letters, numbers, dashes, and underscores.")
            continue
        # Check if this ID is already used by another user
        user_dir = logs_dir / user_id
        if user_dir.is_dir() and any(f.suffix == ".md" for f in user_dir.iterdir()):
            print(f"User ID '{user_id}' already has logs at {user_dir}. Choose a different ID.")
            continue
        return user_id


def _migrate_user_id(target: Path, user_id: str | None = None) -> list[str]:
    """Write user_id to cogmem.local.toml and move existing logs/contexts into user subdirectory."""
    changes: list[str] = []
    toml_path = target / "cogmem.toml"
    local_toml_path = target / "cogmem.local.toml"

    # Skip if cogmem.toml doesn't exist
    if not toml_path.exists():
        return changes

    # Skip if cogmem.local.toml already has user_id
    if local_toml_path.exists():
        local_content = local_toml_path.read_text(encoding="utf-8")
        if re.search(r'^user_id\s*=', local_content, re.MULTILINE):
            return changes

    # Also skip if cogmem.toml still has user_id (old format — remove it)
    content = toml_path.read_text(encoding="utf-8")
    old_user_id_match = re.search(r'^user_id\s*=\s*"([^"]*)"', content, re.MULTILINE)
    if old_user_id_match:
        # Extract user_id from cogmem.toml and remove the line
        if user_id is None:
            user_id = old_user_id_match.group(1)
        updated = re.sub(r'^user_id\s*=\s*"[^"]*"\n?', '', content, flags=re.MULTILINE)
        toml_path.write_text(updated, encoding="utf-8")
        changes.append(f"Removed user_id from {toml_path}")

    # Determine user_id
    if user_id is None:
        logs_dir = target / "memory" / "logs"
        user_id = _prompt_user_id_for_migrate(logs_dir)

    # Write user_id to cogmem.local.toml (gitignored)
    local_toml_path.write_text(
        f'[cogmem]\nuser_id = "{user_id}"\n', encoding="utf-8"
    )
    changes.append(f'Created {local_toml_path} with user_id = "{user_id}"')

    # Add cogmem.local.toml to .gitignore if not present
    gitignore = target / ".gitignore"
    _ensure_gitignore_entry(gitignore, "cogmem.local.toml")
    changes.append(f"Ensured cogmem.local.toml in {gitignore}")

    # Move existing log files into user subdirectory
    for dir_name in ("memory/logs", "memory/contexts"):
        src_dir = target / dir_name
        if not src_dir.is_dir():
            continue

        # Collect .md files in the root of the directory (not in subdirectories)
        md_files = [f for f in src_dir.iterdir() if f.is_file() and f.suffix == ".md"]
        gitkeep = src_dir / ".gitkeep"

        if not md_files:
            # No files to move, just create the user subdirectory
            user_dir = src_dir / user_id
            user_dir.mkdir(parents=True, exist_ok=True)
            user_gitkeep = user_dir / ".gitkeep"
            if not user_gitkeep.exists():
                user_gitkeep.touch()
            continue

        # Create user subdirectory and move files
        user_dir = src_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        moved = 0
        for f in md_files:
            dest = user_dir / f.name
            shutil.move(str(f), str(dest))
            moved += 1

        # Move .gitkeep if it exists at root
        if gitkeep.exists():
            gitkeep.unlink()
        user_gitkeep = user_dir / ".gitkeep"
        if not user_gitkeep.exists():
            user_gitkeep.touch()

        changes.append(f"Moved {moved} files: {dir_name}/ → {dir_name}/{user_id}/")

    # Copy identity/user.md → identity/users/{user_id}.md and replace with symlink
    user_md = target / "identity" / "user.md"
    users_dir = target / "identity" / "users"
    if user_md.exists() and not user_md.is_symlink():
        users_dir.mkdir(parents=True, exist_ok=True)
        dest = users_dir / f"{user_id}.md"
        if not dest.exists():
            shutil.copy2(str(user_md), str(dest))
        user_md.unlink()
        user_md.symlink_to(f"users/{user_id}.md")
        changes.append(f"Replaced identity/user.md with symlink → users/{user_id}.md")

    return changes
