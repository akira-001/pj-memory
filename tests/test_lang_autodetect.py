"""Tests for --lang auto-detection from cogmem.toml.

Prevents regression of the bug where `cogmem migrate` (no flag) silently
overwrote `[cogmem].lang = "ja"` back to "en", which then caused massive false
drift detection between en templates and ja-installed skills.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from cognitive_memory.cli import migrate_cmd, skills_update_cmd, upgrade_cmd


def _seed_ja_project(target: Path) -> None:
    (target / "cogmem.toml").write_text(
        '[cogmem]\nuser_id = "tester"\nlang = "ja"\nlogs_dir = "memory/logs"\n',
        encoding="utf-8",
    )


def _seed_no_lang_project(target: Path) -> None:
    (target / "cogmem.toml").write_text(
        '[cogmem]\nuser_id = "tester"\nlogs_dir = "memory/logs"\n',
        encoding="utf-8",
    )


# ----- migrate auto-detect -----

def test_migrate_lang_none_reads_persisted_ja(tmp_path, monkeypatch):
    """Critical: migrate without --lang must NOT overwrite persisted ja with en."""
    _seed_ja_project(tmp_path)

    captured_skills_lang = {}
    def _fake_update(args):
        captured_skills_lang["lang"] = args.lang
        return 0
    monkeypatch.setattr(
        "cognitive_memory.cli.skills_update_cmd.run_skills_update_templates",
        _fake_update,
    )
    monkeypatch.setattr(
        "cognitive_memory.cli.skills_update_cmd.detect_diffs",
        lambda lang="en", target_skill=None: [{"name": "x", "added": 1, "removed": 1,
                                                "installed": Path("/dev/null"),
                                                "packaged": Path("/dev/null")}],
    )

    migrate_cmd.run_migrate(str(tmp_path), user_id="tester", lang=None)

    # Persisted lang must remain "ja"
    assert upgrade_cmd.get_user_lang(tmp_path) == "ja"
    # Skill update must be invoked with "ja"
    assert captured_skills_lang["lang"] == "ja"


def test_migrate_lang_none_falls_back_to_en(tmp_path, monkeypatch):
    _seed_no_lang_project(tmp_path)
    monkeypatch.setattr(
        "cognitive_memory.cli.skills_update_cmd.detect_diffs",
        lambda lang="en", target_skill=None: [],
    )
    migrate_cmd.run_migrate(str(tmp_path), user_id="tester", lang=None)
    # Without --lang and without persisted lang, default is "en" — but since
    # there was no persisted ja either, no overwrite happens (existing == lang)
    cfg_lang = upgrade_cmd.get_user_lang(tmp_path)
    assert cfg_lang == "en"


def test_migrate_explicit_lang_overrides_persisted(tmp_path, monkeypatch):
    """User can still force a different lang explicitly (intentional change)."""
    _seed_ja_project(tmp_path)
    monkeypatch.setattr(
        "cognitive_memory.cli.skills_update_cmd.detect_diffs",
        lambda lang="en", target_skill=None: [],
    )
    migrate_cmd.run_migrate(str(tmp_path), user_id="tester", lang="en")
    # Explicit en overwrites ja (this is intentional for users who want to switch)
    assert upgrade_cmd.get_user_lang(tmp_path) == "en"


# ----- skills update-templates auto-detect -----

def test_skills_update_lang_none_reads_persisted_ja(tmp_path, monkeypatch):
    _seed_ja_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    captured = {"lang": None}
    monkeypatch.setattr(
        "cognitive_memory.cli.skills_update_cmd.detect_diffs",
        lambda lang="en", target_skill=None: (captured.update({"lang": lang}) or []),
    )

    args = Namespace(lang=None, dry_run=True, auto_yes=False, skill=None, json=False)
    skills_update_cmd.run_skills_update_templates(args)
    assert captured["lang"] == "ja"


def test_skills_update_lang_none_falls_back_to_en(tmp_path, monkeypatch):
    _seed_no_lang_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    captured = {"lang": None}
    monkeypatch.setattr(
        "cognitive_memory.cli.skills_update_cmd.detect_diffs",
        lambda lang="en", target_skill=None: (captured.update({"lang": lang}) or []),
    )

    args = Namespace(lang=None, dry_run=True, auto_yes=False, skill=None, json=False)
    skills_update_cmd.run_skills_update_templates(args)
    assert captured["lang"] == "en"


def test_skills_update_explicit_lang_wins(tmp_path, monkeypatch):
    _seed_ja_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    captured = {"lang": None}
    monkeypatch.setattr(
        "cognitive_memory.cli.skills_update_cmd.detect_diffs",
        lambda lang="en", target_skill=None: (captured.update({"lang": lang}) or []),
    )

    args = Namespace(lang="en", dry_run=True, auto_yes=False, skill=None, json=False)
    skills_update_cmd.run_skills_update_templates(args)
    assert captured["lang"] == "en"
