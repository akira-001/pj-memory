"""Tests for cogmem skills update-templates."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from cognitive_memory.cli import skills_update_cmd


@pytest.fixture
def fake_homes(tmp_path, monkeypatch):
    """Redirect ~/.claude to tmp_path/home and provide a packaged template dir."""
    fake_home = tmp_path / "home"
    (fake_home / ".claude" / "skills").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    pkg_tmpl = tmp_path / "pkg" / "templates" / "skills"
    pkg_tmpl.mkdir(parents=True)
    pkg_tmpl_ja = tmp_path / "pkg" / "templates" / "ja" / "skills"
    pkg_tmpl_ja.mkdir(parents=True)

    def _fake_get_template_dir(lang: str = "en") -> Path:
        return pkg_tmpl_ja if lang == "ja" else pkg_tmpl

    monkeypatch.setattr(skills_update_cmd, "_get_template_dir", _fake_get_template_dir)
    return {
        "home": fake_home,
        "skills_dir": fake_home / ".claude" / "skills",
        "tmpl_en": pkg_tmpl,
        "tmpl_ja": pkg_tmpl_ja,
    }


def _install_skill(skills_dir: Path, name: str, body: str) -> Path:
    p = skills_dir / name / "SKILL.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


def _packaged_skill(tmpl_dir: Path, name: str, body: str) -> Path:
    p = tmpl_dir / name / "SKILL.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


# ----- detect_diffs -----

def test_detect_diffs_returns_empty_when_no_drift(fake_homes):
    body = "---\nname: foo\n---\nbody"
    _install_skill(fake_homes["skills_dir"], "foo", body)
    _packaged_skill(fake_homes["tmpl_en"], "foo", body)
    assert skills_update_cmd.detect_diffs(lang="en") == []


def test_detect_diffs_finds_drift(fake_homes):
    _install_skill(fake_homes["skills_dir"], "foo", "old version\n")
    _packaged_skill(fake_homes["tmpl_en"], "foo", "new version with extra line\nplus more\n")
    diffs = skills_update_cmd.detect_diffs(lang="en")
    assert len(diffs) == 1
    assert diffs[0]["name"] == "foo"
    assert diffs[0]["added"] >= 1
    assert diffs[0]["removed"] >= 1


def test_detect_diffs_skips_uninstalled(fake_homes):
    """Skills not yet in ~/.claude/skills/ are NOT candidates (init handles those)."""
    _packaged_skill(fake_homes["tmpl_en"], "newone", "I am new\n")
    assert skills_update_cmd.detect_diffs(lang="en") == []


def test_detect_diffs_filters_by_skill_name(fake_homes):
    _install_skill(fake_homes["skills_dir"], "foo", "old foo\n")
    _packaged_skill(fake_homes["tmpl_en"], "foo", "new foo\n")
    _install_skill(fake_homes["skills_dir"], "bar", "old bar\n")
    _packaged_skill(fake_homes["tmpl_en"], "bar", "new bar\n")
    diffs = skills_update_cmd.detect_diffs(lang="en", target_skill="foo")
    assert len(diffs) == 1
    assert diffs[0]["name"] == "foo"


def test_detect_diffs_uses_ja_templates(fake_homes):
    _install_skill(fake_homes["skills_dir"], "foo", "english body\n")
    _packaged_skill(fake_homes["tmpl_ja"], "foo", "日本語ボディ\n")
    _packaged_skill(fake_homes["tmpl_en"], "foo", "english body\n")  # same as installed
    en_diffs = skills_update_cmd.detect_diffs(lang="en")
    ja_diffs = skills_update_cmd.detect_diffs(lang="ja")
    assert en_diffs == []
    assert len(ja_diffs) == 1


# ----- run_skills_update_templates: dry-run -----

def test_dry_run_does_not_modify(fake_homes, capsys):
    body_old = "old\n"
    body_new = "new\n"
    installed = _install_skill(fake_homes["skills_dir"], "foo", body_old)
    _packaged_skill(fake_homes["tmpl_en"], "foo", body_new)

    args = Namespace(lang="en", dry_run=True, auto_yes=False, skill=None, json=False)
    rc = skills_update_cmd.run_skills_update_templates(args)
    assert rc == 0
    assert installed.read_text() == body_old  # unchanged


# ----- run_skills_update_templates: auto-yes -----

def test_auto_yes_applies_all(fake_homes, capsys):
    body_old = "old line\n"
    body_new = "new line replacing old\n"
    installed = _install_skill(fake_homes["skills_dir"], "foo", body_old)
    _packaged_skill(fake_homes["tmpl_en"], "foo", body_new)

    args = Namespace(lang="en", dry_run=False, auto_yes=True, skill=None, json=False)
    rc = skills_update_cmd.run_skills_update_templates(args)
    assert rc == 0
    assert installed.read_text() == body_new


def test_auto_yes_creates_backup(fake_homes):
    body_old = "old content\n"
    body_new = "new content\n"
    _install_skill(fake_homes["skills_dir"], "foo", body_old)
    _packaged_skill(fake_homes["tmpl_en"], "foo", body_new)

    args = Namespace(lang="en", dry_run=False, auto_yes=True, skill=None, json=False)
    skills_update_cmd.run_skills_update_templates(args)

    backup_root = fake_homes["skills_dir"]
    backups = list(backup_root.glob(".backup-*/foo/SKILL.md"))
    assert len(backups) == 1
    assert backups[0].read_text() == body_old


# ----- run_skills_update_templates: interactive prompt -----

def test_interactive_y_applies(fake_homes, monkeypatch):
    _install_skill(fake_homes["skills_dir"], "foo", "old\n")
    new_path = _packaged_skill(fake_homes["tmpl_en"], "foo", "new\n")
    monkeypatch.setattr("builtins.input", lambda _: "y")

    args = Namespace(lang="en", dry_run=False, auto_yes=False, skill=None, json=False)
    skills_update_cmd.run_skills_update_templates(args)
    installed = fake_homes["skills_dir"] / "foo" / "SKILL.md"
    assert installed.read_text() == "new\n"


def test_interactive_n_skips(fake_homes, monkeypatch):
    _install_skill(fake_homes["skills_dir"], "foo", "old\n")
    _packaged_skill(fake_homes["tmpl_en"], "foo", "new\n")
    monkeypatch.setattr("builtins.input", lambda _: "n")

    args = Namespace(lang="en", dry_run=False, auto_yes=False, skill=None, json=False)
    skills_update_cmd.run_skills_update_templates(args)
    installed = fake_homes["skills_dir"] / "foo" / "SKILL.md"
    assert installed.read_text() == "old\n"


def test_interactive_eof_skips(fake_homes, monkeypatch):
    """Ctrl-D / EOF should be treated as skip, not crash."""
    _install_skill(fake_homes["skills_dir"], "foo", "old\n")
    _packaged_skill(fake_homes["tmpl_en"], "foo", "new\n")
    def _raise(_): raise EOFError
    monkeypatch.setattr("builtins.input", _raise)

    args = Namespace(lang="en", dry_run=False, auto_yes=False, skill=None, json=False)
    rc = skills_update_cmd.run_skills_update_templates(args)
    assert rc == 0


def test_interactive_d_then_y(fake_homes, monkeypatch, capsys):
    """'d' shows diff and re-prompts; subsequent 'y' applies."""
    _install_skill(fake_homes["skills_dir"], "foo", "old\n")
    _packaged_skill(fake_homes["tmpl_en"], "foo", "new\n")
    answers = iter(["d", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    args = Namespace(lang="en", dry_run=False, auto_yes=False, skill=None, json=False)
    skills_update_cmd.run_skills_update_templates(args)
    installed = fake_homes["skills_dir"] / "foo" / "SKILL.md"
    assert installed.read_text() == "new\n"
    out = capsys.readouterr().out
    assert "---" in out  # unified diff markers


# ----- JSON output -----

def test_json_output_format(fake_homes, capsys):
    _install_skill(fake_homes["skills_dir"], "foo", "old\n")
    _packaged_skill(fake_homes["tmpl_en"], "foo", "new\n")

    args = Namespace(lang="en", dry_run=False, auto_yes=False, skill=None, json=True)
    skills_update_cmd.run_skills_update_templates(args)
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["lang"] == "en"
    assert len(parsed["candidates"]) == 1
    assert parsed["candidates"][0]["name"] == "foo"


def test_json_output_when_no_drift(fake_homes, capsys):
    body = "same\n"
    _install_skill(fake_homes["skills_dir"], "foo", body)
    _packaged_skill(fake_homes["tmpl_en"], "foo", body)

    args = Namespace(lang="en", dry_run=False, auto_yes=False, skill=None, json=True)
    skills_update_cmd.run_skills_update_templates(args)
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["candidates"] == []


# ----- empty/missing dirs -----

def test_no_skills_dir_returns_empty(tmp_path, monkeypatch):
    fake_home = tmp_path / "no_claude"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    assert skills_update_cmd.detect_diffs(lang="en") == []


def test_no_template_dir_returns_empty(fake_homes, monkeypatch):
    monkeypatch.setattr(skills_update_cmd, "_get_template_dir", lambda lang="en": Path("/nonexistent"))
    _install_skill(fake_homes["skills_dir"], "foo", "x\n")
    assert skills_update_cmd.detect_diffs(lang="en") == []
