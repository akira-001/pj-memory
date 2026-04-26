"""Tests for [cogmem].lang persistence and lang-aware upgrade-check drift."""

from __future__ import annotations

from pathlib import Path

import pytest

from cognitive_memory.cli import upgrade_cmd


# ----- get_user_lang / set_cogmem_lang -----

def test_get_user_lang_defaults_to_en_when_missing(tmp_path):
    (tmp_path / "cogmem.toml").write_text(
        '[cogmem]\nuser_id = "x"\n',
        encoding="utf-8",
    )
    assert upgrade_cmd.get_user_lang(tmp_path) == "en"


def test_get_user_lang_returns_persisted_ja(tmp_path):
    (tmp_path / "cogmem.toml").write_text(
        '[cogmem]\nuser_id = "x"\nlang = "ja"\n',
        encoding="utf-8",
    )
    assert upgrade_cmd.get_user_lang(tmp_path) == "ja"


def test_get_user_lang_falls_back_on_invalid_value(tmp_path):
    (tmp_path / "cogmem.toml").write_text(
        '[cogmem]\nuser_id = "x"\nlang = "fr"\n',
        encoding="utf-8",
    )
    assert upgrade_cmd.get_user_lang(tmp_path) == "en"


def test_get_user_lang_no_toml(tmp_path):
    assert upgrade_cmd.get_user_lang(tmp_path) == "en"


def test_set_cogmem_lang_adds_key(tmp_path):
    p = tmp_path / "cogmem.toml"
    p.write_text('[cogmem]\nuser_id = "x"\n', encoding="utf-8")
    upgrade_cmd.set_cogmem_lang(p, "ja")
    assert upgrade_cmd.get_user_lang(tmp_path) == "ja"


def test_set_cogmem_lang_updates_existing_key(tmp_path):
    p = tmp_path / "cogmem.toml"
    p.write_text(
        '[cogmem]\nuser_id = "x"\nlang = "en"\n',
        encoding="utf-8",
    )
    upgrade_cmd.set_cogmem_lang(p, "ja")
    assert upgrade_cmd.get_user_lang(tmp_path) == "ja"
    # Other keys preserved
    cfg = upgrade_cmd._read_toml(p)
    assert cfg["cogmem"]["user_id"] == "x"


def test_set_cogmem_lang_preserves_other_sections(tmp_path):
    p = tmp_path / "cogmem.toml"
    p.write_text(
        '[cogmem]\nuser_id = "akira"\nlogs_dir = "memory/logs"\n\n[updates]\nauto = "ask"\n',
        encoding="utf-8",
    )
    upgrade_cmd.set_cogmem_lang(p, "ja")
    cfg = upgrade_cmd._read_toml(p)
    assert cfg["cogmem"]["user_id"] == "akira"
    assert cfg["cogmem"]["logs_dir"] == "memory/logs"
    assert cfg["cogmem"]["lang"] == "ja"
    assert cfg["updates"]["auto"] == "ask"


def test_set_cogmem_lang_noop_when_section_missing(tmp_path):
    """If [cogmem] section is absent, set_cogmem_lang leaves the file unchanged
    rather than fabricating a section. Templates always include [cogmem]."""
    p = tmp_path / "cogmem.toml"
    original = '[updates]\nauto = "ask"\n'
    p.write_text(original, encoding="utf-8")
    upgrade_cmd.set_cogmem_lang(p, "ja")
    assert p.read_text() == original


def test_set_cogmem_lang_rejects_invalid(tmp_path):
    p = tmp_path / "cogmem.toml"
    p.write_text('[cogmem]\nuser_id = "x"\n', encoding="utf-8")
    upgrade_cmd.set_cogmem_lang(p, "fr")  # invalid; should be no-op
    cfg = upgrade_cmd._read_toml(p)
    assert "lang" not in cfg.get("cogmem", {})


def test_set_cogmem_lang_idempotent(tmp_path):
    p = tmp_path / "cogmem.toml"
    p.write_text('[cogmem]\nuser_id = "x"\n', encoding="utf-8")
    upgrade_cmd.set_cogmem_lang(p, "ja")
    first = p.read_text()
    upgrade_cmd.set_cogmem_lang(p, "ja")
    assert p.read_text() == first  # second call doesn't mutate


# ----- _count_skill_template_drift uses persisted lang -----

def test_drift_count_uses_persisted_lang(tmp_path, monkeypatch):
    p = tmp_path / "cogmem.toml"
    p.write_text('[cogmem]\nuser_id = "x"\nlang = "ja"\n', encoding="utf-8")

    captured = {"lang": None}
    def _fake_detect(lang="en", target_skill=None):
        captured["lang"] = lang
        return [{"name": f"x-{lang}", "added": 1, "removed": 1, "installed": Path("/dev/null"), "packaged": Path("/dev/null")}]

    monkeypatch.setattr("cognitive_memory.cli.skills_update_cmd.detect_diffs", _fake_detect)
    n = upgrade_cmd._count_skill_template_drift(tmp_path)
    assert captured["lang"] == "ja"
    assert n == 1


def test_drift_count_defaults_en_when_no_toml(tmp_path, monkeypatch):
    captured = {"lang": None}
    def _fake_detect(lang="en", target_skill=None):
        captured["lang"] = lang
        return []
    monkeypatch.setattr("cognitive_memory.cli.skills_update_cmd.detect_diffs", _fake_detect)
    upgrade_cmd._count_skill_template_drift(tmp_path)
    assert captured["lang"] == "en"
