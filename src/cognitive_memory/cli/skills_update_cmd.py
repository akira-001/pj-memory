"""cogmem skills update-templates — update locally-installed skills from packaged templates.

Solves the "existing-user skill drift" problem: `cogmem init` skip-protects existing
skills, so template improvements bundled in newer cogmem-agent versions never reach
existing users. This command diffs installed `~/.claude/skills/<name>/SKILL.md` against
the packaged templates and offers to update each one with backup + per-skill confirmation.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any


def _get_template_dir(lang: str = "en") -> Path:
    """Return the packaged templates/skills/ directory for the chosen language."""
    from .. import __file__ as pkg_init
    base = Path(pkg_init).resolve().parent / "templates"
    if lang == "ja":
        return base / "ja" / "skills"
    return base / "skills"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _diff_summary(old: Path, new: Path) -> tuple[int, int]:
    """Return (added_lines, removed_lines)."""
    old_lines = old.read_text(encoding="utf-8").splitlines()
    new_lines = new.read_text(encoding="utf-8").splitlines()
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))
    added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
    removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
    return added, removed


def _show_diff(old: Path, new: Path) -> None:
    old_lines = old.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = new.read_text(encoding="utf-8").splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"installed/{old.parent.name}/SKILL.md",
        tofile=f"packaged/{new.parent.name}/SKILL.md",
    )
    sys.stdout.writelines(diff)


def detect_diffs(lang: str = "en", target_skill: str | None = None) -> list[dict[str, Any]]:
    """Detect skills whose installed copy differs from the packaged template.

    Returns a list of dicts: [{"name": str, "added": int, "removed": int,
                                "installed": Path, "packaged": Path}, ...]
    Skills not yet installed (no `~/.claude/skills/<name>/`) are NOT included —
    those are handled by `cogmem init`.
    """
    tmpl_dir = _get_template_dir(lang)
    global_skills = Path.home() / ".claude" / "skills"

    if not tmpl_dir.is_dir() or not global_skills.is_dir():
        return []

    candidates: list[dict[str, Any]] = []
    for skill_dir in sorted(tmpl_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        name = skill_dir.name
        if target_skill and name != target_skill:
            continue
        new_skill = skill_dir / "SKILL.md"
        old_skill = global_skills / name / "SKILL.md"
        if not new_skill.exists() or not old_skill.exists():
            continue
        if _file_sha256(old_skill) == _file_sha256(new_skill):
            continue
        added, removed = _diff_summary(old_skill, new_skill)
        candidates.append({
            "name": name,
            "added": added,
            "removed": removed,
            "installed": old_skill,
            "packaged": new_skill,
        })
    return candidates


def _prompt_user(name: str, old_skill: Path, new_skill: Path) -> str:
    while True:
        try:
            ans = input(f"  Update '{name}'? [y/N/d=show diff]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "n"
        if ans == "d":
            _show_diff(old_skill, new_skill)
            continue
        return "y" if ans == "y" else "n"


def run_skills_update_templates(args: argparse.Namespace) -> int:
    """Entry point for `cogmem skills update-templates`. Returns exit code."""
    lang = getattr(args, "lang", None) or "en"
    dry_run = getattr(args, "dry_run", False)
    auto_yes = getattr(args, "auto_yes", False)
    target_skill = getattr(args, "skill", None)
    json_output = getattr(args, "json", False)

    candidates = detect_diffs(lang=lang, target_skill=target_skill)

    if json_output:
        result = {
            "lang": lang,
            "candidates": [
                {"name": c["name"], "added": c["added"], "removed": c["removed"]}
                for c in candidates
            ],
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if not candidates:
        if target_skill:
            print(f"✓ Skill '{target_skill}' is up to date (or not installed).")
        else:
            print("✓ All installed skills match packaged templates.")
        return 0

    print(f"Found {len(candidates)} skill(s) with template updates (lang={lang}):")
    for c in candidates:
        print(f"  - {c['name']:<20} (+{c['added']} -{c['removed']} lines)")
    print()

    if dry_run:
        print("(dry-run: no changes applied)")
        print("Use without --dry-run to apply, --auto-yes to skip prompts.")
        return 0

    backup_root = Path.home() / ".claude" / "skills" / f".backup-{date.today().isoformat()}"
    updated, skipped = 0, 0

    for c in candidates:
        name = c["name"]
        old_skill: Path = c["installed"]
        new_skill: Path = c["packaged"]

        if auto_yes:
            answer = "y"
        else:
            answer = _prompt_user(name, old_skill, new_skill)

        if answer != "y":
            skipped += 1
            continue

        bak_path = backup_root / name / "SKILL.md"
        bak_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old_skill, bak_path)
        shutil.copy2(new_skill, old_skill)
        print(f"  ✓ {name} updated (backup: {bak_path})")
        updated += 1

    print()
    print(f"Result: {updated} updated, {skipped} skipped")
    if updated > 0:
        print(f"Backups under: {backup_root}")
    return 0
