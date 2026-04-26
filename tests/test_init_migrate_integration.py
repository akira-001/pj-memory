"""Tests for init→migrate redirection and migrate→skills sync integration."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from cognitive_memory.cli import init_cmd, migrate_cmd, skills_update_cmd


def _seed_project(target: Path) -> None:
    """Create a minimal cogmem.toml so the project counts as 'existing'."""
    (target / "cogmem.toml").write_text(
        '[cogmem]\nuser_id = "tester"\nlogs_dir = "memory/logs"\n',
        encoding="utf-8",
    )


# ----- init: existing project detection -----

def test_init_with_existing_toml_redirects_to_migrate_on_y(tmp_path, monkeypatch):
    _seed_project(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "y")

    called = {}
    def _fake_migrate(target_dir, user_id=None, lang="en", **_):
        called["target_dir"] = target_dir
        called["lang"] = lang

    monkeypatch.setattr("cognitive_memory.cli.migrate_cmd.run_migrate", _fake_migrate)
    init_cmd.run_init(str(tmp_path), lang="en", user_id="tester")
    assert called.get("target_dir") == str(tmp_path)
    assert called.get("lang") == "en"


def test_init_with_existing_toml_skips_migrate_on_n(tmp_path, monkeypatch):
    _seed_project(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "n")

    called = {"migrate": False}
    def _fake_migrate(*a, **kw):
        called["migrate"] = True

    monkeypatch.setattr("cognitive_memory.cli.migrate_cmd.run_migrate", _fake_migrate)
    # The init will continue to its normal flow (which writes more files).
    # We only assert migrate was NOT called.
    try:
        init_cmd.run_init(str(tmp_path), lang="en", user_id="tester")
    except Exception:
        pass  # downstream init steps may fail in the bare tmp_path, that's OK
    assert called["migrate"] is False


def test_init_with_existing_toml_eof_skips_migrate(tmp_path, monkeypatch):
    """OSError/EOFError on input (pytest stdin capture) → treat as 'n'."""
    _seed_project(tmp_path)
    def _raise(_): raise OSError("captured stdin")
    monkeypatch.setattr("builtins.input", _raise)

    called = {"migrate": False}
    def _fake_migrate(*a, **kw):
        called["migrate"] = True
    monkeypatch.setattr("cognitive_memory.cli.migrate_cmd.run_migrate", _fake_migrate)

    try:
        init_cmd.run_init(str(tmp_path), lang="en", user_id="tester")
    except Exception:
        pass
    assert called["migrate"] is False


# ----- migrate: skills update integration -----

def test_migrate_calls_skills_update_when_drift_exists(tmp_path, monkeypatch, capsys):
    _seed_project(tmp_path)

    # Mock detect_diffs to return one fake drift candidate
    fake_candidate = [{"name": "fake-skill", "added": 5, "removed": 2,
                       "installed": Path("/dev/null"), "packaged": Path("/dev/null")}]
    monkeypatch.setattr(
        "cognitive_memory.cli.skills_update_cmd.detect_diffs",
        lambda lang="en", target_skill=None: fake_candidate,
    )

    called = {"update": False}
    def _fake_update(args):
        called["update"] = True
        called["lang"] = args.lang
        called["auto_yes"] = args.auto_yes
        return 0
    monkeypatch.setattr(
        "cognitive_memory.cli.skills_update_cmd.run_skills_update_templates",
        _fake_update,
    )

    migrate_cmd.run_migrate(str(tmp_path), user_id="tester", lang="ja")
    assert called["update"] is True
    assert called["lang"] == "ja"
    assert called["auto_yes"] is False


def test_migrate_no_skills_flag_skips_update(tmp_path, monkeypatch):
    _seed_project(tmp_path)

    called = {"update": False}
    def _fake_update(args):
        called["update"] = True
    monkeypatch.setattr(
        "cognitive_memory.cli.skills_update_cmd.run_skills_update_templates",
        _fake_update,
    )

    migrate_cmd.run_migrate(str(tmp_path), user_id="tester", no_skills=True)
    assert called["update"] is False


def test_migrate_auto_yes_skills_propagates(tmp_path, monkeypatch):
    _seed_project(tmp_path)
    fake_candidate = [{"name": "x", "added": 1, "removed": 1,
                       "installed": Path("/dev/null"), "packaged": Path("/dev/null")}]
    monkeypatch.setattr(
        "cognitive_memory.cli.skills_update_cmd.detect_diffs",
        lambda lang="en", target_skill=None: fake_candidate,
    )

    captured = {}
    def _fake_update(args):
        captured["auto_yes"] = args.auto_yes
        return 0
    monkeypatch.setattr(
        "cognitive_memory.cli.skills_update_cmd.run_skills_update_templates",
        _fake_update,
    )

    migrate_cmd.run_migrate(str(tmp_path), user_id="tester", auto_yes_skills=True)
    assert captured.get("auto_yes") is True


def test_migrate_skill_update_failure_does_not_block(tmp_path, monkeypatch, capsys):
    _seed_project(tmp_path)
    monkeypatch.setattr(
        "cognitive_memory.cli.skills_update_cmd.detect_diffs",
        lambda lang="en", target_skill=None: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    # Should not raise; migrate completes
    migrate_cmd.run_migrate(str(tmp_path), user_id="tester")
    err = capsys.readouterr().err
    assert "skill template sync skipped" in err
